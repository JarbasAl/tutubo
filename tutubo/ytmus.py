import json
import time
from ytmusicapi import YTMusic

from tutubo.models import YoutubePreview, Video

_YTMUS = None


def _get_ytmus(max_retries=5):
    """ attempt at avoiding rate limiting errors, avoid creating YTMusic objects unnecessarily

      for v in search_yt_music(phrase, as_dict=False):
      File "/usr/lib/python3.10/site-packages/tutubo/ytmus.py", line 127, in search_yt_music
        ytmusic = YTMusic()
      File "/usr/lib/python3.10/site-packages/ytmusicapi/ytmusic.py", line 96, in __init__
        self.headers.update(get_visitor_id(self._send_get_request))
      File "/usr/lib/python3.10/site-packages/ytmusicapi/helpers.py", line 63, in get_visitor_id
        response = request_func(YTM_DOMAIN)
      File "/usr/lib/python3.10/site-packages/ytmusicapi/ytmusic.py", line 146, in _send_get_request
        response = requests.get(url, params, headers=self.headers, proxies=self.proxies)
      File "/usr/lib/python3.10/site-packages/requests/api.py", line 75, in get
        return request('get', url, params=params, **kwargs)
      (...)
      File "/usr/lib/python3.10/site-packages/requests/adapters.py", line 519, in send
        raise ConnectionError(e, request=request)
    requests.exceptions.ConnectionError: HTTPSConnectionPool(host='music.youtube.com', port=443): Max retries exceeded with url: / (Caused by NewConnectionError('<urllib3.connection.HTTPSConnection object at 0x7f940cece0>: Failed to establish a new connection: [Errno -2] Name or service not known'))

    """
    global _YTMUS
    if _YTMUS:
        return _YTMUS
    for i in range(max_retries):
        try:
            _YTMUS = YTMusic()
            break
        except:  # rate limited
            time.sleep(0.5 * (i + 1))
            continue
    return _YTMUS


class YTMusicResult(YoutubePreview):
    @property
    def title(self):
        return self._raw_data.get("title")

    @property
    def thumbnail_url(self):
        img = self._raw_data.get("image")
        if not img and self._raw_data.get("thumbnails"):
            img = self._raw_data["thumbnails"][-1]["url"]
        return img

    @property
    def artist(self):
        artist = self._raw_data.get("artist")
        if not artist and self._raw_data.get("artists"):
            artist = ", ".join(a["name"] for a in self._raw_data['artists'])
        return artist

    @property
    def description(self):
        return self._raw_data.get("description")

    @property
    def as_dict(self):
        return self._raw_data

    def __dict__(self):
        return self.as_dict

    def __str__(self):
        return json.dumps(self.as_dict, sort_keys=True)


class MusicTrack(YTMusicResult):
    @property
    def watch_url(self):
        return "https://music.youtube.com/watch?v=" + self._raw_data["videoId"]

    @property
    def length(self):
        # converted to seconds or None
        dur = self._raw_data.get("duration")
        if isinstance(dur, str):
            dur = dur.split(":")
            if len(dur) == 2:
                m, s = dur
                return 60 * int(m) + int(s)
            elif len(dur) == 3:
                h, m, s = dur
                return 60 * 60 * int(h) + 60 * int(m) + int(s)
        return None

    @property
    def album(self):
        return self._raw_data.get("album", {}).get("name")

    @property
    def as_dict(self):
        return {"title": self.title,
                "artist": self.artist,
                "image": self.thumbnail_url,
                "url": self.watch_url,
                "duration": self.length}


class MusicVideo(MusicTrack):
    @property
    def watch_url(self):
        return "https://www.youtube.com/watch?v=" + self._raw_data["videoId"]

    def get(self):
        return Video(self.watch_url)


class MusicPlaylist(YTMusicResult):
    @property
    def tracks(self):
        if "tracks" in self._raw_data:
            return [
                MusicTrack(t) for t in self._raw_data["tracks"]
                if t.get("videoId")
            ]
        elif "songs" in self._raw_data:
            return [
                MusicTrack(t) for t in self._raw_data["songs"].get("results", [])
                if t.get("videoId")
            ]
        return []

    @property
    def as_dict(self):
        return {
            "title": self.title,
            "artist": self.artist,
            "image": self.thumbnail_url,
            "playlist": [t.as_dict for t in self.tracks]
        }


class MusicAlbum(MusicPlaylist):
    @property
    def name(self):
        return self.title


class MusicArtist(MusicPlaylist):
    @property
    def name(self):
        return self.artist

    @property
    def as_dict(self):
        return {
            "artist": self.name,
            "image": self.thumbnail_url,
            "playlist": [t.as_dict for t in self.tracks]
        }


def search_yt_music(query, as_dict=True, n_retries=3):
    ytmusic = _get_ytmus(n_retries)
    for r in ytmusic.search(query):
        if r["resultType"] == "video":
            if as_dict:
                yield MusicVideo(r).as_dict
            else:
                yield MusicVideo(r)
        elif r["resultType"] == "song":
            if as_dict:
                yield MusicTrack(r).as_dict
            else:
                yield MusicTrack(r)
        elif r["resultType"] == "album":
            try:
                a = ytmusic.get_album(r["browseId"])
            except:
                continue
            r.update(a)
            if as_dict:
                yield MusicAlbum(r).as_dict
            else:
                yield MusicAlbum(r)
        elif r["resultType"] == "playlist":
            try:
                a = ytmusic.get_playlist(r["browseId"])
            except:
                continue
            r.update(a)
            if as_dict:
                yield MusicPlaylist(r).as_dict
            else:
                yield MusicPlaylist(r)
        elif r["resultType"] == "artist":
            try:
                a = ytmusic.get_artist(r["browseId"])
            except:
                continue
            r.update(a)
            if as_dict:
                yield MusicArtist(r).as_dict
            else:
                yield MusicArtist(r)
