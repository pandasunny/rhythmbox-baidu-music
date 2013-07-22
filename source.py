# -*- coding: utf-8 -*-
from gi.repository import GObject
from gi.repository import GLib
from gi.repository import Gdk
from gi.repository import RB


class BaiduMusicSource(RB.BrowserSource):

    def __init__(self):
        super(BaiduMusicSource, self).__init__()

        self.client = None

        # source's status
        self.__activated = False
        self.__updating_ids = False
        self.__updating_list = False
        self.__load_progress = (0, 0)

        # set up the coverart
        self.__albumart = {}
        self.__art_store = RB.ExtDB(name="album-art")
        self.__req_id = self.__art_store.connect(
                "request", self.__album_art_requested
                )

        # the collect songs' IDs
        self.__song_ids = []

    def do_selected(self):
        if not self.__activated:
            # init query model and db
            self.__query_model = self.props.query_model
            self.__db = self.__query_model.props.db

            # init the entry-view's settings
            self.props.settings.set_value(
                    "sorting", GLib.Variant("(sb)", ("EntryId", False))
                    )
            ev = self.get_entry_view()
            ev.get_column(RB.EntryViewColumn.TRACK_NUMBER).set_visible(False)
            ev.get_column(RB.EntryViewColumn.GENRE).set_visible(False)
            ev.get_column(RB.EntryViewColumn.DURATION).set_visible(False)

            # load the song list
            if self.client.islogin:
                self.load()

            self.__activated = True

    def do_get_status(self, status, progress_text, progress):
        if self.__updating_ids:
            complete, total = self.__load_progress
            if total > 0:
                progress = min(float(complete) / total, 1.0)
            else:
                progress = -1.0
            return (_("Loading song IDs ..."), None, progress)
        elif self.__updating_list:
            complete, total = self.__load_progress
            if total > 0:
                progress = min(float(complete) / total, 1.0)
            else:
                progress = -1.0
            return (_("Loading song list ..."), None, progress)
        else:
            qm = self.props.query_model
            return (qm.compute_status_normal("%d song", "%d songs"), None, 2.0)

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
        song_ids = [int(entry.dup_string(RB.RhythmDBPropType.LOCATION)) \
                for entry in entries]
        if self.client.remove_favorite_songs(song_ids):
            for entry in entries:
                self.__query_model.remove_entry(entry)
                self.__db.entry_delete(entry)
            self.__song_ids = filter(lambda x: x not in song_ids,
                    self.__song_ids)

    def do_delete_thyself(self):
        #db = self.props.query_model.props.db
        #db.entry_delete_by_type(self.props.entry_type)
        #db.commit()
        self.__albumart = None
        self.__art_store.disconnect(self.__req_id)
        self.__req_id = None
        self.__art_store = None

        self.__song_ids = None
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
        if not songs:
            return False

        for song in songs:
            entry = RB.RhythmDBEntry.new(
                    self.__db, self.props.entry_type, song["songId"]
                    )
            self.__db.entry_set(
                    entry, RB.RhythmDBPropType.TITLE,
                    song["songName"].encode("utf-8")
                    )
            self.__db.entry_set(
                    entry, RB.RhythmDBPropType.ARTIST,
                    song["artistName"].encode("utf-8")
                    )
            self.__db.entry_set(
                    entry, RB.RhythmDBPropType.ALBUM,
                    song["albumName"].encode("utf-8")
                    )
            self.__query_model.add_entry(entry, 0)

            if song["songPicBig"]:
                albumart = song["songPicBig"]
            elif song["songPicRadio"]:
                albumart = song["songPicRadio"]
            else:
                albumart = song["songPicSmall"]
            self.__albumart[song["artistName"]+song["albumName"]] = albumart

        self.__db.commit()

    def __get_song_ids(self):
        start, song_ids = 0, []
        while True:
            song_ids.extend(self.client.get_collect_ids(start))
            self.__load_progress = (start, self.client.total)
            start += 200
            if start >= self.client.total:
                song_ids.reverse()
                self.__updating_ids = False
                self.__updating_list = True
                break
        self.__load_progress = (start, self.client.total)
        return song_ids

    def __get_songs(self, song_ids):
        start, total, songs = 0, len(song_ids), []
        while start < total:
            songs.extend(self.client.get_song_info(song_ids[start:start+200]))
            self.__load_progress = (start, total)
            start += 200
        self.__load_progress = (start, total)
        self.__updating_list = False
        return songs

    def __load_cb(self, args):
        self.__song_ids = self.__get_song_ids()
        songs = self.__get_songs(self.__song_ids)
        self.__add_songs(songs)
        return False

    def load(self):
        self.__updating_ids = True
        self.__updating_list = False
        Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT_IDLE, self.__load_cb, [])

    def __sync_cb(self, args):
        song_ids = self.__get_song_ids()

        # checkout the added items and the deleted items
        add_ids = song_ids[:]   # the added items
        delete_ids = []         # the delete items
        for key, item in enumerate(self.__song_ids):
            index = key - len(delete_ids)
            if index >= len(song_ids) or song_ids[index] != item:
                delete_ids.append(item)
            elif song_ids[index] == item:
                add_ids.remove(item)
        add_ids.reverse()

        # traversal rows in the query model
        if delete_ids:
            for row in self.__query_model:
                entry = row[0]
                song_id = int(entry.get_string(RB.RhythmDBPropType.LOCATION))
                if song_id in delete_ids:
                    self.__query_model.remove_entry(entry)
                    self.__db.entry_delete(entry)

        if add_ids:
            songs = self.__get_songs(add_ids)
            self.__add_songs(songs)

        self.__song_ids = song_ids
        return False

    def sync(self):
        self.__updating_ids = True
        self.__updating_list = False
        Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT_IDLE, self.__sync_cb, [])

    def add(self, songs):
        if songs:
            songs.reverse()
            self.__add_songs(songs)

    def test(self):
        for row in self.__query_model:
            entry = row[0]
            print entry.get_ulong(RB.RhythmDBPropType.ENTRY_ID)
            print entry.get_string(RB.RhythmDBPropType.LOCATION)
            print entry.get_string(RB.RhythmDBPropType.TITLE)

    def clear(self):
        for row in self.__query_model:
            entry = row[0]
            self.__query_model.remove_entry(entry)
            self.__db.entry_delete(entry)

GObject.type_register(BaiduMusicSource)
