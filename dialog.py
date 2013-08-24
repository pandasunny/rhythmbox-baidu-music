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

import os
import gettext
from gi.repository import Gtk
from gi.repository import RB

_ = gettext.gettext
APPNAME = "rhythmbox-baidu-music"
gettext.install(APPNAME, RB.locale_dir())
gettext.textdomain(APPNAME)


class LoginDialog(Gtk.Dialog):
    def __init__(self):
        Gtk.Dialog.__init__(self,
            _("Login"), None, 0, (
                Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                Gtk.STOCK_OK, Gtk.ResponseType.OK,
        ))

        # username and password input
        username_label = Gtk.Label(_("Username:"))
        password_label = Gtk.Label(_("Password:"))
        self.username_entry = Gtk.Entry()
        self.password_entry = Gtk.Entry()
        self.password_entry.set_visibility(False)

        # baidu url
        signup_url = Gtk.Label()
        signup_url.set_markup("<a href='https://passport.baidu.com/v2/?reg'>"
                + _("Sign up") + "</a>")
        signup_url.set_halign(Gtk.Align.START)
        signup_url.set_can_focus(False)

        forgotpassword_url = Gtk.Label()
        forgotpassword_url.set_markup(
                "<a href='https://passport.baidu.com/?getpass_index'>"
                + _("Forgot?") + "</a>")
        forgotpassword_url.set_can_focus(False)

        grid = Gtk.Grid()
        grid.set_column_spacing(5)
        grid.set_border_width(5)

        grid.add(username_label)
        grid.attach(self.username_entry, 1, 0, 2, 1)
        grid.attach(password_label, 0, 1, 1, 1)
        grid.attach(self.password_entry, 1, 1, 2, 1)

        grid.attach(signup_url, 3, 0, 1, 1)
        grid.attach(forgotpassword_url, 3, 1, 1, 1)

        box = self.get_content_area()
        box.add(grid)
        self.show_all()


class AddPlaylistDialog(Gtk.Dialog):
    def __init__(self):
        Gtk.Dialog.__init__(self,
            _("Add Playlist"), None, 0, (
                Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                Gtk.STOCK_OK, Gtk.ResponseType.OK,
        ))

        # username and password input
        title_label = Gtk.Label(_("Title:"))
        self.title_entry = Gtk.Entry()

        grid = Gtk.Grid()
        grid.set_column_spacing(5)
        grid.set_border_width(5)

        grid.add(title_label)
        grid.attach(self.title_entry, 1, 0, 2, 1)

        box = self.get_content_area()
        box.add(grid)
        self.show_all()


class RenamePlaylistDialog(Gtk.Dialog):
    def __init__(self):
        Gtk.Dialog.__init__(self,
            _("Rename Playlist"), None, 0, (
                Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                Gtk.STOCK_OK, Gtk.ResponseType.OK,
        ))

        # username and password input
        old_title_label = Gtk.Label(_("Old title:"))
        title_label = Gtk.Label(_("New title:"))
        self.old_title_entry = Gtk.Entry()
        self.old_title_entry.set_sensitive(False)
        self.title_entry = Gtk.Entry()

        grid = Gtk.Grid()
        grid.set_column_spacing(5)
        grid.set_border_width(5)

        grid.add(old_title_label)
        grid.attach(self.old_title_entry, 1, 0, 2, 1)
        grid.attach(title_label, 0, 1, 1, 1)
        grid.attach(self.title_entry, 1, 1, 2, 1)

        box = self.get_content_area()
        box.add(grid)
        self.show_all()


class AddToPlaylistDialog(Gtk.Dialog):
    def __init__(self, playlists, songs, skip_id=""):
        Gtk.Dialog.__init__(self,
            _("Add songs to..."), None, 0, (
                Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                Gtk.STOCK_OK, Gtk.ResponseType.OK,
        ))

        id_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        id_box.set_border_width(5)

        button = None
        for playlist_id, playlist in playlists.iteritems():
            if playlist_id != skip_id:
                title = playlist.get_property("name")
                if not button:
                    self.playlist_id = playlist_id
                button = Gtk.RadioButton.new_with_label_from_widget(button, title)
                button.connect("toggled", self.on_button_toggled, playlist_id)
                id_box.pack_start(button, False, False, 0)

        box = self.get_content_area()
        box.add(id_box)
        self.show_all()

    def on_button_toggled(self, button, playlist_id):
        if button.get_active():
            self.playlist_id = playlist_id
        else:
            self.playlist_id = None
