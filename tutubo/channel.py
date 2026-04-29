"""Standalone YouTube Channel class — no pytube dependency."""
import json
import logging
from typing import Iterable, List, Optional, Tuple
from urllib.parse import urlencode

import requests

from tutubo._utils import channel_name, initial_data, get_ytcfg, DeferredGeneratorList

logger = logging.getLogger(__name__)

_BROWSE_URL = "https://www.youtube.com/youtubei/v1/browse"
_BROWSE_CONTEXT = {
    "client": {"clientName": "WEB", "clientVersion": "2.20200720.00.02"}
}
# Standard headers and consent cookie for all YouTube page requests.
# SOCS is a proto-encoded persistent consent acceptance token required in EU/similar regions.
_YT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
}
_YT_COOKIES = {
    "CONSENT": "YES+cb",
    "SOCS": "CAESEwgDEgk0ODE3Nzk3MjQaAmVuIAEaBgiA_LyaBg",
}


class Video:
    """Lightweight YouTube video object populated from channel-page data."""

    def __init__(self, video_id: str, title: str = None,
                 thumbnail_url: str = None, is_live: bool = False,
                 keywords: list = None, view_count: str = "",
                 published_time: str = "", channel_tags: list = None,
                 description: str = ""):
        self.video_id = video_id
        self.watch_url = f"https://www.youtube.com/watch?v={video_id}"
        self._title = title
        self._thumbnail_url = thumbnail_url
        self._is_live = is_live
        self.keywords = keywords or []
        self.view_count = view_count        # e.g. "31K views"
        self.published_time = published_time  # e.g. "5 hours ago"
        self.channel_tags = channel_tags or []
        self.description = description

    @property
    def title(self) -> Optional[str]:
        return self._title

    @property
    def thumbnail_url(self) -> str:
        if self._thumbnail_url:
            return self._thumbnail_url
        return f"https://img.youtube.com/vi/{self.video_id}/maxresdefault.jpg"

    @property
    def is_live(self) -> bool:
        return self._is_live

    @property
    def content_type(self):
        from tutubo.content_type import classify_video
        return classify_video(
            title=self._title or "",
            description=self.description,
            is_live=self._is_live,
            channel_tags=self.channel_tags,
        )

    @property
    def tags(self) -> list:
        """Freeform labels from title and description (genre, era, format sub-type, etc.)."""
        from tutubo.content_type import extract_tags
        return extract_tags(self._title or "", self.description)

    @property
    def as_dict(self) -> dict:
        return {
            "videoId": self.video_id,
            "url": self.watch_url,
            "title": self.title,
            "image": self.thumbnail_url,
            "is_live": self.is_live,
            "views": self.view_count,
            "published": self.published_time,
            "description": self.description,
            "content_type": self.content_type,
            "tags": self.tags,
        }

    def __repr__(self):
        return f"<Video {self.video_id!r} title={self.title!r}>"


