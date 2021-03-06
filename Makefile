SCHEMAS_DIR=$(DESTDIR)/usr/share/glib-2.0/schemas
PLUGIN_DIR=$(DESTDIR)/usr/lib/rhythmbox/plugins/baidu-music
PLUGIN_DATA_DIR=$(DESTDIR)/usr/share/rhythmbox/plugins/baidu-music
PLUGIN_USER_DIR=$(HOME)/.local/share/rhythmbox/plugins/baidu-music
PLUGIN_LOCALE_DIR=$(DESTDIR)/usr/share/locale

clear:
	rm -f *.py[co] */*.py[co]
install: install-po schemas
	mkdir -p $(PLUGIN_DIR)
	mkdir -p $(PLUGIN_DATA_DIR)
	cp -r *.py baidu-music.plugin $(PLUGIN_DIR)
	cp -r *.ui popup-ui.xml images $(PLUGIN_DATA_DIR)
install-local: install-po schemas
	mkdir -p $(PLUGIN_USER_DIR)
	cp -r *.py *.ui popup-ui.xml baidu-music.plugin images $(PLUGIN_USER_DIR)
uninstall:
	rm -rf $(PLUGIN_DIR)
	rm -rf $(PLUGIN_DATA_DIR)
	rm -rf $(PLUGIN_USER_DIR)
	rm -f $(SCHEMAS_DIR)/org.gnome.rhythmbox.plugins.baidu-music.gschema.xml
	glib-compile-schemas $(SCHEMAS_DIR)
	for i in ./po/*.po; do \
		lang=`basename $$i .po`; \
		rm -f $(PLUGIN_LOCALE_DIR)/$$lang/LC_MESSAGES/rhythmbox-baidu-music.mo; \
	done
install-po:
	for i in ./po/*.po; do \
		lang=`basename $$i .po`; \
		msgfmt -c ./po/$$lang.po -o ./po/$$lang.mo; \
		mkdir -p $(PLUGIN_LOCALE_DIR)/$$lang/LC_MESSAGES; \
		mv ./po/$$lang.mo $(PLUGIN_LOCALE_DIR)/$$lang/LC_MESSAGES/rhythmbox-baidu-music.mo; \
	done
	rm -f ./po/*.mo
schemas:
	if [ ! -d $(SCHEMAS_DIR) ]; then \
		mkdir -p $(SCHEMAS_DIR); \
	fi
	cp org.gnome.rhythmbox.plugins.baidu-music.gschema.xml $(SCHEMAS_DIR)
	glib-compile-schemas $(SCHEMAS_DIR)
