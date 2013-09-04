# -*- coding: utf-8 -*-
from __future__ import division

import os
import threading
import urllib2
import socket
import time

import rb
from gi.repository import Gtk
from gi.repository import GdkPixbuf
from gi.repository import RB

import gettext

_ = gettext.gettext
APPNAME = "rhythmbox-baidu-music"
gettext.install(APPNAME, RB.locale_dir())
gettext.textdomain(APPNAME)

THREAD_LIMIT = 3
TIMEOUT = 10

CHUNK_SIZE = 16384  # 16KByte/time
RANGE_SIZE = [611840, 204800, 163840, 81920, 81920]

# Download Status
DOWNLOAD_QUEUE = _("queue")
DOWNLOAD_RUN = _("run")
DOWNLOAD_STOP = _("stop")
DOWNLOAD_FINISH = _("finish")
DOWNLOAD_ERROR = _("error")
DOWNLOAD_DELETE = _("delete")

# status icon text
#DOWNLOAD_QUEUE = "download-queue"
#DOWNLOAD_RUN = "download-run"
#DOWNLOAD_STOP = "download-stop"
#DOWNLOAD_FINISH = "download-finish"
#DOWNLOAD_ERROR = "download-error"
#DOWNLOAD_DELETE = "download-delete"

# Song information
(SONG_ID,
 SONG_TITLE,
 SONG_ARTIST,
 SONG_ALBUM,
 SONG_URL,
 SONG_PROGRESS,
 SONG_TYPE,
 SONG_FILE,
 SONG_SIZE,
 SONG_HASH,
 SONG_PATH,
 SONG_FORMAT,
 SONG_STATUS) = range(13)

# song type
(SONG_TYPE_FLAC,
 SONG_TYPE_320,
 SONG_TYPE_256,
 SONG_TYPE_128,
 SONG_TYPE_64) = range(5)


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


class DownloadThread(threading.Thread):

    def __init__(self, liststore, lock):
        threading.Thread.__init__(self)

        self.liststore = liststore
        self.daemon = True
        self.lock = lock

    def set_task(self):
        task = None
        self.lock.acquire()
        for song in self.liststore:
            if song[SONG_STATUS]==DOWNLOAD_QUEUE:
                song[SONG_STATUS] = DOWNLOAD_RUN
                task = song
                break
        self.lock.release()

        if task:
            self.song = task
            self.range_size = RANGE_SIZE[self.song[SONG_TYPE]]

            self.filename = os.path.join(
                    self.song[SONG_PATH], "%s - %s.bd%i" % (
                        self.song[SONG_ARTIST],
                        self.song[SONG_TITLE],
                        self.song[SONG_FILE]
                        ))
            self.handler = open(self.filename, "ab+")
            return True
        else:
            return False

    def run(self):
        while self.set_task():
            try:
                self.downloaded = os.path.getsize(self.filename)
            except OSError:
                self.downloaded = 0

            try:
                while self.song[SONG_PROGRESS]<100 \
                        and self.song[SONG_STATUS]==DOWNLOAD_RUN:
                    self.download()
            except urllib2.URLError, e:
                if isinstance(e.reason, socket.timeout):
                    self.lock.acquire()
                    self.song[SONG_STATUS] = DOWNLOAD_QUEUE
                    self.lock.release()
            except Exception, e:
                print e
                self.lock.acquire()
                self.song[SONG_STATUS] = DOWNLOAD_ERROR
                self.lock.release()
            finally:
                self.handler.close()
            if self.song[SONG_STATUS]==DOWNLOAD_DELETE:
                try:
                    os.remove(self.filename)
                except:
                    pass

    def download(self):
        if self.downloaded+self.range_size>self.song[SONG_SIZE]:
            range_end = self.song[SONG_SIZE]-1
        else:
            range_end = self.downloaded+self.range_size-1

        request = urllib2.Request(self.song[SONG_URL])
        request.add_header("User-Agent",
                "Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.1; \
                        Trident/4.0)")
        request.add_header("Range", "bytes=%d-%d" % \
                (self.downloaded, range_end))

        response = urllib2.urlopen(request, timeout=TIMEOUT)
        chunk = response.read(CHUNK_SIZE)
        while chunk:
            self.handler.write(chunk)
            self.downloaded += len(chunk)
            self.lock.acquire()
            self.song[SONG_PROGRESS] = int(
                    self.downloaded/self.song[SONG_SIZE]*100)
            self.lock.release()
            chunk = response.read(CHUNK_SIZE)
        if self.song[SONG_PROGRESS]==100:
            self.rename()
            self.lock.acquire()
            self.song[SONG_STATUS] = DOWNLOAD_FINISH
            self.lock.release()
        #time.wait(0.5)

    def rename(self):
        number = 0
        root = os.path.splitext(self.filename)[0]
        filename = "%s.%s" % (root, self.song[SONG_FORMAT])
        while os.path.exists(filename):
            number += 1
            filename = "%s (%s).%s" % (root, str(number),
                    self.song[SONG_FORMAT])
        else:
            os.rename(self.filename, filename)
            self.filename = filename


