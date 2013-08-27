# -*- coding: utf-8 -*-

from __future__ import division

import os
import threading
import gettext
import time

from gi.repository import Gtk
from gi.repository import RB

SONG_TYPE_FLAC = 0
SONG_TYPE_320 = 1
SONG_TYPE_256 = 2
SONG_TYPE_128 = 3
SONG_TYPE_64 = 4


class DownloadDialog(Gtk.Dialog):
    """ Download corfim dialog """

    def __init__(self, song_ids, client):
        Gtk.Dialog.__init__(self,
                "", None, 0, (
                    Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                    Gtk.STOCK_OK, Gtk.ResponseType.OK,
                    ))

        self.download_list = []
        self.song_ids = song_ids
        self.client = client

        self.hbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        self.hbox.set_border_width(10)

        #self.info_label = Gtk.Label()
        #self.hbox.pack_start(self.info_label, False, False, 0)

        self.spinner = Gtk.Spinner()
        self.hbox.pack_start(self.spinner, False, False, 0)
        self.spinner.start()

        thread = threading.Thread(target=self.get_songs)
        thread.start()

        box = self.get_content_area()
        box.add(self.hbox)
        self.show_all()

    def get_songs(self):

        self.songs = self.client.get_song_links(self.song_ids, True, True)
        self.set_ui()

    def set_ui(self):

        # setup the dialog's title
        title = _("Download a song") if len(self.songs) == 1 \
                else _("Batch download songs")
        self.set_title(title)

      # create radio buttons and download list
        button, buttons = None, {}
        for song in self.songs:
            download_song = {
                    "id": song["song_id"],
                    "title": song["song_title"].encode("utf-8"),
                    "album": song["album_title"].encode("utf-8"),
                    "artist": song["song_artist"].encode("utf-8"),
                    "lyric": song["lyric_url"],
                    "list": {}
                    }
            for file in song["file_list"]:
                file_type, type_text, comment_text = self.kbps2text(
                        int(file["kbps"]), file["format"]
                        )
                mb = self.size2mb(int(file["size"]))
                # create a radio button
                if file_type not in buttons.keys():
                    button = self.create_radio_button(
                            type_text, comment_text, mb, button
                            )
                    button.connect("toggled", self.on_button_toggled, file_type)
                    buttons[file_type] = button
                # create a files list
                download_song["list"][file_type] = file
            self.download_list.append(download_song)

        self.spinner.stop()
        self.hbox.remove(self.spinner)

        # Add the radio buttons to the dialog
        buttons = sorted(buttons.iteritems(), key=lambda d:d[0])
        for radio in buttons:
            self.hbox.pack_start(radio[1], False, False, 0)
            if radio[0]==1 and not radio[1].get_active():
                radio[1].set_active(True)
            else:
                self.on_button_toggled(radio[1], radio[0])
            radio[1].show()

    def create_radio_button(self, type_text, comment_text, mb, group=None):
        text = "%-20s%10.2fM ( %s )" % (type_text, mb, comment_text) \
                if len(self.songs)==1 else \
                "%-20s ( %s )" % (_("Priority ") + type_text, comment_text)

        radio = Gtk.RadioButton.new_with_label_from_widget(group, text)
        return radio

    def on_button_toggled(self, button, file_type):
        if button.get_active():
            self.select = file_type

    def size2mb(self, size):
        return size/(1024*1024)

    def kbps2text(self, kbps, file_format=None):
        if file_format == "flac":
            type_text = _("Lossless Quality")
            comment_text = _("Lossless flac")
            file_type = SONG_TYPE_FLAC
        else:
            if kbps>=320:
                type_text = _("Ultra High Quality")
                file_type = SONG_TYPE_320
            elif 256<=kbps<320:
                type_text = _("High Quality")
                file_type = SONG_TYPE_256
            elif 128<=kbps<256:
                type_text = _("Standard Quality")
                file_type = SONG_TYPE_128
            elif 64<=kbps<128:
                type_text = _("Normal Quality")
                file_type = SONG_TYPE_64
            elif kbps<64:
                type_text = _("Compression Quality")
                file_type = SONG_TYPE_32
            comment_text = "%ikbps" % kbps
        return file_type, type_text, comment_text

    def get_songs_list(self):
        for song in self.download_list:
            if self.select in song["list"].keys():
                file = song["list"][self.select]
            else:
                file = {}
                for key in song["list"].keys():
                    if key >= self.select:
                        file[key] = song["list"][key]
                file = sorted(file.iteritems(), key=lambda d:d[0])[-1][1]
            song["file"] = file
            song["type"] = self.select
            del song["list"]
        return self.download_list
