# rhythmbox-baidu-music #

A rhythmbox plugin for playing music from Baidu Music.

## Installation ##

### Requirements ###

* Rhythmbox >=2.98
* GObject introspection data packages:

    * gir1.2-glib-2.0
    * gir1.2-gtk-3.0
    * gir1.2-peas-1.0

### Installing via PPA ###

    $ sudo add-apt-repository ppa:pandasunny/rhythmbox-baidu-music
    $ sudo apt-get update
    $ sudo apt-get install rhythmbox-baidu-music

### Installing via git ###

Install this plugin in the system plugin directory (/usr/lib/rhythmbox/plugins/)

    git clone https://github.com/pandasunny/rhythmbox-baidu-music.git
    cd rhythmbox-baidu-music
    sudo make install

Or install it in the per-user plugin directory (~/.local/share/rhythmbox/plugins/), please use:

    sudo make install-local

When you want to uninstall this plugin, you could use:

    make uninstall

### Changlog ###

#### version 0.2 (release 2013-08-23) ####

###### Core ######

* Play the online songs in the temporary list.
* Auto save the temporary list.
* Add the online songs to the collect list or delete them.
* Create, delete and rename the online playlist.
* Switch to high quality music.
* Search song in a alone window.
* Automatically download the lyric file of current playing song.
* Automatically show the coverart.

###### API ######

* Change the api version from 7.0.4 to 8.1.0.8.
* Add apis about the online playlist.
* Replace the hacked search api to the ting's search api
* Enhance the api about getting the song's link.

###### GUI  ######

* Add two toolitems ("search music" and "HQ") to the main toolbar.
* Create a alone page group for baidu music.
* Add some display pages include the temporary list and online playlists.
* Add popup menu to all display pages.
* Remove the "search" toolitem from collect source.

#### version 0.1 (release 2013-07-28) ####

* Create the base version.

## Feedback ##

Please submit bugs to github's [issues system](https://github.com/pandasunny/rhythmbox-baidu-music/issues).

Or contact me with twitter ([@pandasunny](https://twitter.com/pandasunny)) or weibo ([@pandasunny](http://weibo.com/pandasunny))

## License ##

The plugin is licensed under the GPL v3 License.
