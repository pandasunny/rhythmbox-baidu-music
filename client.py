# -*- coding: utf-8 -*-

import os
import logging
import re
import random
import time
import datetime
import urllib
import urllib2
import cookielib
import zlib
import json

def warp_gm_time(fun):
    """ The hook of gm time. """
    def _warp_gm_time(*args):
        args=list(args)
        if args[0]>1899962739:
            args[0]=1899962739
        return fun(*args)
    if  hasattr( fun,'_is_hook'):
        return fun
    _warp_gm_time._is_hook=1
    return _warp_gm_time
time.gmtime=warp_gm_time(time.gmtime)

PASSPORT_URL = "https://passport.baidu.com"
CROSSDOMAIN_URL = "http://user.hao123.com/static/crossdomain.php?"
TTPLAYER_URL = "http://qianqianmini.baidu.com"
MUSICBOX_URL = "http://play.baidu.com"
#REFERER_URL = "http://qianqianmini.baidu.com/app/passport/passport_phoenix.html"
#CROSSDOMAIN_REFERER_URL = "http://qianqianmini.baidu.com/app/passport/index.htm"

class InvalidTokenError(Exception):pass
class InvalidUsernameError(Exception): pass
class InvalidLoginError(Exception): pass
class InvalidVerifyCodeError(Exception): pass
class MissVerifyCodeError(Exception): pass


