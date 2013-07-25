# -*- coding: utf-8 -*-
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
                + _("sign up") + "</a>")
        signup_url.set_halign(Gtk.Align.START)

        forgotpassword_url = Gtk.Label()
        forgotpassword_url.set_markup(
                "<a href='https://passport.baidu.com/?getpass_index'>"
                + _("forgot?") + "</a>")

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
