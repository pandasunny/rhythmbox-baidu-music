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
from gi.repository import RB
from gi.repository import Peas
from gi.repository import Gtk
from gi.repository import GdkPixbuf

from client import Client
from source import BaseSource
from source import CollectSource
from source import TempSource
from search import SearchHandle
from dialog import LoginDialog

import gettext

APPNAME = "rhythmbox-baidu-music"
gettext.install(APPNAME, RB.locale_dir())

POPUP_UI = """
<ui>
  <toolbar name="CollectSourceToolbar">
    <toolitem name="BaiduMusicLogin" action="BaiduMusicLoginAction"/>
    <toolitem name="Browse" action="ViewBrowser"/>
    <toolitem name="BaiduMusicSearch" action="BaiduMusicSearchAction"/>
    <toolitem name="BaiduMusicSync" action="BaiduMusicSyncAction"/>
    <!-- <toolitem name="BaiduMusicTest" action="BaiduMusicTestAction"/> -->
  </toolbar>
  <toolbar name="TempSourceToolbar">
    <toolitem name="Browse" action="ViewBrowser"/>
    <toolitem name="BaiduMusicSearch" action="BaiduMusicSearchAction"/>
    <toolitem name="BaiduMusicCollect" action="BaiduMusicCollectAction"/>
    <!-- <toolitem name="BaiduMusicTest" action="BaiduMusicTestAction"/> -->
  </toolbar>
  <popup name="CollectSourcePopup">
    <menuitem name="BaiduMusicSync" action="BaiduMusicSyncAction"/>
  </popup>
</ui>
"""


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

        self.__set_sources()
        self.__set_client()
        self.__set_ui_manager()

        self.__search_window = None

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

        # delete some variables
        self.db = None
        self.entry_type = None

        self.settings = None
        self.client = None

    def __set_sources(self):

        shell = self.object

        # Add icon to the collect source
        theme = Gtk.IconTheme.get_default()
        what, width, height = Gtk.icon_size_lookup(Gtk.IconSize.LARGE_TOOLBAR)

        # create a page group
        baidu_icon = GdkPixbuf.Pixbuf.new_from_file_at_size(
                rb.find_plugin_file(self, "music.png"), width, height)

        page_group = RB.DisplayPageGroup(
                shell=shell,
                id="baidu-music",
                name=_("Baidu Music"),
                pixbuf=baidu_icon,
                category=RB.DisplayPageGroupType.TRANSIENT,
                )
        shell.append_display_page(page_group,
                RB.DisplayPageGroup.get_by_id("stores"))

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
        shell.append_display_page(self.temp_source, page_group)

        # create the collect source
        collect_icon = GdkPixbuf.Pixbuf.new_from_file_at_size(
                rb.find_plugin_file(self, "favorite.png"), width, height)
        self.collect_source = GObject.new(
                CollectSource,
                name=_("Collect"),
                shell=shell,
                plugin=self,
                entry_type=self.entry_type,
                settings=self.settings.get_child("source"),
                toolbar_path="/CollectSourceToolbar",
                is_local=False,
                )
        self.collect_source.set_property("pixbuf", collect_icon)
        shell.append_display_page(self.collect_source, page_group)
        #shell.register_entry_type_for_source(self.collect_source, self.entry_type)

    def __set_client(self):

        # init the api class
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

        shell = self.object

        # setup the menu in the source
        manager = shell.props.ui_manager
        self.ui_id = manager.add_ui_from_string(POPUP_UI)
        self.action_group = Gtk.ActionGroup(name="BaiduMusicPluginActions")

        # the search action
        action = Gtk.Action(
                name="BaiduMusicSearchAction",
                label=_("Search"),
                tooltip=_("Search music from the baidu music."),
                stock_id=Gtk.STOCK_FIND
                )
        action.connect("activate", self.__search_music)
        self.action_group.add_action(action)

        # the login action
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
        action.connect("activate", self.__login_action)
        self.action_group.add_action(action)

        # the sync action
        action = Gtk.Action(
                name="BaiduMusicSyncAction",
                label=_("Synchronize"),
                tooltip=_("Synchronize data."),
                stock_id=None
                )
        action.connect("activate", lambda a: shell.props.selected_page.sync())
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
        action.connect("activate", self.__collect_songs)
        self.action_group.add_action(action)

        manager.insert_action_group(self.action_group, 0)
        manager.ensure_update()

    def __search_music(self, widget):

        if not self.__search_window:
            builder = Gtk.Builder()
            builder.set_translation_domain(APPNAME)
            builder.add_from_file(rb.find_plugin_file(self, "search.ui"))

            self.__search_window = builder.get_object("search_window")
            self.__search_window.set_icon_from_file(
                    rb.find_plugin_file(self, "music.png")
                    )
            self.__search_window.connect("delete_event",
                    lambda w, e: w.hide() or True)

            builder.connect_signals(
                    SearchHandle(
                        builder = builder,
                        collect_source = self.collect_source,
                        temp_source = self.temp_source,
                        client = self.client
                        )
                    )

        self.__search_window.show_all()

    def __login_action(self, widget):
        if self.client.islogin:
            # logout function
            dialog = Gtk.MessageDialog(None, 0, Gtk.MessageType.QUESTION,
                Gtk.ButtonsType.OK_CANCEL, _("Logout confirm"))
            dialog.format_secondary_text(_("Are you sure you want to logout?"))
            response = dialog.run()
            if response == Gtk.ResponseType.OK:
                self.client.logout()
                if not self.client.islogin:
                    self.settings["username"] = ""
                    self.settings["password"] = ""
                    self.collect_source.clear()
                    widget.set_label(_("Login"))
                    widget.set_tooltip(_("Sign in the baidu music."))
            dialog.destroy()
        else:
            # login function
            dialog = LoginDialog()
            response = dialog.run()
            if response == Gtk.ResponseType.OK:
                username = dialog.username_entry.get_text()
                password = dialog.password_entry.get_text()
                try:
                    self.client.login(username, password)
                    self.settings["username"] = username
                    self.settings["password"] = password
                    dialog.destroy()
                    self.collect_source.load()
                    widget.set_label(_("Logout"))
                    widget.set_tooltip(_("Sign out the baidu music."))
                except Exception as e:
                    print e

    def __collect_songs(self, widget):
        shell = self.object
        entry_view = shell.props.selected_page.get_entry_view()
        entries = entry_view.get_selected_entries()
        song_ids = [int(entry.get_string(RB.RhythmDBPropType.LOCATION)) \
                for entry in entries]
        songs = self.client.add_favorite_songs(song_ids)
        if self.collect_source.activated and songs:
            self.collect_source.add(songs)

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
        song_id = entry.get_string(RB.RhythmDBPropType.LOCATION)
        artist = entry.get_string(RB.RhythmDBPropType.ARTIST)
        title = entry.get_string(RB.RhythmDBPropType.TITLE)
        songinfo = self.client.get_song_links(
                [song_id], [artist], [title]
                )
        song = songinfo[0]["fileslist"][0]
        db.entry_set(entry, RB.RhythmDBPropType.DURATION, song["time"])
        db.entry_set(entry, RB.RhythmDBPropType.FILE_SIZE, song["size"])
        db.entry_set(entry, RB.RhythmDBPropType.BITRATE, song["rate"])

        def save_lyric_cb(data):
            path = os.path.expanduser(self.settings["lyric-path"])
            filename = "%s-%s.lrc" % (artist, title)
            with open(os.path.join(path, filename), "wb") as lyric:
                lyric.write(data)
                lyric.close()

        if song["lrcLink"]:
            loader =  rb.Loader()
            loader.get_url(song["lrcLink"], save_lyric_cb)

        return song["songLink"]

    def do_can_sync_metadata(self, entry):
        return True

    def do_sync_metadata(self, entry, changes):
        return
