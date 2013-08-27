# -*- coding: utf-8 -*-

"""
    A rhythmbox plugin for playing music from baidu music.

    Copyright (C) 2013 pandasunny <pandasunny@gmail.com>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import os

import rb
from gi.repository import GObject
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import RB
from gi.repository import Peas
from gi.repository import PeasGtk
from gi.repository import Gtk
from gi.repository import GdkPixbuf

from client import Client

from source import BaseSource
from source import CollectSource
from source import OnlinePlaylistSource
from source import TempSource

from search import SearchHandle
from dialog import LoginDialog
from dialog import AddPlaylistDialog
from dialog import RenamePlaylistDialog
from dialog import AddToPlaylistDialog

from download import DownloadDialog

import gettext

_ = gettext.gettext
APPNAME = "rhythmbox-baidu-music"
gettext.install(APPNAME, RB.locale_dir())
gettext.textdomain(APPNAME)

# icon files
BAIDU_MUSIC_ICON = "images/baidu-music.png"
COLLECT_ICON = "images/collect.png"
HQ_ICON = "images/hq.png"

# ui files
POPUP_UI = "popup-ui.xml"
SEARCH_UI = "search.ui"
PREFS_UI = "baidu-music-prefs.ui"


class BaiduMusicPlugin(GObject.Object, Peas.Activatable):
    __gtype_name__ = "BaiduMusicPlugin"
    object = GObject.property(type=GObject.GObject)

    def __init__(self):
        super(BaiduMusicPlugin, self).__init__()

    def do_activate(self):
        print "Baidu Music Plugin activated."

        self.settings = Gio.Settings("org.gnome.rhythmbox.plugins.baidu-music")

        shell = self.object
        self.db = shell.props.db

        self.entry_type = BaiduMusicEntryType(self.db)
        self.db.register_entry_type(self.entry_type)

        self.playlists = {}

        self.__set_sources()
        self.__set_client()
        self.__set_ui_manager()

        if self.client.islogin:
            self.__set_playlists()

        self.__search_window = None

        self.__set_ui_status()

    def do_deactivate(self):
        print "Baidu Music Plugin is deactivated"

        shell = self.object

        # remove the ui toolbar
        manager = shell.props.ui_manager
        manager.remove_ui(self.ui_id)
        manager.remove_action_group(self.action_group)
        self.ui_id = None
        self.action_group = None

        # remove the search window
        if self.__search_window:
            self.__search_window.destroy()
            self.__search_window = None

        # delete sources
        self.collect_source.delete_thyself()
        self.collect_source = None
        self.temp_source.delete_thyself()
        self.temp_source = None

        # delete playlists
        playlists = self.playlists.values()
        for playlist in playlists:
            playlist.delete_thyself()
        self.playlists = None

        # delete page_group
        self.playlist_page_group.delete_thyself()
        self.playlist_page_group = None
        self.page_group.delete_thyself()
        self.page_group = None

        # delete some variables
        self.db = None
        self.entry_type = None

        self.settings = None
        self.client = None

    def __set_sources(self):
        """ setup the sources includes collect, temp """
        shell = self.object

        # Add icon to the collect source
        theme = Gtk.IconTheme.get_default()
        what, width, height = Gtk.icon_size_lookup(Gtk.IconSize.LARGE_TOOLBAR)

        # create a page group
        page_group = RB.DisplayPageGroup.get_by_id("baidu-music")
        if not page_group:
            page_group = RB.DisplayPageGroup(
                    shell=shell,
                    id="baidu-music",
                    name=_("Baidu Music"),
                    category=RB.DisplayPageGroupType.TRANSIENT,
                    )
        shell.append_display_page(page_group, None)
                #RB.DisplayPageGroup.get_by_id("stores"))

        # create the temp source
        self.temp_source = GObject.new(
                TempSource,
                name=_("Temporary"),
                shell=shell,
                plugin=self,
                entry_type=self.entry_type,
                settings=self.settings.get_child("source"),
                toolbar_path="/TempSourceToolbar",
                is_local=False,
                )
        icon = Gtk.IconTheme.get_default().load_icon(
                "audio-x-generic", width,
                Gtk.IconLookupFlags.GENERIC_FALLBACK)
        #icon = GdkPixbuf.Pixbuf.new_from_file_at_size(
                #rb.find_plugin_file(self, TEMP_ICON), width, height
                #)
        self.temp_source.set_property("pixbuf", icon)
        shell.append_display_page(self.temp_source, page_group)

        # create the collect source
        self.collect_source = GObject.new(
                CollectSource,
                name=_("My Collect"),
                shell=shell,
                plugin=self,
                entry_type=self.entry_type,
                settings=self.settings.get_child("source"),
                toolbar_path="/CollectSourceToolbar",
                is_local=False,
                )
        icon = GdkPixbuf.Pixbuf.new_from_file_at_size(
                rb.find_plugin_file(self, COLLECT_ICON), width, height
                )
        self.collect_source.set_property("pixbuf", icon)
        shell.append_display_page(self.collect_source, page_group)
        shell.register_entry_type_for_source(self.collect_source, self.entry_type)

        # Add a page_group which includes all online playlists
        playlist_page_group = RB.DisplayPageGroup.get_by_id("baidu-music-playlists")
        if not playlist_page_group:
            playlist_page_group = RB.DisplayPageGroup(
                    shell=shell,
                    id="baidu-music-playlists",
                    name=_("Online Playlists"),
                    category=RB.DisplayPageGroupType.TRANSIENT,
                    )
        icon = Gtk.IconTheme.get_default().load_icon(
                "audio-x-mp3-playlist", width,
                Gtk.IconLookupFlags.GENERIC_FALLBACK)
        #icon = GdkPixbuf.Pixbuf.new_from_file_at_size(
                #rb.find_plugin_file(self, PLAYLIST_ICON), width, height
                #)
        playlist_page_group.set_property("pixbuf", icon)
        shell.append_display_page(playlist_page_group, page_group)

        self.page_group = page_group
        self.playlist_page_group = playlist_page_group

    def __get_playlists(self):
        """ Get all online playlists. """
        havemore, result = 1, []
        if self.client.islogin:
            while havemore:
                havemore, total, playlists = self.client.get_playlists()
                result.extend(playlists)
        return result

    def __set_playlists(self):
        """ Setup all online playlists. """
        playlists = self.__get_playlists()
        for playlist in playlists:
            self.__set_playlist(playlist)

    def __set_playlist(self, playlist):
        """ Setup a online playlist.

        Args:
            playlist: A dict includes id and title.
        """
        shell = self.object

        playlist_source = GObject.new(
                OnlinePlaylistSource,
                name=playlist["title"],
                shell=shell,
                plugin=self,
                entry_type=self.entry_type,
                settings=self.settings.get_child("source"),
                toolbar_path="/OnlinePlaylistSourceToolbar",
                is_local=False,
                )
        playlist_source.playlist_id = playlist["id"]
        playlist_source.set_property("pixbuf", None)
        shell.append_display_page(playlist_source, self.playlist_page_group)
        self.playlists[playlist["id"]] = playlist_source

    def __set_client(self):
        """ setup the client api """
        cache_dir = RB.find_user_cache_file("baidu-music")
        if not os.path.isdir(cache_dir):
            os.mkdir(cache_dir)
        cookie =  RB.find_user_cache_file("baidu-music/cookie")

        self.client = Client(cookie, debug=False)
        username = self.settings.get_string("username")
        password = self.settings.get_string("password")
        if username and password and not self.client.islogin:
            try:
                self.client.login(username, password)
            except Exception, e:
                self.settings["username"] = ""
                self.settings["password"] = ""

        BaseSource.client = self.client
        self.entry_type.client = self.client

    def __set_ui_manager(self):
        """ Setup the ui manager. """
        shell = self.object

        # setup the menu in the source
        manager = shell.props.ui_manager
        popup_file = rb.find_plugin_file(self, POPUP_UI)
        self.ui_id = manager.add_ui_from_file(popup_file)
        self.action_group = Gtk.ActionGroup(name="BaiduMusicPluginActions")

        # the search action
        action = Gtk.Action(
                name="BaiduMusicSearchAction",
                label=_("Search Music"),
                tooltip=_("Search music from the baidu music."),
                stock_id=None
                )
        icon = Gio.FileIcon.new(Gio.File.new_for_path(
            rb.find_plugin_file(self, BAIDU_MUSIC_ICON)
            ))
        action.set_gicon(icon)
        action.connect("activate", self.__action_search)
        self.action_group.add_action(action)

        # the user login or logout action
        if self.client.islogin:
            action = Gtk.Action(
                    name="BaiduMusicLoginAction",
                    label=_("Logout"),
                    tooltip=_("Sign out the baidu music."),
                    stock_id=None
                    )
        else:
            action = Gtk.Action(
                    name="BaiduMusicLoginAction",
                    label=_("Login"),
                    tooltip=_("Sign in the baidu music."),
                    stock_id=None
                    )
        action.connect("activate", self.__action_user)
        self.action_group.add_action(action)

        # the Refresh action
        action = Gtk.Action(
                name="BaiduMusicRefreshAction",
                label=_("Refresh"),
                tooltip=_("Refresh the song list."),
                stock_id=None
                )
        action.connect("activate", lambda a: shell.props.selected_page.refresh())
        self.action_group.add_action(action)

        # the test action
        action = Gtk.Action(
                name="BaiduMusicTestAction",
                label=_("Test"),
                tooltip=_("Test"),
                stock_id=None
                )
        action.connect("activate", lambda a: shell.props.selected_page.test())
        self.action_group.add_action(action)

        # the collect action
        action = Gtk.Action(
                name="BaiduMusicCollectAction",
                label=_("Collect"),
                tooltip=_("Collect all selected songs."),
                stock_id=None
                )
        action.connect("activate", self.__action_collect)
        self.action_group.add_action(action)

        # the action about adding a playlist
        action = Gtk.Action(
                name="BaiduMusicPlaylistAddAction",
                label=_("New playlist"),
                tooltip=_("Add new online playlist."),
                stock_id=None
                )
        action.connect("activate", self.__action_add_playlist)
        self.action_group.add_action(action)

        # the action about renaming a playlist
        action = Gtk.Action(
                name="BaiduMusicPlaylistRenameAction",
                label=_("Rename"),
                tooltip=_("Rename the title of playlist."),
                stock_id=None
                )
        action.connect("activate", self.__action_rename_playlist)
        self.action_group.add_action(action)

        # the action about deleting a playlist
        action = Gtk.Action(
                name="BaiduMusicPlaylistDeleteAction",
                label=_("Delete playlist"),
                tooltip=_("Delete this playlist."),
                stock_id=None
                )
        action.connect("activate", self.__action_delete_playlist)
        self.action_group.add_action(action)

        # the action about adding songs to a playlist
        action = Gtk.Action(
                name="BaiduMusicAddAction",
                label=_("Add"),
                tooltip=_("Add songs to a online playlist."),
                stock_id=None
                )
        action.connect("activate", self.__action_add_to_playlist)
        self.action_group.add_action(action)

        # the action about toggling the hq status
        action = Gtk.ToggleAction(
                name="BaiduMusicSwitchAction",
                label=_("HQ"),
                tooltip=_("Switch to HQ music or not."),
                stock_id=None
                )
        icon = Gio.FileIcon.new(Gio.File.new_for_path(
            rb.find_plugin_file(self, HQ_ICON)
            ))
        action.set_gicon(icon)
        action.set_active(self.settings.get_boolean("hq"))
        action.connect("toggled", self.__action_toggle_hq)
        self.action_group.add_action(action)

        # the action about download songs
        action = Gtk.Action(
                name="BaiduMusicDownloadAction",
                label=_("Download"),
                tooltip=_("Download songs to the local disk."),
                stock_id=None
                )
        action.connect("activate", self.__action_download)
        self.action_group.add_action(action)

        manager.insert_action_group(self.action_group, 0)
        manager.ensure_update()

    def __set_ui_status(self):
        """ Setup the status of all button and menu. """
        shell = self.object
        manager = shell.props.ui_manager

        widgets = [
                #manager.get_widget("/TempSourceToolbar/BaiduMusicCollect"),
                #manager.get_widget("/TempSourceToolbar/BaiduMusicAdd"),
                manager.get_widget("/CollectSourceToolbar/BaiduMusicRefresh"),
                #manager.get_widget("/CollectSourceToolbar/BaiduMusicAdd"),
                manager.get_widget("/CollectSourcePopup/BaiduMusicRefresh"),
                manager.get_widget("/CollectSourcePopup/BaiduMusicPlaylistAdd"),
                manager.get_widget("/TempSourcePopup/BaiduMusicPlaylistAdd"),
                ]
        for widget in widgets:
            widget.set_sensitive(self.client.islogin)

    def __action_search(self, widget):
        """ Show the search box window """
        if not self.__search_window:
            builder = Gtk.Builder()
            builder.set_translation_domain(APPNAME)
            builder.add_from_file(rb.find_plugin_file(self, SEARCH_UI))

            self.__search_window = builder.get_object("search_window")
            self.__search_window.set_icon_from_file(
                    rb.find_plugin_file(self, BAIDU_MUSIC_ICON)
                    )
            # do not delete window
            self.__search_window.connect("delete_event",
                    lambda w, e: w.hide() or True)
            builder.connect_signals(
                    SearchHandle(
                        builder=builder,
                        collect_source=self.collect_source,
                        temp_source=self.temp_source,
                        client=self.client,
                        playlists=self.playlists,
                        )
                    )
        self.__search_window.show_all()

    def __action_user(self, widget):
        """ Login or logout action. """
        if self.client.islogin:
            self.__action_logout(widget)
        else:
            self.__action_login(widget)
        self.__set_ui_status()

    def __action_login(self, widget):
        """ Login action. """
        # create the login dialog
        dialog = LoginDialog()
        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            username = dialog.username_entry.get_text().strip()
            password = dialog.password_entry.get_text().strip()
            if username and password:
                try:
                    self.client.login(username, password)
                    # setup the username and the password
                    self.settings["username"] = username
                    self.settings["password"] = password

                    self.collect_source.load()
                    self.__set_playlists()

                    widget.set_label(_("Logout"))
                    widget.set_tooltip(_("Sign out the baidu music."))
                except Exception as e:
                    print e
        elif response == Gtk.ResponseType.CANCEL:
            pass
        dialog.destroy()

    def __action_logout(self, widget):
        """ Logout action. """
        # create the logout dialog
        dialog = Gtk.MessageDialog(
                None, 0, Gtk.MessageType.QUESTION,
                Gtk.ButtonsType.OK_CANCEL,
                _("Logout confirm")
                )
        dialog.format_secondary_text(_("Are you sure you want to logout?"))

        response = dialog.run()

        if response == Gtk.ResponseType.OK and self.client.logout():
            # clean up the username and password
            self.settings["username"] = ""
            self.settings["password"] = ""
            # clear all entries in all sources
            self.collect_source.clear()
            # delete all online playlists
            playlists = self.playlists.values()
            for playlist in playlists:
                playlist.delete_thyself()
            self.playlists = {}
            # setup the widget
            widget.set_label(_("Login"))
            widget.set_tooltip(_("Sign in the baidu music."))
        dialog.destroy()

    def __action_collect(self, widget):
        """ Add songs to the collect list. """
        shell = self.object
        entry_view = shell.props.selected_page.get_entry_view()
        entries = entry_view.get_selected_entries()
        song_ids = [int(entry.get_string(RB.RhythmDBPropType.LOCATION)[6:]) \
                for entry in entries]
        song_ids = self.client.add_collect_songs(song_ids)
        if self.collect_source.activated and song_ids:
            song_ids = [song_ids] if isinstance(song_ids, int) else song_ids
            songs = self.client.get_song_info(song_ids)
            songs.reverse()
            self.collect_source.add(songs)

    def __action_add_playlist(self, widget):
        """ Add a playlist with custom title. """
        dialog = AddPlaylistDialog()
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            title = dialog.title_entry.get_text().strip()
            if title != "":
                playlist_id = self.client.add_playlist(title)
                if playlist_id:
                    self.__set_playlist({
                        "id": playlist_id,
                        "title": title
                        })
        elif response == Gtk.ResponseType.CANCEL:
            pass
        dialog.destroy()

    def __action_rename_playlist(self, widget):
        """ Rename a playlist. """
        shell = self.object
        old_title = shell.props.selected_page.get_property("name")

        dialog = RenamePlaylistDialog()
        dialog.old_title_entry.set_text(old_title)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            title = dialog.title_entry.get_text().strip()
            if old_title != title:
                result = self.client.rename_playlist(
                        shell.props.selected_page.playlist_id, title
                        )
                if result:
                    shell.props.selected_page.set_property("name", title)
        elif response == Gtk.ResponseType.CANCEL:
            pass
        dialog.destroy()

    def __action_delete_playlist(self, widget):
        """ Delete a playlist. """
        shell = self.object
        playlist_id = shell.props.selected_page.playlist_id
        dialog = Gtk.MessageDialog(None, 0, Gtk.MessageType.QUESTION,
            Gtk.ButtonsType.OK_CANCEL, _("Delete confirm"))
        dialog.format_secondary_text(
                _("Are you sure you want to delete this playlist?")
                )
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            if self.client.delete_playlist(playlist_id):
                playlist = self.playlists[playlist_id]
                playlist.delete_thyself()
                del self.playlists[playlist_id]
        elif response == Gtk.ResponseType.CANCEL:
            pass
        dialog.destroy()

    def __action_add_to_playlist(self, widget):
        """ Add songs to a online playlist. """
        shell = self.object
        source = shell.props.selected_page

        try:
            skip_id = source.playlist_id
        except Exception, e:
            skip_id = ""
        entries = source.get_entry_view().get_selected_entries()
        if not entries:
            return False
        song_ids = [int(entry.get_string(RB.RhythmDBPropType.LOCATION)[6:]) \
                for entry in entries]

        dialog = AddToPlaylistDialog(self.playlists, song_ids, str(skip_id))
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            playlist_id = dialog.playlist_id
            if playlist_id:
                songs_ids = self.client.add_playlist_songs(
                        playlist_id, song_ids
                        )
                songs = self.client.get_song_info(song_ids)
                songs.reverse()
                self.playlists[playlist_id].add(songs)
        elif response == Gtk.ResponseType.CANCEL:
            pass
        dialog.destroy()

    def __action_toggle_hq(self, widget):
        self.settings["hq"] = widget.get_active()

    def __action_download(self, widget):
        shell = self.object
        entry_view = shell.props.selected_page.get_entry_view()
        entries = entry_view.get_selected_entries()
        song_ids = [int(entry.get_string(RB.RhythmDBPropType.LOCATION)[6:]) \
                for entry in entries]
        songs = self.client.get_song_links(song_ids, True, True)

        dialog = DownloadDialog(song_ids, self.client)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            songs_list = dialog.get_songs_list()
            print songs_list
        elif response == Gtk.ResponseType.CANCEL:
            pass
        dialog.destroy()


class BaiduMusicEntryType(RB.RhythmDBEntryType):

    def __init__(self, db):
        super(BaiduMusicEntryType, self).__init__(
                db=db,
                name="baidu-music-entry-type",
                )
        self.settings = Gio.Settings("org.gnome.rhythmbox.plugins.baidu-music")
        self.client = None

    def do_get_playback_uri(self, entry):
        db = self.props.db
        song_id = entry.get_string(RB.RhythmDBPropType.LOCATION)[6:]
        artist = entry.get_string(RB.RhythmDBPropType.ARTIST)
        title = entry.get_string(RB.RhythmDBPropType.TITLE)
        songinfo = self.client.get_song_links(
                [song_id], False, self.settings.get_boolean("hq")
                )
        song = songinfo[0]["file_list"][0]
        lyric = songinfo[0]["lyric_url"]

        db.entry_set(entry, RB.RhythmDBPropType.DURATION, song["duration"])
        db.entry_set(entry, RB.RhythmDBPropType.FILE_SIZE, song["size"])
        db.entry_set(entry, RB.RhythmDBPropType.BITRATE, song["kbps"])

        def save_lyric_cb(data):
            path = os.path.expanduser(self.settings["lyric-path"])
            filename = "%s-%s.lrc" % (artist, title)
            with open(os.path.join(path, filename), "wb") as lyric:
                lyric.write(data)
                lyric.close()

        if lyric:
            loader =  rb.Loader()
            loader.get_url(lyric, save_lyric_cb)

        return song["url"]

    def do_can_sync_metadata(self, entry):
        return True

    def do_sync_metadata(self, entry, changes):
        return


class BaiduMusicConfigDialog(GObject.Object, PeasGtk.Configurable):
    __gtype_name__ = "BaiduMusicConfigDialog"
    object = GObject.property(type=GObject.Object)

    def do_create_configure_widget(self):

        self.settings = Gio.Settings("org.gnome.rhythmbox.plugins.baidu-music")

        builder = Gtk.Builder()
        builder.set_translation_domain(APPNAME)
        builder.add_from_file(rb.find_plugin_file(self, PREFS_UI))
        self.config_dialog = builder.get_object("config")

        self.lyricdir_entry = builder.get_object("lyricdir_entry")
        self.lyricdir_entry.set_text(self.settings["lyric-path"])

        self.lyricdir_button = builder.get_object("lyricdir_button")
        self.lyricdir_button.connect("clicked", self.lyricdir_clicked_cb)

        return self.config_dialog

    def lyricdir_clicked_cb(self, widget):
        dialog = Gtk.FileChooserDialog(_("Please choose a folder"),
                self.config_dialog.get_toplevel(),
                Gtk.FileChooserAction.SELECT_FOLDER,
                (
                    Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                    Gtk.STOCK_OK, Gtk.ResponseType.OK
                ))
        dialog.set_default_size(800, 400)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            lyricdir = dialog.get_filename()
            self.lyricdir_entry.set_text(lyricdir)
            self.settings["lyric-path"] = lyricdir
        elif response == Gtk.ResponseType.CANCEL:
            pass

        dialog.destroy()