class Client(object):
    """ The class of Baidu Music Client

    Attributes:
        cookie: The name of a file in which you want to save cookies. If its
                value is None, you mean that do not save cookies.
        debug: A boolean indicating if show the debug information or not.
    """

    def __init__(self, cookie="", debug=False):
        """ Initialize the baidu music client class. """

        self.CLIENTVER = "7.0.4"    # TTPlayer"s client version 
        self.APIVER = "v3"          # Baidu Music API version 3
        self.TPL = "qianqian"       # The template of TTPlayer

        self.__bduss = ""           # the string "BDUSS" of cookie
        self.__token = ""           # login token
        self.__codestring = ""      # login codestring
        self.__bdu = ""     # the string "BDU" of cross domain
        self.islogin = False        # a boolean of login

        #self.__cloud = {}           # the cloud information dict
        self.total = 0              # the count of songs in collect list

        if debug:
            logging.basicConfig(format="%(asctime)s - %(levelname)s - \
                    %(message)s", level=logging.DEBUG)

        # If the param "cookie" is a filename, create a cookiejar with the file
        # and check the cookie to comfire whether the client has logged on.

        if cookie:
            self.__cj = cookielib.LWPCookieJar(cookie)
            if os.path.isfile(cookie):
                self.__cj.revert()
                for cookie in self.__cj:
                    if cookie.name == "BDUSS" and cookie.domain == ".baidu.com":
                        logging.info("Login successed!")
                        self.__bduss = cookie.value
                        logging.debug("The cookie 'BDUSS': " + cookie.value)
                        self.islogin = True
        else:
            self.__cj = cookielib.CookieJar()

        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.__cj))
        opener.addheaders = [
                ("Accept", "*/*"),
                ("Accept-Language", "zh-CN"),
                ("Accept-Encoding", "gzip, deflate"),
                ("User-Agent", "Mozilla/4.0 (compatible; MSIE 7.0; \
                        Windows NT 6.1; Trident/6.0; SLCC2; \
                        .NET CLR 2.0.50727; .NET CLR 3.5.30729; \
                        .NET CLR 3.0.30729; Media Center PC 6.0; \
                        .NET4.0C; .NET4.0E)")
                #("User-Agent", "Mozilla/5.0 (X11; Linux i686) \
                        #AppleWebKit/537.36 (KHTML, like Gecko) \
                        #Chrome/29.0.1547.0 Safari/537.36")
                ]
        urllib2.install_opener(opener)

    def __request(self, url, method, params={}, headers={}):
        """ HEAD/POST/GET the date with urllib2.

        Args:
            url: A url which you want to fetch.
            method: A method which one of HEAD, POST, GET.
            params: A dict mapping the parameters.
            headers: A dict mapping the custom headers.

        Returns:
            A string include the response. Or a boolean if method is HEAD.

        Raises:
            HTTPError: urllib2.HTTPError
            URLError: urllib2.URLError
        """

        params = urllib.urlencode(params)

        if method == "GET":
            request = urllib2.Request(url + params, None)
        elif method == "POST":
            request = urllib2.Request(url, params)
        elif method == "HEAD":
            request = urllib2.Request(url + params, None)
            request.get_method = lambda: "HEAD"

        for key in headers:
            request.add_header(key, headers[key])

        try:
            response = urllib2.urlopen(request)
        except urllib2.HTTPError as e:
            print "The server couldn't fulfill the request."
            print url
            print "Error code: " +  e.code
        except urllib2.URLError as e:
            print "We failed to reach a server."
            print url
            print "Reason: " + e.reason
        else:
            self.__save_cookie()
            result = self.unzip(response) if method != "HEAD" else True
            return result

    def __save_cookie(self):
        """ Save the cookie string as a file """
        if isinstance(self.__cj, cookielib.LWPCookieJar):
            self.__cj.save()

    @staticmethod
    def unzip(response):
        """ Decompress the zip response.

        Args:
            response: A file-like object which the function urllib2.urlopen
                    returns.

        Returns:
            A string which be decompress.
        """
        info, result = response.info(), response.read()
        if "Content-Encoding" in info and info["Content-Encoding"] == "gzip":
            try:
                result = zlib.decompress(result, 16+zlib.MAX_WBITS)
            except Exception as e:
                print "Decompress the response failed."
        return result

    def __login_get_id(self):
        """ Get the cookie 'BAIDUID' """
        timestamp = int(time.time())
        url = PASSPORT_URL + "/passApi/js/wrapper.js?"
        params = {
                "cdnversion": timestamp,
                "_": timestamp
                }
        #headers = {"Referer": REFERER_URL}
        self.__request(url, "HEAD", params)
        for cookie in self.__cj:
            if (cookie.name == 'BAIDUID') and (cookie.domain == '.baidu.com'):
                logging.debug("The cookie 'BAIDUID': " + cookie.value)

    def __login_get_token(self):
        """ Get the token string

        Returns:
            A dict which include the token string and the codestring string. The
        dict is as follows:
        {
            "errInfo": { "no": the errno },
            "data": {
                "rememberedUserName": the remembered username,
                "codeString": the codestring,
                "token":the token string,
                "cookie": unknown
            }
        }

        Raises:
            InvalidTokenError: An error occurred get the error token string.
        """
        params = {
            "tpl": self.TPL,
            "apiver": self.APIVER,
            "tt": int(time.time()),
            "class": "login",
            "callback": ""
            }
        url = PASSPORT_URL + "/v2/api/?getapi&"
        #headers = {"Referer": REFERER_URL}
        response = json.loads(self.__request(url, "GET", params))

        if response["errInfo"]["no"] == "0":
            self.__token = response["data"]["token"]
            self.__codestring = response["data"]["codeString"]
            logging.debug("login token: " + self.__token)
            logging.debug("login codestring: " + self.__codestring)
        else:
            raise TokenError("Get token faild.")

    def login_check(self, username):
        """ Check login status.

        Returns:
            A boolean about codestring. If the codestring is true, visit the
        url "https://passport.baidu.com/cgi-bin/genimage?<codestring>" to get
        a captcha image. The get image function is self.get_captcha().
        """
        #callback = self.__getCallbackString()
        callback = ""
        url = PASSPORT_URL + "/v2/api/?logincheck&"
        params = {
            "token": self.__token,
            "tpl": self.TPL,
            "apiver": self.APIVER,
            "tt": int(time.time()),
            "username": username,
            "isphone": "false",
            "callback": callback
            }
        #headers = {"Referer": CROSSDOMAIN_REFERER_URL}
        response = self.__request(url, "GET", params)
        self.__codestring = response["data"]["codeString"]
        return bool(self.__codestring)

    def get_captcha(self):
        """ Get the captcha image.

        Returns:
            A file byte about the image.
        """
        url = PASSPORT_URL + "/cgi-bin/genimage?" + self.__codestring
        response = self.__request(url, "GET")
        return response

    def __login(self, username, password, verifycode=None, remember=True):
        """ Post the username and password for login.

        Get html data and find two variables: err_no and hao123Param in
        javascript code.
        The 'err_no' string has three values:
            err_no = 0: login successed
            err_no = 2: username invalid
            err_no = 4: username or password invalid
            err_no = 6: captcha invalid
            err_no = 257: use captcha

        Args:
            username: The user's login name
            password: The user's password
            verifycode: The verify code from image
            remember: A boolean if remembered the username and the password

        Raises:
            InvalidUsernameError: An error occurred post the invalid username.
            InvalidLoginError: An error occurred post the invalid username or
                the invalid password.
            InvalidVerifyCodeError: An error occurred input the invalid verifycode.
            MissVerifyCodeError: An error occurred do not input the verifycode.

        TODO:
            1.use the phone number to login the baidu music
        """
        url = PASSPORT_URL + "/v2/api/?login"
        params = {
            "staticpage": TTPLAYER_URL + "/app/passport/jump1.html",
            "charset": "utf-8",
            "token": self.__token,
            "tpl": self.TPL,
            "apiver": self.APIVER,
            "tt": int(time.time()),
            "codestring": self.__codestring,
            "isphone": "false",
            "safeflg": 0,
            "u": "",
            "username": username,
            "password": password,
            "verifycode": verifycode,
            "ppui_logintime": random.randint(1000, 99999),
            "callback": ""
            }
        if remember:
            params["mem_pass"] = "on"
        #headers = {"Referer": REFERER_URL}
        response = self.__request(url, "POST", params)

        errno = re.search("err_no=(\d+)", response).group(1)
        if errno == "0":
            logging.info("Login successed!")
            self.__bdu = re.search("hao123Param=(\w+)", response).group(1)
            logging.debug("The cross domain param 'bdu': " + self.__bdu)
        elif errno == "2":
            logging.error("The username is invalid.")
            raise InvalidUsernameError()
        elif errno == "4":
            logging.error("The username or password is invalid.")
            raise InvalidLoginError()
        elif errno == "6":
            logging.error("The captcha is invalid.")
            raise InvalidVerifyCodeError()
        elif errno == "257":
            logging.error("Please input the captcha.")
            raise MissVerifyCodeError()

    def __login_cross_domain(self):
        """ Cross domain login """
        params = {
            "bdu": self.__bdu,
            "t": int(time.time())
            }
        #headers = {"Referer": CROSSDOMAIN_REFERER_URL}
        self.__request(CROSSDOMAIN_URL, "HEAD", params)
        for cookie in self.__cj:
            if (cookie.name == 'BDUSS') and (cookie.domain == '.baidu.com'):
                logging.info("Cross domain login successed")
                self.__bduss = cookie.value
                logging.debug("The cookie 'BDUSS': " + cookie.value)

    def login(self, username, password, verifycode=None, remember=True):
        """ Login baidu music.

        Args:
            username: The user's login name
            password: The user's password
            verifycode: The verify code from image
            remember: A boolean if remembered the username and the password

        Returns:
            A boolean whether the client has logged on.
        """
        if not self.islogin:
            self.__login_get_id()
            self.__login_get_token()
            self.__login(username, password, remember)
            self.__login_cross_domain()
            self.islogin = True
        return int(self.islogin)

    def logout(self):
        """ Logout baidu music """
        self.__cj.clear()
        self.__save_cookie()
        self.islogin = False
        logging.info("Logout successed!")

    def __get_cloud_info(self):
        """ Get the information of baidu cloud music.

        Returns:
            A dict which has four items: cloud_surplus: the remaining quota;
            cloud_total: the quota; cloud_used: the used quota; level: the
            user's level, the possible values are 0, 1, 2.
        """
        url = TTPLAYER_URL + "/app/cloudMusic/spaceSongs.php?"
        params = {"bduss": self.__bduss}
        response = json.loads(self.__request(url, "GET", params))
        logging.debug("cloud_total: %s; cloud_used: %s; cloud_surplus: %s",
                response["cloud_total"], response["cloud_used"],
                response["cloud_surplus"])
        return response

    def get_collect_ids(self, start, size=200):
        """ Get all the ids of collect list.

        Returns:
            A list include all song ids.
            The response data is a dict like this:
            {
                "query": {
                    "cloud_type": unknown,
                    "type": "song",
                    "start": the start number,
                    "size": the size of ids,
                    "_": timestamp
                },
                "errorCode": the error(22000 is normal),
                "data": {
                    "quota": the cloud quota,
                    "songList": [{
                        "id": the song id,
                        "ctime": ctime
                    }, ... ]
                }
            }
        """
        url = MUSICBOX_URL + "/data/mbox/collectlist?"
        params = {
            "cloud_type": 0,
            "type": "song",
            "start": start,
            "size": size,
            "_": int(time.time())
            }
        response = json.loads(self.__request(url, "GET", params))
        if response["errorCode"] == 22000:
            song_ids = [song["id"] for song in response["data"]["songList"]]
            logging.debug("The total of song: %i", len(song_ids))
            logging.debug("The song IDs: %s", str(song_ids))
            self.total = int(response["data"]["total"])
            return song_ids
        return False

    def get_song_info(self, song_ids):
        """ Get basic information of songs whose id in the param 'song_ids'.

        Returns:
            A list includes the dicts of song. This list is a part of response.
            The response data is a dict like this:
            {
                "errorCode": the error(22000 is normal),
                "data": {
                    "songList": [{
                        "queryId": the song id,
                        "albumId": the album id,
                        "albumName": the album title,
                        "artistId": the artist id,
                        "artistName": the artist name,
                        "songId": the song id,
                        "songName": the song title,
                        "songPicBig": the big cover,
                        "songPicRadio": the radio cover,
                        "songPicSmall": the small cover,
                        "del status": 0, # unknown
                        "relateStatus": 0, # unknown
                        "resourceType": 0 #unknown
                    }, ... ]
                }
            }
        """
        url = MUSICBOX_URL + "/data/music/songinfo"
        params = {"songIds": ",".join(map(str, song_ids))}
        response = json.loads(self.__request(url, "POST", params))
        if response["errorCode"] == 22000:
            result = response["data"]["songList"]
            logging.debug("The song list: %s", str(result))
            return result
        return False

    def get_song_links(self, song_ids, artist=[], title=[], link_type="stream"):
        """ Get the informations about song's links.

        Args:
            song_ids: A list includes the song ids.
            artist: A list includes the song's artists.
            title: A list includes the song's titles.
            link_type: A string about link which be got, stream or all.

        Returns:
            A dict is the response which is as follows:
            {
                albumName: the album title,
                artist: the artist of song,
                songID: the song id,
                title: the song title,
                URL: the URL which be shown,
                fileslist: [{
                    album_pic_small: the small cover,
                    expiretimespan: unknown,
                    fileID: the file id,
                    format: the format of file such as mp3, flac and so on,
                    hash: the hash of file,
                    lrclink: the lyric url,
                    rate: the rate of file,
                    resource_type: unknown,
                    size: the size of file,
                    songLink: the url of song,
                    songShowLink: the shown url of song,
                    static: unknown,
                    time: the time of song
                }, ... ]
            }
        """
        url = TTPLAYER_URL + "/app/link/getLinks.php?"
        params = {
            "songId": "@@".join(map(str, song_ids)),
            "songArtist": "@@".join(artist),
            "songTitle": "@@".join(title),
            "linkType": {"stream": 0, "all": 1}.get(link_type),
            "isLogin": int(self.islogin),
            "clientVer": self.CLIENTVER
            }
        response = json.loads(self.__request(url, "GET", params))
        return response

    def search(self, keyword, page=1):
        """ Search songs with keywords.

        Args:
            keyword: the keyword with music.
            page: the search page number.

        Returns:
            A dict about songs and others:
            {
                count: the count of songs,
                page: the current page number,
                num: the number of songs per page,
                song: [{
                    id: the song id,
                    url: the song shown url,
                    artist: the artist of song,
                    title: the title of song,
                    album: the album of song,
                    # num: unknown
                    }, ...
                ]
            }
        """
        url = TTPLAYER_URL + "/app/search/searchList.php?"
        params = {
                "qword": keyword,
                "page": page
                }
        response = self.__request(url, "GET", params, {})
        songs = []  # the songs list

        # Get all songs from this search page with re. The example page is in
        # url(http://qianqianmini.baidu.com/app/search/searchList.php?qword=).
        # old resong
        #reSong = re.compile(r"<td class='uName'><[^>]+?"
                #r"title=\"(?P<album>[^\"]*)\">.+\n"
                #r".+?addSong\("
                #r"'(?P<id>\d*)','(?P<url>[^']*)','(?P<artist>[^']*)',"
                #r"'(?P<title>[^']*)','(?P<num>\d*)'\)\"", re.MULTILINE)
        reSong = re.compile(r"<td class='uName'><[^>]+?"
                r"title=\"(?P<album>[^\"]*)\">.+\n"
                r".+?addSong\("
                r"'(?P<id>\d*)','(?P<url>[^']*)','(?P<artist>[^']*)',"
                r"'(?P<title>[^']*)',[^\"]+\"", re.MULTILINE)
        for song in reSong.finditer(response):
            songs.append({
                "id": song.group("id"),
                "url": song.group("url"),
                "artist": song.group("artist"),
                "title": song.group("title"),
                "album": song.group("album"),
                #"num": song.group("num")
                })

        # Get the page information.
        rePage = re.compile(r"pageLink\([^']+'[^']*'\)\),\s*"
                r"(?P<count>\d+),\s*"
                r"(?P<page>\d+),\s*"
                r"(?P<num>\d+)")
        page = rePage.search(response)
        if page:
            result = {
                    "count": int(page.group("count")),
                    "page": int(page.group("page")),
                    "num": int(page.group("num")),
                    "songs": songs
                    }
        else:
            result = {}
        return result

    def add_favorite_songs(self, song_ids):
        """ Add some songs from baidu cloud.

        Args:
            song_ids: A list includes all ids of songs.

        Returns:
            A boolean "False" or a list includes the dicts of song.
        """
        url = MUSICBOX_URL + "/data/user/collect"
        params = {
            "ids": ",".join(map(str, song_ids)),
            "type": "song",
            "cloud_type": 0
            }
        headers = {"Referer": "http://play.baidu.com/"}

        response = json.loads(self.__request(url, "POST", params, headers))
        if response["errorCode"] == 22000:
            ids = response["data"]["collectIds"]
            ids = [ids] if isinstance(ids, int) else ids
            if ids:
                logging.debug("The successful collection of songs: %s", str(ids))
                return self.get_song_info(ids)
        return False

    def remove_favorite_songs(self, song_ids):
        """ Remove some songs from baidu cloud.

        Args:
            song_ids: A list includes all ids of songs.

        Returns:
            A boolean.
        """
        url = MUSICBOX_URL + "/data/user/deletecollectsong"
        params = {
            "songIds": ",".join(map(str, song_ids)),
            "type": "song"
            }

        response = json.loads(self.__request(url, "POST", params))
        result = True if response["errorCode"] == 22000 else False
        logging.debug("The deleted collection of songs: %s", str(song_ids))
        return result

