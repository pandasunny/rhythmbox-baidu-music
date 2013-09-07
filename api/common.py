# -*- coding: utf-8 -*-

from base import BaseCall
from base import CLIENTVER
from base import MUSICBOX_URL, TINGAPI_URL, MUSICMINI_URL
from user import is_login


class GetSongInfo(BaseCall):
    """
    Get basic information of songs whose id in the param 'song_ids'.

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
    method = "POST"
    url = MUSICBOX_URL + "/data/music/songinfo"
    #custom_params = {
            #"songIds": ",".join(map(str, song_ids))
            #}

    def _parse(self, content):
        if content["errorCode"] == 22000:
            return content["data"]["songList"]
        return False

    def _custom(self, params):
        for key in params.keys():
            if key=="songIds":
                params[key] = ",".join(map(str, params[key]))
        return params


class GetSongLinks(BaseCall):
    """
    Get the informations about song's links.

    Args:
        song_ids: A list includes the song ids.
        link_type: A boolean about link which be got.
        is_hq: A boolean.

    Returns:
        A list is the response which is as follows:
        [{
            song_id: (int)the song id,
            song_title: (str)the song title,
            append: (null),
            song_artist: (str)artist,
            album_title: (str)album title,
            album_image_url: (null),
            lyric_url: (str)lyric file url,
            version: (null),
            copy_type: (str)unknown(1),
            resource_source: (str)source,
            has_mv: (str)undefined,
            file_list: [{
                file_id: (int)file id,
                url: (str)the song url,
                display_url: (str)the song display url,
                format: (str)format(ma3, flac),
                hash: (str)hash,
                size: (int)filesize,
                kbps: (int)rate,
                duration: (int)time,
                url_expire_time: (int)expire time,
                is_hq: (int)is HQ file
            }, ...]
        }, ...]
    """
    url = MUSICMINI_URL + "/app/link/getLinks.php?"
    params = {
            "songArtist": "",
            "songTitle": "",
            "songAppend": "",
            "clientVer": CLIENTVER,
            "isCloud": 0,
            "hasMV": "undefined"
            # dynamic
            #"isLogin": int(islogin),
            # custom
            #"songId": "@@".join(map(str, song_ids)),
            #"linkType": int(link_type),
            #"isHq": int(is_hq),
            }

    def _dynamic(self):
        global is_login
        return {
                "isLogin": int(is_login),
                "linkType": int(False),
                "isHq": int(False),
                }

    def _custom(self, params):
        for key in params.keys():
            if key=="songId":
                params[key] = "@@".join(map(str, params[key]))
            elif key in ["linkType", "isHq"]:
                params[key] = int(params[key])
        return params


class Search(BaseCall):
    """
    Search songs with keywords.

    Args:
        keyword: the keyword with music.
        page_no: the search page number.
        page_size: the size of songs per page.

    Returns:
        A dict about songs and other informations.
    """
    url = TINGAPI_URL + "/v1/restserver/ting?"
    params = {
            "method": "baidu.ting.search.common",
            "format": "json",
            "from": "bmpc",
            "version": "1.0.0",
            # custom
            #"page_size": page_size,
            #"page_no": page_no,
            #"query": keyword,
            }

    def _dynamic(self):
        return {"page_size": 1, "page_no": 25, }

    def _custom(self, params):
        for key in params.keys():
            if key!="query":
                params[key] = int(params[key])
        return params