class Playlist:
    """A YouTube playlist — fetches video URLs from the playlist page."""

    def __init__(self, url: str):
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(url)
        ids = parse_qs(parsed.query).get("list", [])
        if not ids:
            raise ValueError(f"No playlist ID found in URL: {url}")
        self._playlist_id = ids[0]
        self._html: Optional[str] = None
        self._initial_data: Optional[dict] = None
        self._ytcfg: Optional[dict] = None
        self._title: Optional[str] = None

    @property
    def playlist_id(self) -> str:
        return self._playlist_id

    @property
    def playlist_url(self) -> str:
        return f"https://www.youtube.com/playlist?list={self._playlist_id}"

    @property
    def html(self) -> str:
        if not self._html:
            resp = requests.get(
                self.playlist_url,
                headers={**_YT_HEADERS, "Accept-Language": "en-US,en;q=0.9"},
                cookies=_YT_COOKIES,
                timeout=30,
            )
            resp.raise_for_status()
            self._html = resp.text
        return self._html

    @property
    def data(self) -> dict:
        if not self._initial_data:
            self._initial_data = initial_data(self.html)
        return self._initial_data

    @property
    def yt_api_key(self) -> str:
        if not self._ytcfg:
            self._ytcfg = get_ytcfg(self.html)
        return self._ytcfg.get("INNERTUBE_API_KEY", "AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8")

    @property
    def title(self) -> Optional[str]:
        if not self._title:
            try:
                self._title = self.data["metadata"]["playlistMetadataRenderer"]["title"]
            except (KeyError, TypeError):
                pass
        return self._title

    @staticmethod
    def _extract_video_ids(raw: str) -> Tuple[List[str], Optional[str]]:
        data = json.loads(raw) if isinstance(raw, str) else raw
        try:
            section = data["contents"]["twoColumnBrowseResultsRenderer"]["tabs"][0][
                "tabRenderer"]["content"]["sectionListRenderer"]["contents"]
            try:
                items = section[0]["itemSectionRenderer"]["contents"][0][
                    "playlistVideoListRenderer"]["contents"]
            except (KeyError, IndexError):
                items = section[1]["itemSectionRenderer"]["contents"][0][
                    "playlistVideoListRenderer"]["contents"]
        except (KeyError, IndexError, TypeError):
            try:
                items = data["onResponseReceivedActions"][0][
                    "appendContinuationItemsAction"]["continuationItems"]
            except (KeyError, IndexError, TypeError):
                return [], None

        continuation = None
        try:
            token = items[-1]["continuationItemRenderer"][
                "continuationEndpoint"]["continuationCommand"]["token"]
            continuation = token
            items = items[:-1]
        except (KeyError, IndexError):
            pass

        ids = []
        seen = set()
        for item in items:
            vid_id = item.get("playlistVideoRenderer", {}).get("videoId")
            if vid_id and vid_id not in seen:
                ids.append(vid_id)
                seen.add(vid_id)
        return ids, continuation

    def _continuation_post(self, token: str) -> str:
        url = f"{_BROWSE_URL}?key={self.yt_api_key}"
        resp = requests.post(url, json={
            "continuation": token,
            "context": _BROWSE_CONTEXT,
        }, timeout=30)
        resp.raise_for_status()
        return resp.text

    def _video_id_generator(self):
        ids, continuation = self._extract_video_ids(json.dumps(self.data))
        yield from ids
        while continuation:
            raw = self._continuation_post(continuation)
            ids, continuation = self._extract_video_ids(raw)
            yield from ids

    @property
    def video_urls(self) -> List[str]:
        return [f"https://www.youtube.com/watch?v={vid}" for vid in self._video_id_generator()]

    @property
    def videos(self) -> Iterable[Video]:
        for vid_id in self._video_id_generator():
            yield Video(vid_id)

    def __repr__(self):
        return f"<Playlist {self._playlist_id!r} title={self.title!r}>"


class PodcastPreview:
    """A podcast show card from a channel's Podcasts tab."""

    def __init__(self, title: str, playlist_id: str, episode_count: str = "",
                 last_updated: str = "", thumbnail_url: str = ""):
        self.title = title
        self.playlist_id = playlist_id
        self.episode_count = episode_count
        self.last_updated = last_updated
        self.thumbnail_url = thumbnail_url

    @property
    def playlist_url(self) -> str:
        return f"https://www.youtube.com/playlist?list={self.playlist_id}"

    def get(self) -> "Playlist":
        return Playlist(self.playlist_url)

    @property
    def as_dict(self) -> dict:
        return {
            "title": self.title,
            "playlistId": self.playlist_id,
            "url": self.playlist_url,
            "episodeCount": self.episode_count,
            "lastUpdated": self.last_updated,
            "image": self.thumbnail_url,
        }

    def __repr__(self):
        return f"<PodcastPreview {self.title!r} episodes={self.episode_count!r}>"


