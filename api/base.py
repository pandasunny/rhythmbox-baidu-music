# -*- coding: utf-8 -*-

#import os
import urllib
import urllib2
import cookielib
import zlib
import json
import time
import logging

MUSICBOX_URL = "http://play.baidu.com"
TINGAPI_URL = "http://tingapi.ting.baidu.com"
PASSPORT_URL = "https://passport.baidu.com"
MUSICMINI_URL = "http://musicmini.baidu.com"
CROSSDOMAIN_URL = "http://user.hao123.com/static/crossdomain.php?"

CLIENTVER = "8.1.3.1"  # BaiduMusic"s client version 
APIVER = "v3"          # Baidu Music API version 3
TPL = "qianqian"       # The template of TTPlayer


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

def get_timestamp():
    return int(time.time())


class BaseCall(object):
    """
    The base call class of GET/POST/HEAD http.
    """
    cj = None
    cookie = ""
    bduss = ""

    method = "GET"      # HEAD, GET, POST
    url = ""
    params = {}
    headers = {}
    types = "json"      # xml, json or html

    def run(self, params={}):
        self.params.update(self._dynamic())
        self.params.update(self._custom(params))
        params = urllib.urlencode(self.params)

        if self.method == "GET":
            request = urllib2.Request(self.url + params, None)
        elif self.method == "POST":
            request = urllib2.Request(self.url, params)
        elif self.method == "HEAD":
            request = urllib2.Request(self.url + params, None)
            request.get_method = lambda: "HEAD"

        for key,value in self.headers.iteritems():
            request.add_header(key, value)

        response = urllib2.urlopen(request)
        self.save()
        result = self.parse(response) if self.method != "HEAD" else True
        return result

    def parse(self, response):
        info, content = response.info(), response.read()

        # unzip the content of response
        if "Content-Encoding" in info and info["Content-Encoding"] == "gzip":
            content = zlib.decompress(content, 16+zlib.MAX_WBITS)

        # init parse the content
        if self.types=="json":
            content = json.loads(content)
        elif self.types=="xml":
            content = content   #TODO: parse xml
        else:
            content

        # parse the content
        result = self._parse(content)
        return result

    def save(self):
        if isinstance(self.cj, cookielib.LWPCookieJar):
            self.cj.save()

    # replace the functions: _parse, _dynamic, _custom
    def _parse(self, content):
        logging.debug(content)
        return content

    def _dynamic(self):
        return {}

    def _custom(self, params):
        return params


class InitCall(BaseCall):
    """
    Initialize the base call class.
    """
    def __init__(self, cookie, debug=False):

        if debug:
            logging.basicConfig(
                    format="%(asctime)s - %(levelname)s - %(message)s",
                    level=logging.DEBUG
                    )

        BaseCall.cookie = cookie
        logging.debug("The cookie file is %s" % BaseCall.cookie)

        if self.cookie:
            BaseCall.cj = cookielib.LWPCookieJar(self.cookie)
            try:
                BaseCall.cj.revert()
            except Exception, e:
                BaseCall.cj.save()
        else:
            BaseCall.cj = cookielib.CookieJar()

        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cj))
        opener.addheaders = [
                ("Accept", "*/*"),
                ("Accept-Language", "zh-CN"),
                ("Accept-Encoding", "gzip, deflate"),
                ("User-Agent", "Mozilla/4.0 (compatible; MSIE 7.0; \
                        Windows NT 6.1; Trident/6.0; SLCC2; \
                        .NET CLR 2.0.50727; .NET CLR 3.5.30729; \
                        .NET CLR 3.0.30729; Media Center PC 6.0; \
                        .NET4.0C; .NET4.0E)")
                ]
        urllib2.install_opener(opener)
