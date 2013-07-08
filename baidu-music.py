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

username = ""
password = ""
cookie = os.environ['HOME']+'/baidumusic.cookie'

class BaiduMusicPlugin(GObject.Object, Peas.Activatable):
    __gtype_name__ = "BaiduMusicPlugin"
    object = GObject.property(type=GObject.GObject)

    def __init__(self):
        super(BaiduMusicPlugin, self).__init__()

    def do_activate(self):
        print "Baidu Music Plugin activated."

        shell = self.object
        self.db = shell.props.db

        self.entry_type = BaiduMusicEntryType(self.db)
        self.db.register_entry_type(self.entry_type)

        self.query_model = RB.RhythmDBQueryModel.new_empty(self.db)

        # Add icon to the collect source
        #theme = Gtk.IconTheme.get_default()
        #what, width, height = Gtk.icon_size_lookup(Gtk.IconSize.LARGE_TOOLBAR)
        #icon = GdkPixbuf.Pixbuf.new_from_file_at_size(
                #rb.find_plugin_file(self, "favorite.png"), width, height)

        self.source = GObject.new(
                BaiduMusicSource,
                name=_("Baidu Music"),
                shell=shell,
                plugin=self,
                entry_type=self.entry_type,
                query_model=self.query_model,
                #pixbuf=icon,
                #settings=settings,
                #toolbar_path="/CloudToolbar",
                )
        shell.append_display_page(self.source,
                RB.DisplayPageGroup.get_by_id("library"))
        shell.register_entry_type_for_source(self.source, self.entry_type)

        # init the api class
        self.client = Client(cookie, debug=False)
        if username and password:
            self.client.login(username, password)

        self.source.client = self.client
        self.entry_type.client = self.client

    def do_deactivate(self):
        print "Baidu Music Plugin is deactivated"

        shell = self.object

        #self.db.entry_delete_by_type(self.entry_type)
        #self.db.commit()

        self.db = None
        self.query_model = None
        self.entry_type = None

        # delete the source
        self.source.delete_thyself()
        self.source = None

        self.client = None

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
