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

from __future__ import division

import os
import cPickle as pickle
import threading

from gi.repository import GObject
from gi.repository import GLib
from gi.repository import Gdk
from gi.repository import Gtk
from gi.repository import RB

import api as client

DELTA = 200
TEMP_PLAYLIST = "baidu-music/temp.pls"


class PlaylistGroup(RB.DisplayPage):

    def do_selectable(self):
        return False


class BaseSource(RB.StaticPlaylistSource):

    albumart = {}   # the coverart dict
    #client = None   # the client API

    def __init__(self):
        super(BaseSource, self).__init__()

        self.songs = []             # the song ids in this source
        self.activated = False      # the tag of activate
        self.popup = None           # the popup menu
        self.index = -1             # the index of position where insert song

        # get_status function
        self.updating = False       # the status of update
        self.status = ""            # the message of source's status
        self.progress = 0           # the progress of update

        self.entry_widgets = []     # a list includes the toolitems

        # set up the coverart
        self.__art_store = RB.ExtDB(name="album-art")
        self.__req_id = self.__art_store.connect(
                "request", self.__album_art_requested
                )

    def do_selected(self):
        if not self.activated:
            self.set_entry_view()
            # setup the source's status
            self.activated = True

    def do_show_popup(self):
        if self.activate and self.popup:
            self.popup.popup(None, None, None, None,
                    3, Gtk.get_current_event_time())

    def do_get_status(self, status, progress_text, progress):
        progress_text = None
        if self.updating:
            return (self.status, progress_text, self.progress)
        else:
            qm = self.get_query_model()
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

    def do_delete_thyself(self):

        # clean up the coverart function
        self.__art_store.disconnect(self.__req_id)
        self.__req_id = None
        self.__art_store = None

        # delete the variables
        self.songs = None
        self.popup = None

        RB.StaticPlaylistSource.delete_thyself(self)

    def __album_art_requested(self, store, key, last_time):
        """ Get the coverart of song. """

        album = key.get_field("album").decode("utf-8")
        artist = key.get_field("artist").decode("utf-8")
        uri = self.albumart[artist+album] \
                if artist+album in self.albumart else None
        if uri:
            print('album art uri: %s' % uri)
            storekey = RB.ExtDBKey.create_storage("album", album)
            storekey.add_field("artist", artist)
            store.store_uri(storekey, RB.ExtDBSourceType.SEARCH, uri)

    def __add_songs(self, songs):
        """ Create entries and commit.

        Args:
            songs: A list includes all songs.
            index: the index position of song.
        """
        if not songs or not self.activated:
            return False

        db = self.get_db()

        for song in songs:
            try:
                # create and add a entry
                entry = RB.RhythmDBEntry.new(
                        db, self.props.entry_type, "baidu/" + song["songId"]
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
                self.add_entry(entry, self.index)

                # setup the coverart uri
                if song["songPicBig"]:
                    albumart = song["songPicBig"]
                elif song["songPicRadio"]:
                    albumart = song["songPicRadio"]
                else:
                    albumart = song["songPicSmall"]
                self.albumart[song["artistName"]+song["albumName"]] = albumart
            except TypeError, e:
                self.add_location("baidu/" + song["songId"], self.index)
            except KeyError, e:
                pass

        db.commit()

    def add_songs(self, *args):
        """ The wrap of __add_songs function.

        Args:
            args: A list includes all args.
        """
        Gdk.threads_add_idle(
                GLib.PRIORITY_DEFAULT_IDLE,
                lambda args: self.__add_songs(*args),
                args
                )

    def set_entry_view(self):
        """ Setup the entry view of this source. """

        def do_selection_changed(entry_view, widgets):
            """ Setup the toolitems' status.

            Args:
                entry_view: the instance of RB.EntryView.
                widgets: the list includes all widgets' name.
            """
            status = entry_view.have_selection() and client.user.is_login
            manager = self.props.shell.props.ui_manager
            toolbar_path = self.props.toolbar_path
            for widget_path in widgets:
                widget = manager.get_widget(toolbar_path + "/" + widget_path)
                widget.set_sensitive(status)
            widget = manager.get_widget(
                    toolbar_path + "/" + "BaiduMusicDownload"
                    )
            widget.set_sensitive(entry_view.have_selection())

        ev = self.get_entry_view()
        ev.get_column(RB.EntryViewColumn.TRACK_NUMBER).set_visible(False)
        ev.get_column(RB.EntryViewColumn.GENRE).set_visible(False)
        do_selection_changed(ev, self.entry_widgets)
        ev.connect("selection-changed",do_selection_changed,
                self.entry_widgets)

    def get_songs(self, song_ids):
        """ Get all informations of songs.

        Args:
            song_ids: A list includes all songs' IDs.

        Returns:
            A list includes all informations.
        """
        self.status = _("Loading song list...")
        start, total, songs = 0, len(song_ids), []
        while start < total:
            songs.extend(client.common.GetSongInfo().run({
                "songIds": song_ids[start:start+DELTA],
                }))
            self.progress = start/total
            self.notify_status_changed()
            start += DELTA
        self.progress = start/total
        self.notify_status_changed()
        return songs

    def test(self):
        """ Show the entries' informations in console. """
        qm = self.get_query_model()
        for row in qm:
            entry = row[0]
            print entry.get_ulong(RB.RhythmDBPropType.ENTRY_ID)
            print entry.get_string(RB.RhythmDBPropType.LOCATION)[6:]
            print entry.get_string(RB.RhythmDBPropType.TITLE)

class BasePlaylist(BaseSource):

    def __init__(self):
        super(BasePlaylist, self).__init__()
        self.popup_widget = None
        self.index = 0

    def do_selected(self):
        if not self.activated:

            # setup the popup menu
            shell = self.props.shell
            self.popup = shell.props.ui_manager.get_widget(self.popup_widget)

            self.set_entry_view()

            # load the song list
            if client.user.is_login:
                self.load()

            self.activated = True

    def do_impl_delete(self):
        entries = self.get_entry_view().get_selected_entries()
        song_ids = [int(entry.dup_string(RB.RhythmDBPropType.LOCATION)) \
                for entry in entries]
        # remove songs in the online playlist
        if self.delete_songs(song_ids):
            for entry in entries:
                self.remove_entry(entry)
                self.songs = filter(lambda x: x not in song_ids, self.songs)

    def get_song_ids(self):
        """ Get all ids of songs from baidu music.

        Returns:
            A list includes all ids.
        """
        return []

    def load_cb(self):
        """ The callback function of load all songs. """
        self.updating = True
        self.songs = self.get_song_ids()
        if self.songs:
            songs = self.get_songs(self.songs)
            self.add_songs(songs)
        self.updating = False
        self.notify_status_changed()

    def load(self):
        """ The thread function of load all songs. """
        thread = threading.Thread(target=self.load_cb)
        thread.start()

    def refresh_cb(self):
        """ The callback function of refresh all songs. """
        self.updating = True
        song_ids = self.get_song_ids()

        # checkout the added items and the deleted items
        add_ids = song_ids[:]   # the added items
        delete_ids = []         # the delete items
        for key, item in enumerate(self.songs):
            index = key - len(delete_ids)
            if index >= len(song_ids) or song_ids[index] != item:
                delete_ids.append(item)
            elif song_ids[index] == item:
                add_ids.remove(item)
        #add_ids.reverse()

        # traversal rows in the query model
        for delete_id in delete_ids:
            self.remove_location(str(delete_id))

        if add_ids:
            songs = self.get_songs(add_ids)
            self.add_songs(songs)

        self.songs = song_ids
        self.updating = False
        self.notify_status_changed()

    def refresh(self):
        """ The thread function of refresh all songs. """
        thread = threading.Thread(target=self.refresh_cb)
        thread.start()

    def add(self, songs):
        """ Create entries with songs.

        Args:
            songs: A list includes songs.
        """
        if songs:
            #songs.reverse()
            self.songs.extend([int(song["songId"]) for song in songs])
            self.add_songs(songs)

    def clear(self):
        """ Clear all entries in this source. """
        qm = self.get_query_model()
        for row in qm:
            entry = row[0]
            self.remove_entry(entry)


class CollectSource(BasePlaylist):

    def __init__(self):
        super(CollectSource, self).__init__()

        self.popup_widget = "/CollectSourcePopup"
        self.entry_widgets = ["BaiduMusicAdd"]

    def delete_songs(self, song_ids):
        return client.collect.DeleteSongs().run({"songId": song_ids, })

    def get_song_ids(self):
        self.status = _("Loading song IDs...")
        start, song_ids = 0, []
        while True:
            total, ids = client.collect.GetSongIDs().run({"start": start, })
            song_ids.extend(ids)
            self.progress = start/total
            self.notify_status_changed()
            start += DELTA
            if start >= total:
                song_ids.reverse()
                break
        self.progress = start/total
        self.notify_status_changed()
        return song_ids


class OnlinePlaylistSource(BasePlaylist):

    def __init__(self):
        super(OnlinePlaylistSource, self).__init__()

        self.playlist_id = None
        self.popup_widget = "/OnlinePlaylistPopup"
        self.entry_widgets = ["BaiduMusicAdd", "BaiduMusicCollect"]

    def delete_songs(self, song_ids):
        return client.playlist.DeleteSongs().run({
            "listId": self.playlist_id,
            "songId": song_ids,
            })

    def get_song_ids(self):
        song_ids = client.playlist.GetSongIDs().run({
            "playListId": self.playlist_id,
            })
        song_ids.reverse()
        return song_ids


class TempSource(BaseSource):

    def __init__(self):
        super(TempSource, self).__init__()

        self.popup_widget = "/TempSourcePopup"
        self.entry_widgets = ["BaiduMusicAdd", "BaiduMusicCollect"]

    def do_selected(self):
        if not self.activated:
            # setup the popup menu
            shell = self.props.shell
            self.popup = shell.props.ui_manager.get_widget(self.popup_widget)

            self.set_entry_view()

            self.__playlist =  RB.find_user_cache_file(TEMP_PLAYLIST)
            if not os.path.isfile(self.__playlist):
                os.mknod(self.__playlist)
            else:
                try:
                    song_ids = pickle.load(open(self.__playlist, "rb"))
                    songs = self.get_songs(song_ids)
                    self.add(songs)
                except Exception, e:
                    pass

            self.activated = True

    def do_impl_delete(self):
        entries = self.get_entry_view().get_selected_entries()
        for entry in entries:
            self.remove_entry(entry)
            song_id = int(entry.get_string(RB.RhythmDBPropType.LOCATION)[6:])
            self.songs.remove(song_id)
        self.__save()

    def add(self, songs):
        """ Create entries with songs.

        Args:
            songs: A list includes songs.
        """
        if songs:
            self.songs.extend([int(song["songId"]) for song in songs])
            self.add_songs(songs)
            self.__save()

    def __save(self):
        """ Save all entries in a playlist. """
        pickle.dump(self.songs, open(self.__playlist, "wb"))


GObject.type_register(CollectSource)
GObject.type_register(OnlinePlaylistSource)
GObject.type_register(TempSource)
