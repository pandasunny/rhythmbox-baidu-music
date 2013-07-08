# -*- coding: utf-8 -*-
from gi.repository import GObject
from gi.repository import RB

class BaiduMusicSource(RB.BrowserSource):

    def __init__(self):
        super(BaiduMusicSource, self).__init__()
        self.__activated = False

    def do_selected(self):
        if not self.__activated:
            entry_view = self.get_entry_view()
            entry_view.get_column(RB.EntryViewColumn.TRACK_NUMBER).set_visible(False)
            entry_view.get_column(RB.EntryViewColumn.GENRE).set_visible(False)
            entry_view.get_column(RB.EntryViewColumn.DURATION).set_visible(False)
            self.__activated = True

    def do_add_uri(self):
        return False

    def do_impl_can_cut(self):
        return False

    def do_impl_can_copy(self):
        return False

    def do_impl_can_delete(self):
        return True

    def do_impl_can_move_to_trash(self):
        return False


GObject.type_register(BaiduMusicSource)
