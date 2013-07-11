# -*- coding: utf-8 -*-
import os
import rb
from gi.repository import GObject
from gi.repository import Gio
from gi.repository import RB
from gi.repository import Peas
from gi.repository import Gtk
from gi.repository import GdkPixbuf
from client import Client
from source import BaiduMusicSource

cookie = os.environ['HOME']+'/baidumusic.cookie'

POPUP_UI = """
<ui>
  <toolbar name="SourceToolbar">
    <toolitem name="BaiduMusicLogin" action="BaiduMusicLoginAction"/>
    <toolitem name="Browse" action="ViewBrowser"/>
    <toolitem name="BaiduMusicSearch" action="BaiduMusicSearchAction"/>
    <toolitem name="BaiduMusicRefresh" action="BaiduMusicRefreshAction"/>
  </toolbar>
</ui>
"""


class BaiduMusicPlugin(GObject.Object, Peas.Activatable):
    __gtype_name__ = "BaiduMusicPlugin"
    object = GObject.property(type=GObject.GObject)

    def __init__(self):
        super(BaiduMusicPlugin, self).__init__()

    def do_activate(self):
        print "Baidu Music Plugin activated."

        self.settings = Gio.Settings("org.gnome.rhythmbox.plugins.baidumusic")

        shell = self.object
        self.db = shell.props.db

        self.entry_type = BaiduMusicEntryType(self.db)
        self.db.register_entry_type(self.entry_type)

        self.query_model = RB.RhythmDBQueryModel.new_empty(self.db)

        # Add icon to the collect source
        theme = Gtk.IconTheme.get_default()
        what, width, height = Gtk.icon_size_lookup(Gtk.IconSize.LARGE_TOOLBAR)
        icon = GdkPixbuf.Pixbuf.new_from_file_at_size(
                rb.find_plugin_file(self, "music.png"), width, height)

        self.source = GObject.new(
                BaiduMusicSource,
                name=_("Baidu Music"),
                shell=shell,
                plugin=self,
                entry_type=self.entry_type,
                query_model=self.query_model,
                pixbuf=icon,
                settings=self.settings.get_child("source"),
                toolbar_path="/SourceToolbar",
                )
        shell.append_display_page(self.source,
                RB.DisplayPageGroup.get_by_id("library"))
        shell.register_entry_type_for_source(self.source, self.entry_type)

        # init the api class
        self.client = Client(cookie, debug=False)
        username = self.settings.get_string("username")
        password = self.settings.get_string("password")
        if username and password:
            self.client.login(username, password)

        self.source.client = self.client
        self.entry_type.client = self.client

        # setup the menu in the source
        manager = shell.props.ui_manager
        self.ui_id = manager.add_ui_from_string(POPUP_UI)
        self.action_group = Gtk.ActionGroup(name="BaiduMusicPluginActions")

        action = Gtk.Action(
                name="BaiduMusicSearchAction",
                label=_("Search"),
                tooltip=_("Search music from baidu music."),
                stock_id=Gtk.STOCK_FIND
                )
        action.connect("activate", self.__search_music)
        self.action_group.add_action(action)

        if self.client.islogin:
            action = Gtk.Action(
                    name="BaiduMusicLoginAction",
                    label=_("Logout"),
                    tooltip=_("Log out the baidu music."),
                    stock_id=None
                    )
        else:
            action = Gtk.Action(
                    name="BaiduMusicLoginAction",
                    label=_("Login"),
                    tooltip=_("Log in the baidu music."),
                    stock_id=None
                    )
        action.connect("activate", self.__login_action)
        self.action_group.add_action(action)

        action = Gtk.Action(
                name="BaiduMusicSyncAction",
                label=_("Synchronize"),
                tooltip=_("Synchronize the collect data."),
                stock_id=None
                )
        action.connect("activate", self.__sync_data)
        self.action_group.add_action(action)

        manager.insert_action_group(self.action_group, 0)
        manager.ensure_update()

    def do_deactivate(self):
        print "Baidu Music Plugin is deactivated"

        shell = self.object

        # remove the ui toolbar
        manager = shell.props.ui_manager
        manager.remove_ui(self.ui_id)
        manager.remove_action_group(self.action_group)
        self.ui_id = None
        self.action_group = None

        #self.db.entry_delete_by_type(self.entry_type)
        #self.db.commit()

        self.db = None
        self.query_model = None
        self.entry_type = None

        # delete the source
        self.source.delete_thyself()
        self.source = None

        self.settings = None
        self.client = None

    def __search_music(self, widget):
        pass

    def __login_action(self, widget):
        pass

    def __sync_data(self, widget):
        pass


class BaiduMusicEntryType(RB.RhythmDBEntryType):

    def __init__(self, db):
        super(BaiduMusicEntryType, self).__init__(
                db=db,
                name="baidu-music-entry-type",
                #has-playlists=False
                )
        self.client = None

    def do_get_playback_uri(self, entry):
        db = self.props.db
        songinfo = self.client.get_song_links(
                entry.dup_string(RB.RhythmDBPropType.LOCATION).split("`"),
                entry.dup_string(RB.RhythmDBPropType.ARTIST).split("`"),
                entry.dup_string(RB.RhythmDBPropType.TITLE).split("`")
                )
        song = songinfo[0]["fileslist"][0]
        db.entry_set(entry, RB.RhythmDBPropType.DURATION, song["time"])
        db.entry_set(entry, RB.RhythmDBPropType.FILE_SIZE, song["size"])
        db.entry_set(entry, RB.RhythmDBPropType.BITRATE, song["rate"])
        return song["songLink"]

    def do_can_sync_metadata(self, entry):
        return True
