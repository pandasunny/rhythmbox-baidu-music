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

import re
import gettext

from gi.repository import Gtk
from gi.repository import RB

from dialog import AddToPlaylistDialog

_ = gettext.gettext
APPNAME = "rhythmbox-baidu-music"
gettext.install(APPNAME, RB.locale_dir())
gettext.textdomain(APPNAME)

PREPAGE = 30

class SearchHandle(object):

    def __init__(self, builder, client, collect_source, temp_source, playlists):

        # the basic objects
        self.__collect_source = collect_source
        self.__temp_source = temp_source
        self.__client = client
        self.__builder = builder
        self.__playlists = playlists

        # the widgets
        self.__liststore = builder.get_object("liststore")
        self.__search_entry = builder.get_object("search_entry")
        self.__page_spinbutton = builder.get_object("page_spinbutton")
        self.__page_adjustment = builder.get_object("page_adjustment")
        self.__total_lable = builder.get_object("total_label")

        # the basic variables
        self.__song_ids = []
        self.__keyword = ""
        self.__current_page = 0
        self.__last_page = 0
        self.__select_all = False

        self.__check_buttons_status()

    def __check_buttons_status(self):
        """ check the status of all buttons. """
        buttons = []
        if not self.__song_ids:
            buttons.extend(["collect", "play", "add"])
        if self.__current_page <= 1:
            buttons.extend(["first", "back"])
        if self.__current_page == self.__last_page:
            buttons.extend(["forward", "last"])
        if not len(self.__liststore):
            buttons.append("select_all")
        if not self.__current_page and not self.__last_page:
            buttons.append("goto")
            self.__page_spinbutton.set_sensitive(False)
        else:
            self.__page_spinbutton.set_sensitive(True)

        if not self.__client.islogin:
            buttons.extend(["collect", "add"])

        buttons = list(set(buttons))

        all_buttons = [
                "select_all", "collect", "goto", "play",
                "first", "back", "forward", "last", "add"
                ]
        enable_buttons = [btn for btn in all_buttons if btn not in buttons]
        for btn in enable_buttons:
            self.__builder.get_object(btn+"_button").set_sensitive(True)
        for btn in buttons:
            self.__builder.get_object(btn+"_button").set_sensitive(False)

    def __refresh(self):
        """ Refresh the liststore of view. """
        pattern = re.compile("</?em>")

        info = self.__client.search(self.__keyword, self.__current_page, PREPAGE)
        self.__liststore.clear()
        for song in info["song_list"]:
            self.__liststore.append([
                False,
                int(song["song_id"]) if song["song_id"] else None,
                pattern.sub("", song["title"]),
                pattern.sub("", song["author"]),
                pattern.sub("", song["album_title"]),
                True # TODO: make sure the status of a song
                ])
        total = 1000 if int(info["pages"]["total"]) >= 1000 \
                else int(info["pages"]["total"])
        #num = int(info["pages"]["rn_num"])
        #self.__last_page = (total + num - 1) / num
        self.__last_page = (total + PREPAGE - 1) / PREPAGE
        self.__total_lable.set_label(str(self.__last_page) + " /")
        self.__page_adjustment.set_value(self.__current_page)
        self.__page_adjustment.set_upper(self.__last_page)
        self.__song_ids = []
        self.__select_all = False
        self.__check_buttons_status()

    def on_search(self, widget):
        """ Search the keywords of entry. """
        self.__keyword = self.__search_entry.get_text().strip()
        if self.__keyword:
            self.__current_page = 1
            self.__refresh()
        self.__check_buttons_status()

    def on_toggled(self, widget, path):
        """ Toggle the status of select. """
        self.__liststore[path][0] = not self.__liststore[path][0]
        song_id = self.__liststore[path][1]
        if song_id in self.__song_ids:
            self.__song_ids.remove(song_id)
            self.__select_all = False
        else:
            self.__song_ids.append(song_id)
            # check all song status
            self.__select_all = True
            for song in self.__liststore:
                if not song[0]:
                    self.__select_all = False
        self.__check_buttons_status()

    def on_select_all_toggled(self, widget):
        """ Select all songs. """
        self.__song_ids = []
        if self.__select_all:
            for song in self.__liststore:
                song[0] = False
            self.__select_all = False
            widget.set_label(_("Select All"))
            widget.set_tooltip_text(
                    _("Select all songs which can be selected.")
                    )
        else:
            for song in self.__liststore:
                song[0] = True
                self.__song_ids.append(song[1])
            self.__select_all = True
            widget.set_label(_("Reject All"))
            widget.set_tooltip_text(
                    _("Reject all songs which be selected.")
                    )
        self.__check_buttons_status()

    def on_first(self, widget):
        """ Go to the first page. """
        if self.__current_page > 1:
            self.__current_page = 1
            self.__refresh()

    def on_back(self, widget):
        """ Go to the back page. """
        if self.__current_page > 1:
            self.__current_page -= 1
            self.__refresh()

    def on_forward(self, widget):
        """ Go to the forward page. """
        if self.__current_page < self.__last_page:
            self.__current_page += 1
            self.__refresh()

    def on_last(self, widget):
        """ Go to the last page. """
        if self.__current_page < self.__last_page:
            self.__current_page = self.__last_page
            self.__refresh()

    def on_collect(self, widget):
        """ Collect all selected songs. """
        song_ids = self.__client.add_collect_songs(self.__song_ids)
        if song_ids:
            song_ids = [song_ids] if isinstance(song_ids, int) else song_ids
            songs = self.__client.get_song_info(song_ids)
            songs.reverse()
            self.__collect_source.add(songs)

    def on_play(self, widget):
        """ Play all selected songs. """
        song_ids = [song_id for song_id in self.__song_ids \
                if song_id not in self.__temp_source.songs]
        songs = self.__client.get_song_info(song_ids)
        if songs:
            self.__temp_source.add(songs)

    def on_add(self, widget):
        """ Add all selected songs to playlist. """
        song_ids = [song_id for song_id in self.__song_ids]
        dialog = AddToPlaylistDialog(self.__playlists, song_ids)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            playlist_id = dialog.playlist_id
            if playlist_id:
                songs_ids = self.__client.add_playlist_songs(playlist_id, song_ids)
                songs = self.__client.get_song_info(song_ids)
                songs.reverse()
                self.__playlists[playlist_id].add(songs)
        elif response == Gtk.ResponseType.CANCEL:
            pass
        dialog.destroy()

    def on_goto(self, widget):
        """ Go to the custom page. """
        self.__page_spinbutton.update()
        page = int(self.__page_spinbutton.get_value())
        if page <= self.__last_page:
            self.__current_page = page
            self.__refresh()