class DownloadSource(RB.Source):

    def __init__(self):
        super(DownloadSource, self).__init__()

        self.items = []

        self.pool = []
        self.lock = threading.RLock()
        self.status_icon = {}
        #self.running = 0

    def create_ui(self):
        shell = self.props.shell
        #self.register_stock_icons()

        builder = Gtk.Builder()
        builder.set_translation_domain(APPNAME)
        builder.add_from_file(
                rb.find_plugin_file(self.props.plugin, "download-source.ui")
                )

        handlers = {
            "on_run_btn_clicked": self.run_cb,
            "on_pause_btn_clicked": self.pause_cb,
            "on_delete_btn_clicked": self.delete_cb,
            "on_tree_selection_changed": self.select_cb,
            #"on_liststore_row_changed": self.row_changed_cb,
        }
        builder.connect_signals(handlers)

        scrolledwindow = builder.get_object("scrolledwindow")
        self.liststore = builder.get_object("liststore")
        self.treeview = builder.get_object("treeview")
        self.toolbar = builder.get_object("toolbar")
        self.toolbar.set_sensitive(False)

        self.vbox = Gtk.Paned.new(Gtk.Orientation.VERTICAL)

        self.vbox.add1(self.toolbar)
        self.vbox.add2(scrolledwindow)
        self.pack_start(self.vbox, True, True, 0)
        self.show_all()

    def register_stock_icons(self):
        icons = [
                DOWNLOAD_QUEUE,
                DOWNLOAD_RUN,
                DOWNLOAD_STOP,
                DOWNLOAD_FINISH,
                DOWNLOAD_ERROR,
                DOWNLOAD_DELETE
                ]
        factory = Gtk.IconFactory()
        for icon in icons:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(
                rb.find_plugin_file(self.props.plugin, "images/%s.png" % icon)
                )
            icon_set = Gtk.IconSet.new_from_pixbuf(pixbuf)
            factory.add(icon, icon_set)
        factory.add_default()

    def run_cb(self, widget):
        selection = self.treeview.get_selection()
        (model, paths) = selection.get_selected_rows()
        count = 0
        for path in paths:
            treeiter = model.get_iter(path)
            song = model[treeiter]
            if song[SONG_STATUS] in [DOWNLOAD_ERROR, DOWNLOAD_STOP]:
                song[SONG_STATUS] = DOWNLOAD_QUEUE
                count += 1
        self.join(count)

    def pause_cb(self, widget):
        selection = self.treeview.get_selection()
        (model, paths) = selection.get_selected_rows()
        for path in paths:
            treeiter = model.get_iter(path)
            status = model.get_value(treeiter, SONG_STATUS)
            if status in [DOWNLOAD_QUEUE, DOWNLOAD_RUN]:
                self.lock.acquire()
                model.set_value(treeiter, SONG_STATUS, DOWNLOAD_STOP)
                self.lock.release()

    def delete_cb(self, widget):
        selection = self.treeview.get_selection()
        (model, paths) = selection.get_selected_rows()
        for path in paths:
            treeiter = model.get_iter(path)
            song = model[treeiter]
            status = model.get_value(treeiter, SONG_STATUS)
            key = model.get_value(treeiter, SONG_FILE)
            if status==DOWNLOAD_RUN:
                model.set_value(treeiter, SONG_STATUS, DOWNLOAD_DELETE)
            else:
                if status==DOWNLOAD_FINISH:
                    filename = "%s - %s.%s" % (
                            song[SONG_ARTIST],
                            song[SONG_TITLE],
                            song[SONG_FORMAT]
                            )
                else:
                    filename = "%s - %s.bd%i" % (
                            song[SONG_ARTIST],
                            song[SONG_TITLE],
                            song[SONG_FILE]
                            )
                file = os.path.join(song[SONG_PATH], filename)
                try:
                    os.remove(file)
                except:
                    pass
                print "Delete the file: %s" % file
            model.remove(treeiter)
            self.items.remove(key)
        selection.unselect_all()

    def select_cb(self, selection):
        (model, paths) = selection.get_selected_rows()
        self.toolbar.set_sensitive(bool(len(paths)))

    def add_items(self, songs):
        path = os.path.join(RB.music_dir(), "baidu")

        self.lock.acquire()
        for song in songs:
            key = song["file"]["file_id"]
            if key not in self.items:
                self.liststore.append([
                    song["id"],
                    song["title"],
                    song["artist"],
                    song["album"],
                    song["file"]["url"],
                    0,  # progress
                    song["type"],
                    song["file"]["file_id"],
                    song["file"]["size"],
                    song["file"]["hash"],
                    path,   # download dir
                    song["file"]["format"],
                    DOWNLOAD_QUEUE
                ])
                self.items.append(key)
        self.lock.release()
        self.join(len(songs))

    def join(self, count):
        for thread in self.pool:
            if not thread.is_alive():
                self.pool.remove(thread)
                del thread
        limit = THREAD_LIMIT - len(self.pool)
        count = count if count<limit else limit
        for i in range(count):
            thread = DownloadThread(self.liststore, self.lock)
            thread.start()
            self.pool.append(thread)
