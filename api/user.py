# -*- coding: utf-8 -*-

import re
import random
import logging

from base import BaseCall
from base import PASSPORT_URL, MUSICMINI_URL, CROSSDOMAIN_URL
from base import CLIENTVER, TPL, APIVER
from base import get_timestamp

from exception import InvalidTokenError, InvalidUsernameError
from exception import InvalidLoginError, InvalidVerifyCodeError
from exception import MissVerifyCodeError

is_login = False


def login(username, password, remember=True, isphone=False, verifycode=""):
    """
    Log in baidu music.

    Args:
        username: The user's login name
        password: The user's password
        isphone: A boolean if the username is phone number
        remember: A boolean if remembered the username and the password
        verifycode: The verify code from image

    Returns:
        A boolean whether the client has logged on.
    """
    global is_login
    if not is_login:
        GetID().run()
        GetToken().run()
        if CheckLogin().run({
            "username": username,
            "isphone": "true" if isphone else "false",
            }):
            raise MissVerifyCodeError()
        is_login = DoLogin().run({
            "username": username,
            "password": password,
            "remember": "on" if remember else "off",    #TODO: remember=False
            "verifycode": verifycode,
            "isphone": "true" if isphone else "false",
            })
        CrossDomain().run()
        GetBduss().run()
    return bool(is_login)

def logout():
    """
    Log out baidu music.

    Returns:
        A boolean whether the client has logged out.
    """
    global is_login
    BaseCall().cj.clear()
    BaseCall().save()
    is_login = False
    return not is_login

def getCaptche():
    """
    Get the captche image.

    Returns:
        The image file content.
    """
    return GetCaptcha().run()


class BaseLoginCall(BaseCall):
    """
    The base login class.
    """
    token = ""
    codestring = ""
    bdu = ""


class GetID(BaseLoginCall):
    """
    Get the cookie 'BAIDUID'.
    """
    method = "HEAD"
    url = PASSPORT_URL + "/passApi/js/wrapper.js?"
    params = {
            "cdnversion": get_timestamp(),
            "_": get_timestamp()
            }


class GetToken(BaseLoginCall):
    """
    Get the token string.

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
    url = PASSPORT_URL + "/v2/api/?getapi&"
    params = {
            "tpl": TPL,
            "apiver": APIVER,
            "tt": get_timestamp(),
            "class": "login",
            "logintype": "basicLogin",
            "callback": ""
            }

    def _parse(self, content):
        if content["errInfo"]["no"] == "0":
            BaseLoginCall.token = content["data"]["token"]
            BaseLoginCall.codestring = content["data"]["codeString"]
            logging.debug("Token: " + BaseLoginCall.token)
            logging.debug("Codestring: " + BaseLoginCall.codestring)
        else:
            raise InvalidTokenError("Get token faild.")
        return True


class CheckLogin(BaseLoginCall):
    """
    Check login status.

    Returns:
        A boolean about codestring. If the codestring is true, visit the
    url "https://passport.baidu.com/cgi-bin/genimage?<codestring>" to get
    a captcha image. The get image function is self.get_captcha().
    """
    url = PASSPORT_URL + "/v2/api/?logincheck&"
    params = {
            #"token": BaseLoginCall.token,  # dynamic
            #"username": username,          # custom
            #"isphone": "false",            # custom
            "tpl": TPL,
            "apiver": APIVER,
            "tt": get_timestamp(),
            "callback": ""
            }

    def _parse(self, content):
        BaseLoginCall.codestring = content["data"]["codeString"]
        return bool(BaseLoginCall.codestring)

    def _dynamic(self):
        return {"token": BaseLoginCall.token, }

    def _custom(self, params):
        for key in params.keys():
            if key=="isphone":
                params[key] = str(params[key]).lower()
        return params


class GetCaptcha(BaseLoginCall):
    """
    Get the captcha image.

    Returns:
        A file byte about the image.
    """
    url = PASSPORT_URL + "/cgi-bin/genimage?" + BaseLoginCall.codestring
    types = "html"


class DoLogin(BaseLoginCall):
    """
    Post the username and password for login.

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
    method = "POST"
    url = PASSPORT_URL + "/v2/api/?login"
    params = {
            "staticpage": MUSICMINI_URL + "/app/passport/jump.html",
            "charset": "utf-8",
            "tpl": TPL,
            "apiver": APIVER,
            "tt": get_timestamp(),
            "safeflg": 0,
            "u": "",
            "quick_user": 0,
            "ppui_logintime": random.randint(1000, 99999),
            "callback": ""
            # dynamic
            #"token": BaseLoginCall.token,
            #"codestring": BaseLoginCall.codestring,
            #custom
            #"username": username,
            #"password": password,
            #"isphone": "false",
            #"mem_pass": "on",
            #"verifycode": verifycode,
            }
    types = "html"

    def _parse(self, content):
        try:
            errno = re.search("err_no=(\d+)", content).group(1)
        except Exception, e:
            raise LoginError()

        if errno == "0":
            logging.info("Login successed!")
            BaseLoginCall.bdu = re.search("hao123Param=(\w+)", content).group(1)
            logging.debug("The cross domain param 'bdu': " + self.bdu)
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
        return True

    def _dynamic(self):
        return {
                "token": BaseLoginCall.token,
                "codestring": BaseLoginCall.codestring,
                "mem_pass": "on",
                "verifycode": "",
                "isphone": "false",
                }

    def _custom(self, params):
        for key in params.keys():
            if key=="isphone":
                params[key] = str(params[key]).lower()
            elif key=="mem_pass":
                params[key] = "on" if params[key] else "off"
        return params


class CrossDomain(BaseLoginCall):
    """
    Cross domain login with hao123.com.
    """
    method = "HEAD"
    url = CROSSDOMAIN_URL
    params = {
        "t": get_timestamp(),
        # dynamic
        #"bdu": BaseLoginCall.bdu,
        }

    def _dynamic(self):
        return {"bdu": BaseLoginCall.bdu, }


class GetBduss(BaseLoginCall):
    """
    Get the bduss value.
    """
    url = MUSICMINI_URL + "/app/passport/getBDUSS.php"
    types = "html"

    def _parse(self, content):
        BaseLoginCall.bduss = content[1:-1]
        logging.debug("bduss: %s" % self.bduss)
        return True
