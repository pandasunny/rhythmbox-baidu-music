# -*- coding: utf-8 -*-
from gi.repository import GObject
from gi.repository import GLib
from gi.repository import RB


class BaiduMusicSource(RB.BrowserSource):

    def __init__(self):
        super(BaiduMusicSource, self).__init__()

        self.client = None
        self.__activated = False
        #self.__updating = False
        #self.__load_progress = (0, 0)

        self.__albumart = {}
        self.__art_store = RB.ExtDB(name="album-art")
        self.__req_id = self.__art_store.connect("request", self.__album_art_requested)

    def do_selected(self):
        #settings=self.settings.get_child("source")
        if not self.__activated:
            self.props.settings.set_value("sorting", GLib.Variant("(sb)", ("EntryId", True)))

            entry_view = self.get_entry_view()
            entry_view.get_column(RB.EntryViewColumn.TRACK_NUMBER).set_visible(False)
            entry_view.get_column(RB.EntryViewColumn.GENRE).set_visible(False)
            entry_view.get_column(RB.EntryViewColumn.DURATION).set_visible(False)

            self.load()
            self.__activated = True

    #def do_get_status(self, status, progress_text, progress):
        #if self.__updating:
            #complete, total = self.__load_progress
            #if total > 0:
                #progress = min(float(complete) / total, 1.0)
            #else:
                #progress = -1.0
            #return (_("Loading collect songs"), None, progress)
        #else:
            #qm = self.props.query_model
            #return (qm.compute_status_normal("%d song", "%d songs"), None, 2.0)

    def do_add_uri(self):
        return False

    def do_impl_can_add_to_queue(self):
        return False

    def do_impl_can_cut(self):
        return False

    def do_impl_can_copy(self):
        return False

    def do_impl_can_delete(self):
        return True

    def do_impl_can_move_to_trash(self):
        return False

    def do_impl_can_paste(self):
        return False

    def do_impl_can_rename(self):
        return False

    def do_impl_delete(self):
        entry_view = self.get_entry_view()
        entries = entry_view.get_selected_entries()
        song_ids = [entry.dup_string(RB.RhythmDBPropType.LOCATION) \
                for entry in entries]
        if self.client.remove_favorite_songs(song_ids):
            for entry in entries:
                self.props.query_model.remove_entry(entry)

    def do_delete_thyself(self):
        #db = self.props.shell.props.db
        #db.entry_delete_by_type(self.props.entry_type)
        #db.commit()
        self.__art_store.disconnect(self.__req_id)
        self.__req_id = None
        self.__art_store = None
        RB.BrowserSource.delete_thyself(self)

    def __album_art_requested(self, store, key, last_time):
        album = key.get_field("album").decode("utf-8")
        artist = key.get_field("artist").decode("utf-8")
        uri = self.__albumart[artist+album] \
                if artist+album in self.__albumart else None
        if uri:
            print('album art uri: %s' % uri)
            storekey = RB.ExtDBKey.create_storage("album", album)
            storekey.add_field("artist", artist)
            store.store_uri(storekey, RB.ExtDBSourceType.SEARCH, uri)

    def __add_songs(self, songs):
        db = self.props.shell.props.db
        for song in songs:
            entry = RB.RhythmDBEntry.new(
                db, self.props.entry_type, song["songId"]
                )
            db.entry_set(
                    entry, RB.RhythmDBPropType.TITLE,
                    song["songName"].encode("utf-8")
                    )
            db.entry_set(
                    entry, RB.RhythmDBPropType.ARTIST,
                    song["artistName"].encode("utf-8")
                    )
            db.entry_set(
                    entry, RB.RhythmDBPropType.ALBUM,
                    song["albumName"].encode("utf-8")
                    )
            self.props.query_model.add_entry(entry, -1)

            if song["songPicBig"]:
                albumart = song["songPicBig"]
            elif song["songPicRadio"]:
                albumart = song["songPicRadio"]
            else:
                albumart = song["songPicSmall"]
            self.__albumart[song["artistName"]+song["albumName"]] = albumart

        db.commit()

    def load(self):
        start, size = (0, 50)
        collect_list = []
        if self.client.islogin:
            #self.__updating = True
            song_ids = self.client.get_collect_ids(size, start)
            #self.__load_progress = (len(song_ids), self.client.total)
            collect_list = self.client.get_song_info(song_ids)
            #collect_list.extend(self.client.get_song_info(song_ids))
            start = start + size
            #self.__load_progress = (start, self.client.total)
            self.__add_songs(collect_list)
            while start < self.client.total:
                song_ids = self.client.get_collect_ids(size, start)
                collect_list = self.client.get_song_info(song_ids)
                #collect_list.extend(self.client.get_song_info(song_ids))
                start = start + size
                #self.__load_progress = (start, self.client.total)
                self.__add_songs(collect_list)
            #self.__updating = False

    def clear(self):
        db = self.props.shell.props.db
        if not self.client.islogin:
            for row in self.props.query_model:
                entry = row[0]
                self.props.query_model.remove_entry(entry)
                db.entry_delete(entry)

GObject.type_register(BaiduMusicSource)
