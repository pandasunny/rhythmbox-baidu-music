# rhythmbox-baidu-music #

Rhythmbox的百度音乐插件。

## 功能 ##

实现Windows下百度音乐（原“千千静听”）有关在线方面的基本功能

* 播放在线音乐，可以切换“高音质”模式
* 自动显示歌曲封面
* 自定义歌词目录，并自动下载歌词
* 通过关键词搜索音乐
* 收藏音乐，同步“我的收藏”列表
* 同步在线歌单

建议使用OSD Lyrics来直接显示歌词，初始歌词目录为 ~/.lyrics/

## 安装 ##

### 依赖 ###

* Rhythmbox >=2.98
* GObject introspection data packages:

    * gir1.2-glib-2.0
    * gir1.2-gtk-3.0
    * gir1.2-peas-1.0

### 使用PPA安装 ###

    $ sudo add-apt-repository ppa:pandasunny/rhythmbox-baidu-music
    $ sudo apt-get update
    $ sudo apt-get install rhythmbox-baidu-music

### 使用git安装 ###

将插件安装到系统插件目录 (/usr/lib/rhythmbox/plugins/)：

    git clone https://github.com/pandasunny/rhythmbox-baidu-music.git
    cd rhythmbox-baidu-music
    sudo make install

或者安装的本地用户插件目录 (~/.local/share/rhythmbox/plugins/)：

    sudo make install-local

卸载插件，使用命令：

    sudo make uninstall

## 反馈 ##

请提交到github的反馈系统中 ([link](https://github.com/pandasunny/rhythmbox-baidu-music/issues))。
联系我：

* twitter ([@pandasunny](https://twitter.com/pandasunny)) 
* weibo ([@pandasunny](http://weibo.com/pandasunny))

## 许可 ##

GPL v3 License.
