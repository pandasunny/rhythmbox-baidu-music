# -*- coding: utf-8 -*-

class SearchHandle(object):

    def __init__(self, builder, source, client):

        self.__source = source
        self.__client = client
        self.__builder = builder

        self.__liststore = builder.get_object("liststore")
        self.__search_entry = builder.get_object("search_entry")
        self.__page_spinbutton = builder.get_object("page_spinbutton")
        self.__page_adjustment = builder.get_object("page_adjustment")
        self.__total_lable = builder.get_object("total_label")

        self.__song_ids = []
        self.__keyword = ""
        self.__current_page = 0
        self.__last_page = 0
        self.__select_all = False

        self.__check_buttons_status()

    def __check_buttons_status(self):
        buttons = []
        if not self.__song_ids:
            buttons.append("collect")
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

        all_buttons = [
                "select_all", "collect", "goto",
                "first", "back", "forward", "last"
                ]
        enable_buttons = [btn for btn in all_buttons if btn not in buttons]
        for btn in enable_buttons:
            self.__builder.get_object(btn+"_button").set_sensitive(True)
        for btn in buttons:
            self.__builder.get_object(btn+"_button").set_sensitive(False)

    def __refresh(self, songs):
        self.__liststore.clear()
        for song in songs["songs"]:
            self.__liststore.append([
                False,
                int(song["id"]) if song["id"] else None,
                song["title"].decode("utf-8"),
                song["album"].decode("utf-8"),
                song["artist"].decode("utf-8"),
                True if song["id"] else False
                ])
        self.__current_page = songs["page"]
        self.__last_page = int((songs["count"]+songs["num"]-1)/songs["num"])
        self.__total_lable.set_label(str(self.__last_page) + " /")
        self.__page_adjustment.set_value(self.__current_page)
        self.__page_adjustment.set_upper(self.__last_page)
        self.__song_ids = []
        self.__select_all = False
        self.__check_buttons_status()

    def on_search(self, widget):
        self.__keyword = self.__search_entry.get_text().strip()
        if self.__keyword:
            result = self.__client.search(self.__keyword)
            self.__refresh(result)
        self.__check_buttons_status()

    def on_toggled(self, widget, path):
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
        if self.__current_page > 1:
            result = self.__client.search(self.__keyword, 1)
            self.__refresh(result)

    def on_back(self, widget):
        if self.__current_page > 1:
            result = self.__client.search(
                    self.__keyword,
                    self.__current_page - 1
                    )
            self.__refresh(result)

    def on_forward(self, widget):
        if self.__current_page < self.__last_page:
            result = self.__client.search(
                    self.__keyword,
                    self.__current_page + 1
                    )
            self.__refresh(result)

    def on_last(self, widget):
        if self.__current_page < self.__last_page:
            result = self.__client.search(
                    self.__keyword,
                    self.__last_page
                    )
            self.__refresh(result)

    def on_collect(self, widget):
        songs = self.__client.add_favorite_songs(self.__song_ids)
        if songs:
            self.__source.add(songs)

    def on_goto(self, widget):
        self.__page_spinbutton.update()
        page = int(self.__page_spinbutton.get_value())
        if page <= self.__last_page:
            result = self.__client.search(self.__keyword, page)
            self.__refresh(result)
