SCHEMAS_DIR=$(DEST_DIR)/usr/share/glib-2.0/schemas
PLUGIN_DIR=$(DEST_DIR)/usr/lib/rhythmbox/plugins/baidu-music
PLUGIN_DATA_DIR=$(DEST_DIR)/usr/share/rhythmbox/plugins/baidu-music
PLUGIN_USER_DIR=$(HOME)/.local/share/rhythmbox/plugins/baidu-music
PLUGIN_LOCALE_DIR=$(DEST_DIR)/usr/share/locale

clear:
	rm -f *.py[co] */*.py[co]
install: install-po schemas
	sudo mkdir -p $(PLUGIN_DIR)
	sudo mkdir -p $(PLUGIN_DATA_DIR)
	sudo cp -r *.py baidu-music.plugin $(PLUGIN_DIR)
	sudo cp -r *.ui *.png $(PLUGIN_DATA_DIR)
install-per-user: install-po schemas
	mkdir -p $(PLUGIN_USER_DIR)
	cp -r *.py *.ui *.png baidu-music.plugin $(PLUGIN_USER_DIR)
uninstall:
	sudo rm -rf $(PLUGIN_DIR)
	sudo rm -rf $(PLUGIN_DATA_DIR)
	rm -rf $(PLUGIN_USER_DIR)
	sudo rm $(SCHEMAS_DIR)/org.gnome.rhythmbox.plugins.baidu-music.gschema.xml
	sudo glib-compile-schemas $(SCHEMAS_DIR)
	for i in ./po/*.po; do \
		lang=`basename $$i .po`; \
		sudo rm -f $(PLUGIN_LOCALE_DIR)/$$lang/LC_MESSAGES/rhythmbox-baidu-music.mo; \
	done
install-po:
	for i in ./po/*.po; do \
		lang=`basename $$i .po`; \
		msgfmt -c ./po/$$lang.po -o ./po/$$lang.mo; \
		sudo mv ./po/$$lang.mo $(PLUGIN_LOCALE_DIR)/$$lang/LC_MESSAGES/rhythmbox-baidu-music.mo; \
	done
	rm -f ./po/*.mo
schemas:
	sudo cp org.gnome.rhythmbox.plugins.baidu-music.gschema.xml $(SCHEMAS_DIR)
	sudo glib-compile-schemas $(SCHEMAS_DIR)
