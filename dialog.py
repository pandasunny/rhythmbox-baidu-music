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
from gi.repository import Gtk


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
