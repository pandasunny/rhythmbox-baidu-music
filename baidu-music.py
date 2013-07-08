# -*- coding: utf-8 -*-
import os
import rb
from gi.repository import GObject
from gi.repository import Gio
from gi.repository import RB
from gi.repository import Peas
from gi.repository import Gtk
from gi.repository import GdkPixbuf
#from source import BaiduMusicSource


class BaiduMusicPlugin(GObject.Object, Peas.Activatable):
    __gtype_name__ = "BaiduMusicPlugin"
    object = GObject.property(type=GObject.GObject)

    def __init__(self):
        super(BaiduMusicPlugin, self).__init__()

    def do_activate(self):
        print "Baidu Music Plugin activated."

        shell = self.object
        self.db = shell.props.db

        self.entry_type = BaiduMusicEntryType()
        self.db.register_entry_type(self.entry_type)

    def do_deactivate(self):
        print "Baidu Music Plugin is deactivated"


class BaiduMusicEntryType(RB.RhythmDBEntryType):

    def __init__(self):
        super(BaiduMusicEntryType, self).__init__(
                name="baidu-music-entry-type"
                )

    def do_can_sync_metadata(self, entry):
        return True
