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

class InvalidTokenError(Exception):pass
class InvalidUsernameError(Exception): pass
class InvalidLoginError(Exception): pass


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
        self.__hao123Param = ""     # the string "BDU" of cross domain
        self.islogin = False        # a boolean of login

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
                ("User-Agent", "Mozilla/5.0 (X11; Linux i686) \
                        AppleWebKit/537.36 (KHTML, like Gecko) \
                        Chrome/29.0.1547.0 Safari/537.36")
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
            print "Error code: ", e.code
        except urllib2.URLError as e:
            print "We failed to reach a server."
            print "Reason: ", e.reason
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
        self.__request(PASSPORT_URL, "HEAD")
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
        response = json.loads(self.__request(url, "GET", params))

        if response["errInfo"]["no"] == "0":
            self.__token = response["data"]["token"]
            self.__codestring = response["data"]["codeString"]
            logging.debug("login token: " + self.__token)
            logging.debug("login codestring: " + self.__codestring)
        else:
            raise TokenError("Get token faild.")

    def __login_perform(self, username, password, remember):
        """ Post the username and password for login.

        Get html data and find two variables: err_no and hao123Param in
        javascript code.
        The 'err_no' string has three values:
            err_no = 2: username invalid
            err_no = 4: username or password invalid
            err_no = 0: login successed

        Args:
            username: The user's login name
            password: The user's password
            remember: A boolean if remembered the username and the password

        Raises:
            InvalidUsernameError: An error occurred post the invalid username.
            InvalidLoginError: An error occurred post the invalid username or
                the invalid password.

        TODO:
            1.use the phone number to login the baidu music
            2.when err_no = 257, use the codestring
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
            "verifycode": "",
            "ppui_logintime": random.randint(1000, 99999),
            "callback": ""
            }
        if remember:
            params["mem_pass"] = "on"

        response = self.__request(url, "POST", params)

        errno = response[response.find("err_no=")+len("err_no=")]

        if errno == "0":
            logging.info("Login successed!")
            pos = response.rfind("hao123Param=")
            self.__hao123Param = response[pos+len("hao123Param="):pos+len("hao123Param=")+256]
            logging.debug("The cross domain param 'bdu': " + self.__hao123Param)
        elif errno == "2":
            logging.error("The username is invalid.")
            raise InvalidUsernameError()
        elif errno == "4":
            logging.error("The username or password is invalid.")
            raise InvalidLoginError()

    def __login_cross_domain(self):
        """ Cross domain login """
        params = {
            "bdu": self.__hao123Param,
            "t": int(time.time())
            }
        self.__request(CROSSDOMAIN_URL, "HEAD", params)
        for cookie in self.__cj:
            if (cookie.name == 'BDUSS') and (cookie.domain == '.baidu.com'):
                logging.info("Cross domain login successed")
                self.__bduss = cookie.value
                logging.debug("The cookie 'BDUSS': " + cookie.value)

    def login(self, username, password, remember=True):
        """ Login baidu music.

        Args:
            username: The user's login name
            password: The user's password
            remember: A boolean if remembered the username and the password

        Returns:
            A boolean whether the client has logged on.
        """
        if not self.islogin:
            self.__login_get_id()
            self.__login_get_token()
            self.__login_perform(username, password, remember)
            self.__login_cross_domain()
            self.islogin = True
        return self.islogin

    def logout(self):
        """ Logout baidu music """
        self.__cj.clear()
        self.__save_cookie()
        self.islogin = False
        logging.info("Logout successed!")
