# -*- coding: utf-8 -*-

from base import BaseCall
from base import MUSICBOX_URL, TINGAPI_URL, MUSICMINI_URL
from base import get_timestamp


class GetInfo(BaseCall):
    """
    Get the information of baidu cloud music.

    Returns:
        A dict which has four items: cloud_surplus: the remaining quota;
        cloud_total: the quota; cloud_used: the used quota; level: the
        user's level, the possible values are 0, 1, 2.
    """
    url = MUSICMINI_URL + "/app/cloudMusic/spaceSongs.php?"

    def _dynamic(self):
        return {"bduss": BaseCall.bduss, }


class GetSongIDs(BaseCall):
    """
    Get all the ids of collect list.

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
            "_": get_timestamp()
            #custom
            #"start": start,
            #"size": size,
            }

    def _parse(self, content):
        if content["errorCode"] == 22000:
            song_ids = [song["id"] for song in content["data"]["songList"]]
            total = int(content["data"]["total"])
            return total, song_ids
        return False

    def _dynamic(self):
        return {"start": 0, "size": 200, }

    def _custom(self, params):
        for key in params.keys():
            params[key] = int(params[key])
        return params


class AddSongs(BaseCall):
    """
    Add songs to the collect list.

    Args:
        song_ids: A list of songs.

    Returns:
        A list of songs which were been added. Or False when failed.
    """
    url = TINGAPI_URL + "/v1/restserver/ting?"
    params = {
            "method": "baidu.ting.favorite.addSongFavorites",
            "format": "json",
            "from": "bmpc",
            "version": "1.0.0",
            # dynamic
            #"bduss": bduss,
            # custom
            #"songId": ",".join(map(str, song_ids)),
            }
    headers = {
            "Referer": "http://pc.music.baidu.com",
            "User-Agent": "bmpc_1.0.0"
            }

    def _parse(self, content):
        if content["error_code"] == 22000:
            return content["result"]
        else:
            return False

    def _dynamic(self):
        return {"bduss": BaseCall.bduss, }

    def _custom(self, params):
        for key in params.keys():
            if key=="songId":
                params[key] = ",".join(map(str, params[key]))
        return params


class DeleteSongs(BaseCall):
    """
    Remove songs from the collect list.

    Args:
        song_ids: A list of songs.

    Returns:
        A boolean.
    """
    url = TINGAPI_URL + "/v1/restserver/ting?"
    params = {
            "method": "baidu.ting.favorite.delCollectSong",
            "format": "json",
            "from": "bmpc",
            "version": "1.0.0",
            # dynamic
            #"bduss": bduss,
            # custom
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
            if key=="songId":
                params[key] = ",".join(map(str, params[key]))
        return params
