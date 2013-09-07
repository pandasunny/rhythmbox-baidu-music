# -*- coding: utf-8 -*-

from base import BaseCall
from base import MUSICBOX_URL, TINGAPI_URL
from base import get_timestamp


class GetAll(BaseCall):
    """
    Get all playlists.

    Args:
        page_no: The number of page.
        page_size: The count of playlists in a page.

    Returns:
        Three variables includes "havemore", "total", "play_list".
        play_list = {
            "id": string,
            "title": string,
            "author":null,
            "tag":null,
            "description":null,
            "create_time": int,
            "covers":null,
            "song_count": string,
            "collected_count":null,
            "recommend_count":null,
            "songlist":null,
            "access_control":0,
            "diy_type":1,
            "status":null,
            "pic_180": string # playlist coverart
            }
    """
    url = TINGAPI_URL + "/v1/restserver/ting?"
    params = {
            "method": "ting.baidu.diy.getPlaylists",
            "format": "json",
            "from": "bmpc",
            "version": "1.0.0",
            "with_song": 0,
            # dynamic
            #"bduss": bduss,
            # custom
            #"page_no": page_no,
            #"page_size": page_size,
            }
    headers = {
            "Referer": "http://pc.music.baidu.com",
            "User-Agent": "bmpc_1.0.0"
            }

    def _parse(self, content):
        if content["error_code"] == 22000:
            result = content["havemore"], content["total"], content["play_list"]
        else:
            result = False
        return result

    def _dynamic(self):
        return {
                "bduss": BaseCall.bduss,
                "page_no": 0,
                "page_size": 50,
                }

    def _custom(self, params):
        for key in params.keys():
            params[key] = int(params[key])
        return params


class GetSongIDs(BaseCall):
    """
    Get all the ids of online playlist.

    Args:
        playlist_id: The id of online playlist.

    Returns:
        A list include all song ids.
        The response data is a dict like this:
        {
            "query": {
                "sid": "1",
                "playListId": the size of ids,
                "_": timestamp
            },
            "errorCode": the error(22000 is normal),
            "data": {
                "songIds": a list
            }
        }
    """
    url = MUSICBOX_URL + "/data/playlist/getDetail?"
    params = {
            "sid": 1,
            "_": get_timestamp(),
            #custom
            #"playListId": playlist_id,
            }

    def _parse(self, content):
        if content["errorCode"] == 22000:
            return content["data"]["songIds"]
        else:
            return False


class Add(BaseCall):
    """
    Add a playlist in cloud.

    Args:
        title: The title of a playlist which were been added.

    Returns:
        The id of playlist.
    """
    url = TINGAPI_URL + "/v1/restserver/ting?"
    params = {
            "method": "baidu.ting.diy.addList",
            "format": "json",
            "from": "bmpc",
            "version": "1.0.0",
            # dynamic
            #"bduss": bduss,
            # custom
            #"title": title,
            }
    headers = {
            "Referer": "http://pc.music.baidu.com",
            "User-Agent": "bmpc_1.0.0"
            }

    def _parse(self, content):
        if content["errorCode"] == 22000:
            return content["result"]["listId"]
        else:
            return False

    def _dynamic(self):
        return {"bduss": BaseCall.bduss, }


class Delete(BaseCall):
    """
    Delete a playlist in cloud.

    Args:
        playlist_id: The id of a playlist.

    Returns:
        A boolean.
    """
    url = TINGAPI_URL + "/v1/restserver/ting?"
    params = {
            "method": "baidu.ting.diy.delList",
            "format": "json",
            "from": "bmpc",
            "version": "1.0.0",
            # dynamic
            #"bduss": bduss,
            # custom
            #"listId": int(playlist_id),
            }
    headers = {
            "Referer": "http://pc.music.baidu.com",
            "User-Agent": "bmpc_1.0.0"
            }

    def _parse(self, content):
        return True if content["error_code"] == 22000 else False

    def _dynamic(self):
        return {"bduss": BaseCall.bduss, }

    def _custom(self, params):
        for key in params.keys():
            params[key] = int(params[key])
        return params


class Rename(BaseCall):
    """
    Rename a playlist in cloud.

    Args:
        playlist_id: The id of a playlist.
        title: The title of a playlist.

    Returns:
        A boolean.
    """
    url = TINGAPI_URL + "/v1/restserver/ting?"
    params = {
            "method": "baidu.ting.diy.upList",
            "format": "json",
            "from": "bmpc",
            "version": "1.0.0",
            # dynamic
            #"bduss": bduss,
            #custom
            #"listId": int(playlist_id),
            #"title": title,
            }
    headers = {
            "Referer": "http://pc.music.baidu.com",
            "User-Agent": "bmpc_1.0.0"
            }

    def _parse(self, content):
        return True if content["error_code"] == 22000 else False

    def _dynamic(self):
        return {"bduss": BaseCall.bduss, }

    def _custom(self, params):
        for key in params.keys():
            if key=="listId":
                params[key] = int(params[key])
        return params


class AddSongs(BaseCall):
    """
    Add songs to a playlist.

    Args:
        playlist_id: The id of a playlist.
        song_ids: The ids list of songs.

    Returns:
        A list includes the ids of songs which were added.
    """
    url = TINGAPI_URL + "/v1/restserver/ting?"
    params = {
            "method": "baidu.ting.diy.addListSong",
            "format": "json",
            "from": "bmpc",
            "version": "1.0.0",
            # dynamic
            #"bduss": bduss,
            #custom
            #"listId": int(playlist_id),
            #"songId": ",".join(map(str, song_ids)),
            }
    headers = {
            "Referer": "http://pc.music.baidu.com",
            "User-Agent": "bmpc_1.0.0"
            }

    def _parse(self, content):
        if content["error_code"] == 22000:
            return content["result"]["add"]
        else:
            return False

    def _dynamic(self):
        return {"bduss": BaseCall.bduss, }

    def _custom(self, params):
        for key in params.keys():
            if key=="listId":
                params[key] = int(params[key])
            if key=="songId":
                params[key] = ",".join(map(str, params[key]))
        return params


class DeleteSongs(BaseCall):
    """
    Delete songs to a playlist.

    Args:
        playlist_id: The id of a playlist.
        song_ids: The ids list of songs.

    Returns:
        A boolean.
    """
    url = TINGAPI_URL + "/v1/restserver/ting?"
    params = {
            "method": "baidu.ting.diy.delListSong",
            "format": "json",
            "from": "bmpc",
            "version": "1.0.0",
            # dynamic
            #"bduss": bduss,
            # custom
            #"listId": int(playlist_id),
            #"songId": ",".join(map(str, song_ids)),
            }
    headers = {
            "Referer": "http://pc.music.baidu.com",
            "User-Agent": "bmpc_1.0.0"
            }

    def _parse(self, content):
        return True if content["error_code"] == 22000 else False

    def _dynamic(self):
        return {"bduss": BaseCall.bduss, }

    def _custom(self, params):
        for key in params.keys():
            if key=="listId":
                params[key] = int(params[key])
            if key=="songId":
                params[key] = ",".join(map(str, params[key]))
        return params