class Channel:
    """YouTube Channel — fetches metadata, videos, shorts, live streams, and playlists."""

    def __init__(self, url: str, language: str = "en-US,en;q=0.9"):
        self._channel_uri = channel_name(url)
        self.language = language
        self.channel_url = f"https://www.youtube.com{self._channel_uri}"
        self.videos_url = self.channel_url + "/videos"
        self.shorts_url = self.channel_url + "/shorts"
        self.streams_url = self.channel_url + "/streams"
        self.playlists_url = self.channel_url + "/playlists"
        self.podcasts_url = self.channel_url + "/podcasts"

        self._html_cache: dict = {}
        self._initial_data_cache: dict = {}
        self._ytcfg: Optional[dict] = None
        self._visitor_data: Optional[str] = None

    def _get_html(self, url: str) -> str:
        if url not in self._html_cache:
            resp = requests.get(
                url,
                headers={**_YT_HEADERS, "Accept-Language": self.language},
                cookies=_YT_COOKIES,
                timeout=30,
            )
            resp.raise_for_status()
            self._html_cache[url] = resp.text
        return self._html_cache[url]

    def _get_data(self, url: str) -> dict:
        if url not in self._initial_data_cache:
            self._initial_data_cache[url] = initial_data(self._get_html(url))
        return self._initial_data_cache[url]

    @property
    def _metadata_renderer(self) -> dict:
        return self._get_data(self.channel_url).get(
            "metadata", {}
        ).get("channelMetadataRenderer", {})

    @property
    def _page_header(self) -> dict:
        data = self._get_data(self.channel_url)
        return (data.get("header", {})
                    .get("pageHeaderRenderer", {})
                    .get("content", {})
                    .get("pageHeaderViewModel", {}))

    def _header_metadata_texts(self) -> list:
        rows = (self._page_header
                    .get("metadata", {})
                    .get("contentMetadataViewModel", {})
                    .get("metadataRows", []))
        texts = []
        for row in rows:
            for part in row.get("metadataParts", []):
                t = part.get("text", {}).get("content", "")
                if t:
                    texts.append(t)
        return texts

    @property
    def channel_name(self) -> str:
        return self._metadata_renderer.get("title", "")

    @property
    def channel_id(self) -> str:
        return self._metadata_renderer.get("externalId", "")

    @property
    def vanity_url(self) -> Optional[str]:
        return self._metadata_renderer.get("vanityChannelUrl")

    @property
    def description(self) -> str:
        hdr_desc = (self._page_header
                        .get("description", {})
                        .get("descriptionPreviewViewModel", {})
                        .get("description", {})
                        .get("content", ""))
        return hdr_desc or self._metadata_renderer.get("description", "")

    @property
    def subscribers(self) -> str:
        """Subscriber count label, e.g. '12.3M subscribers'."""
        for t in self._header_metadata_texts():
            if "subscriber" in t.lower():
                return t
        return ""

    @property
    def video_count_label(self) -> str:
        """Video count label, e.g. '2.3K videos'."""
        for t in self._header_metadata_texts():
            if "video" in t.lower():
                return t
        return ""

    @property
    def thumbnail_url(self) -> str:
        thumbs = self._metadata_renderer.get("avatar", {}).get("thumbnails", [])
        return thumbs[0]["url"] if thumbs else ""

    @property
    def keywords(self) -> list:
        """Channel tags / keywords as a list of strings."""
        raw = self._metadata_renderer.get("keywords", "")
        if isinstance(raw, list):
            return raw
        # older response format: space-separated, quoted phrases
        import shlex
        try:
            return shlex.split(raw) if raw else []
        except Exception:
            return raw.split() if raw else []

    @property
    def available_countries(self) -> list:
        """ISO country codes where this channel is available."""
        return self._metadata_renderer.get("availableCountryCodes", [])

    @property
    def rss_url(self) -> str:
        """RSS feed URL for this channel's uploads."""
        return self._metadata_renderer.get("rssUrl", "")

    @property
    def title(self) -> str:
        return self.channel_name

    @property
    def yt_api_key(self) -> str:
        if not self._ytcfg:
            self._ytcfg = get_ytcfg(self._get_html(self.channel_url))
        return self._ytcfg.get("INNERTUBE_API_KEY", "AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8")

    def _continuation_post(self, token: str) -> str:
        url = f"{_BROWSE_URL}?key={self.yt_api_key}"
        resp = requests.post(url, json={
            "continuation": token,
            "context": _BROWSE_CONTEXT,
            **({"visitorData": self._visitor_data} if self._visitor_data else {}),
        }, timeout=30)
        return resp.text

    # ------------------------------------------------------------------
    # Video item parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _video_id_from_item(item: dict) -> Optional[str]:
        content = item.get("richItemRenderer", {}).get("content", {})
        if "videoRenderer" in content:
            return content["videoRenderer"].get("videoId")
        if "reelItemRenderer" in content:
            return content["reelItemRenderer"].get("videoId")
        if "lockupViewModel" in content:
            return content["lockupViewModel"].get("contentId")
        return None

    @staticmethod
    def _title_from_item(item: dict) -> Optional[str]:
        content = item.get("richItemRenderer", {}).get("content", {})
        runs = content.get("videoRenderer", {}).get("title", {}).get("runs", [])
        if runs:
            return runs[0].get("text")
        lvm = content.get("lockupViewModel", {})
        return (lvm.get("metadata", {})
                   .get("lockupMetadataViewModel", {})
                   .get("title", {})
                   .get("content"))

    @staticmethod
    def _description_from_item(item: dict) -> str:
        """Return description snippet text from a videoRenderer item, or empty string."""
        content = item.get("richItemRenderer", {}).get("content", {})
        runs = (content.get("videoRenderer", {})
                       .get("descriptionSnippet", {})
                       .get("runs", []))
        return " ".join(r.get("text", "") for r in runs).strip()

    @staticmethod
    def _is_live_from_item(item: dict) -> bool:
        content = item.get("richItemRenderer", {}).get("content", {})
        for badge in content.get("videoRenderer", {}).get("badges", []):
            if "LIVE" in badge.get("metadataBadgeRenderer", {}).get("style", ""):
                return True
        for overlay in (content.get("lockupViewModel", {})
                                .get("contentImage", {})
                                .get("thumbnailViewModel", {})
                                .get("overlays", [])):
            for badge in overlay.get("thumbnailBottomOverlayViewModel", {}).get("badges", []):
                if "LIVE" in badge.get("thumbnailBadgeViewModel", {}).get("badgeStyle", ""):
                    return True
        return False

    @staticmethod
    def _metadata_rows_from_item(item: dict) -> list:
        """Return flat list of metadata text strings from lockupViewModel or videoRenderer."""
        content = item.get("richItemRenderer", {}).get("content", {})
        # lockupViewModel: rows → parts → text.content
        lvm = content.get("lockupViewModel", {})
        if lvm:
            rows = (lvm.get("metadata", {})
                       .get("lockupMetadataViewModel", {})
                       .get("metadata", {})
                       .get("contentMetadataViewModel", {})
                       .get("metadataRows", []))
            texts = []
            for row in rows:
                for part in row.get("metadataParts", []):
                    t = part.get("text", {}).get("content", "")
                    if t:
                        texts.append(t)
            return texts
        # videoRenderer: publishedTimeText + shortViewCountText
        vr = content.get("videoRenderer", {})
        texts = []
        svc = vr.get("shortViewCountText", {}).get("simpleText", "")
        if svc:
            texts.append(svc)
        pt = vr.get("publishedTimeText", {}).get("simpleText", "")
        if pt:
            texts.append(pt)
        return texts

    def _extract_items(self, raw_json: str, tab_suffix: str, channel_tags: list = None) -> Tuple[List[Video], Optional[str]]:
        data = json.loads(raw_json) if isinstance(raw_json, str) else raw_json

        # Initial page: find the active tab
        items = None
        try:
            for tab in data["contents"]["twoColumnBrowseResultsRenderer"]["tabs"]:
                tr = tab.get("tabRenderer", {})
                url = (tr.get("endpoint", {})
                         .get("commandMetadata", {})
                         .get("webCommandMetadata", {})
                         .get("url", ""))
                if url.split("?")[0].rsplit("/", 1)[-1] == tab_suffix:
                    items = tr["content"]["richGridRenderer"]["contents"]
                    try:
                        self._visitor_data = (
                            data["responseContext"]
                            ["webResponseContextExtensionData"]
                            ["ytConfigData"]["visitorData"]
                        )
                    except (KeyError, TypeError):
                        pass
                    break
        except (KeyError, TypeError):
            pass

        # Continuation response
        if items is None:
            try:
                items = data["onResponseReceivedActions"][0][
                    "appendContinuationItemsAction"]["continuationItems"]
            except (KeyError, IndexError, TypeError):
                return [], None

        if not items:
            return [], None

        continuation = None
        try:
            token = items[-1]["continuationItemRenderer"][
                "continuationEndpoint"]["continuationCommand"]["token"]
            continuation = token
            items = items[:-1]
        except (KeyError, IndexError):
            pass

        videos = []
        seen = set()
        for item in items:
            vid_id = self._video_id_from_item(item)
            if not vid_id or vid_id in seen:
                continue
            seen.add(vid_id)
            meta = self._metadata_rows_from_item(item)
            # heuristic: "X views" comes before the date string
            view_count = next((t for t in meta if "view" in t.lower()), "")
            published_time = next((t for t in meta if "view" not in t.lower()), "")
            videos.append(Video(
                video_id=vid_id,
                title=self._title_from_item(item),
                is_live=self._is_live_from_item(item),
                view_count=view_count,
                published_time=published_time,
                channel_tags=channel_tags or [],
                description=self._description_from_item(item),
            ))
        return videos, continuation

    def _video_generator(self, page_url: str) -> Iterable[Video]:
        tab_suffix = page_url.rsplit("/", 1)[-1]
        data = self._get_data(page_url)
        tags = self.keywords
        videos, continuation = self._extract_items(data, tab_suffix, channel_tags=tags)
        yield from videos
        while continuation:
            raw = self._continuation_post(continuation)
            videos, continuation = self._extract_items(raw, tab_suffix, channel_tags=tags)
            yield from videos

    # ------------------------------------------------------------------
    # Public video/stream properties
    # ------------------------------------------------------------------

    @property
    def videos(self) -> Iterable[Video]:
        """Yield Video objects for all videos in this channel."""
        return DeferredGeneratorList(self._video_generator(self.videos_url))

    @property
    def shorts(self) -> Iterable[Video]:
        """Yield Video objects for Shorts in this channel."""
        return DeferredGeneratorList(self._video_generator(self.shorts_url))

    @property
    def streams(self) -> Iterable[Video]:
        """Yield Video objects from the channel's /streams tab (past and current livestreams).

        Maps to ``/@handle/streams`` — a paginated browse tab that lists all
        livestream uploads, including recordings of ended streams.
        For the single currently on-air stream use :attr:`live`.
        """
        return DeferredGeneratorList(self._video_generator(self.streams_url))

    @property
    def live(self) -> Optional[Video]:
        """Return the currently on-air live stream, or None if the channel is offline.

        Maps to ``/@handle/live``, which YouTube redirects to the active livestream
        watch page.  If no stream is live YouTube redirects to a regular video or
        the channel home — both cases return ``None``.

        For a paginated list of all livestream uploads use :attr:`streams`.
        """
        url = self.channel_url + "/live"
        try:
            data = self._get_data(url)
        except Exception:
            return None

        ep = (data.get("currentVideoEndpoint", {})
                  .get("watchEndpoint", {}))
        video_id = ep.get("videoId")
        if not video_id:
            return None

        # Confirm this is actually a live stream, not a redirect to a regular video.
        # videoDetails.isLiveContent is set on live and live-replay pages.
        # playerMicroformat.liveBroadcastDetails.isLiveNow is set only while streaming.
        is_live_content = (
            data.get("videoDetails", {}).get("isLiveContent")
            or data.get("microformat", {})
                   .get("playerMicroformatRenderer", {})
                   .get("liveBroadcastDetails", {})
                   .get("isLiveNow")
        )
        if not is_live_content:
            return None

        # Extract title from videoPrimaryInfoRenderer
        title = ""
        try:
            contents = (data["contents"]["twoColumnWatchNextResults"]
                            ["results"]["results"]["contents"])
            for block in contents:
                pvir = block.get("videoPrimaryInfoRenderer", {})
                if pvir:
                    runs = pvir.get("title", {}).get("runs", [])
                    title = "".join(r.get("text", "") for r in runs)
                    break
        except (KeyError, TypeError):
            pass

        channel_tags = self.keywords
        return Video(
            video_id=video_id,
            title=title,
            is_live=True,
            channel_tags=channel_tags,
        )

    # ------------------------------------------------------------------
    # Playlists
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_playlist_ids(data: dict) -> Tuple[List[str], Optional[str]]:
        playlists = []
        try:
            tabs = data["contents"]["twoColumnBrowseResultsRenderer"]["tabs"]
            for tab in tabs:
                content = tab.get("tabRenderer", {}).get("content", {})
                if "sectionListRenderer" not in content:
                    continue
                for c in content["sectionListRenderer"]["contents"][0][
                        "itemSectionRenderer"]["contents"]:
                    if "shelfRenderer" in c:
                        playlists = c["shelfRenderer"]["content"][
                            "horizontalListRenderer"]["items"]
                        break
                    elif "gridRenderer" in c:
                        playlists = c["gridRenderer"]["items"]
                        break
                if playlists:
                    break
        except (KeyError, IndexError, TypeError):
            pass

        continuation = None
        try:
            token = playlists[-1]["continuationItemRenderer"][
                "continuationEndpoint"]["continuationCommand"]["token"]
            continuation = token
            playlists = playlists[:-1]
        except (KeyError, IndexError):
            pass

        ids = []
        for p in playlists:
            if "gridPlaylistRenderer" in p:
                ids.append(p["gridPlaylistRenderer"]["playlistId"])
            elif "lockupViewModel" in p:
                ids.append(p["lockupViewModel"]["contentId"])
        return ids, continuation

    def _playlist_generator(self):
        data = self._get_data(self.playlists_url)
        ids, _ = self._extract_playlist_ids(data)
        for pid in ids:
            yield Playlist(f"https://www.youtube.com/playlist?list={pid}")

    @property
    def playlist_urls(self) -> List[str]:
        data = self._get_data(self.playlists_url)
        ids, _ = self._extract_playlist_ids(data)
        return [f"https://www.youtube.com/playlist?list={pid}" for pid in ids]

    @property
    def playlists(self) -> Iterable[Playlist]:
        """Yield Playlist objects for all playlists in this channel."""
        return DeferredGeneratorList(self._playlist_generator())

    # ------------------------------------------------------------------
    # Podcasts
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_podcast_item(lvm: dict) -> Optional["PodcastPreview"]:
        import re as _re
        meta = lvm.get("metadata", {}).get("lockupMetadataViewModel", {})
        title = meta.get("title", {}).get("content", "")
        rows = (meta.get("metadata", {})
                    .get("contentMetadataViewModel", {})
                    .get("metadataRows", []))
        last_updated = ""
        for row in rows:
            for part in row.get("metadataParts", []):
                t = part.get("text", {}).get("content", "")
                if t and t.lower() != "view full podcast":
                    last_updated = t
        # Episode count is in the thumbnail badge
        episode_count = ""
        primary = (lvm.get("contentImage", {})
                      .get("collectionThumbnailViewModel", {})
                      .get("primaryThumbnail", {})
                      .get("thumbnailViewModel", {}))
        for overlay in primary.get("overlays", []):
            for badge in overlay.get("thumbnailOverlayBadgeViewModel", {}).get("thumbnailBadges", []):
                episode_count = badge.get("thumbnailBadgeViewModel", {}).get("text", "")
        # Thumbnail URL
        sources = primary.get("image", {}).get("sources", [])
        thumbnail_url = sources[0].get("url", "") if sources else ""
        # Playlist ID from onTap command URL
        url_path = (lvm.get("rendererContext", {})
                       .get("commandContext", {})
                       .get("onTap", {})
                       .get("innertubeCommand", {})
                       .get("commandMetadata", {})
                       .get("webCommandMetadata", {})
                       .get("url", ""))
        m = _re.search(r"list=([^&]+)", url_path)
        playlist_id = m.group(1) if m else ""
        if not playlist_id:
            return None
        return PodcastPreview(
            title=title,
            playlist_id=playlist_id,
            episode_count=episode_count,
            last_updated=last_updated,
            thumbnail_url=thumbnail_url,
        )

    def _podcast_generator(self) -> Iterable["PodcastPreview"]:
        data = self._get_data(self.podcasts_url)
        tabs = data.get("contents", {}).get("twoColumnBrowseResultsRenderer", {}).get("tabs", [])
        for tab in tabs:
            tr = tab.get("tabRenderer", {})
            url_path = (tr.get("endpoint", {})
                          .get("commandMetadata", {})
                          .get("webCommandMetadata", {})
                          .get("url", ""))
            if not url_path.endswith("/podcasts"):
                continue
            content = tr.get("content", {})
            items = content.get("richGridRenderer", {}).get("contents", [])
            for item in items:
                lvm = item.get("richItemRenderer", {}).get("content", {}).get("lockupViewModel", {})
                if lvm:
                    pod = self._parse_podcast_item(lvm)
                    if pod:
                        yield pod

    @property
    def podcasts(self) -> Iterable["PodcastPreview"]:
        """Yield PodcastPreview objects for each show on the Podcasts tab."""
        return DeferredGeneratorList(self._podcast_generator())

    @property
    def as_dict(self) -> dict:
        return {
            "channelId": self.channel_id,
            "title": self.title,
            "image": self.thumbnail_url,
            "url": self.channel_url,
            "description": self.description,
            "subscribers": self.subscribers,
            "video_count": self.video_count_label,
            "keywords": self.keywords,
            "rss_url": self.rss_url,
        }

    def __repr__(self):
        return f"<Channel {self._channel_uri!r}>"
