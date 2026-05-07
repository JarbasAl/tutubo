"""tutubo — a typed, dependency-light YouTube/YouTube Music search & metadata client.

Public API:
    YoutubeSearch, YoutubeMusicSearch, SearchType, search_yt, search_yt_music
    Channel, Playlist, Video, PodcastPreview
    ContentType, classify_video, classify_video_dict, extract_tags
    TitleParseResult, parse_title
    download, download_playlist
    MusicTrack, MusicVideo, MusicAlbum, MusicPlaylist, MusicArtist

ContentType, classify_video, parse_title and the locale system live in
``mediavocab``; for non-default languages pass ``lang="xx-yy"`` to the
function call (the locale system is stateless / thread-safe).
"""
from tutubo.search import YoutubeSearch, YoutubeMusicSearch, SearchType, search_yt, search_yt_music
from tutubo.channel import Channel, Playlist, Video, PodcastPreview
from mediavocab.taxonomy import ContentType
from mediavocab.text import (
    classify_video, classify_video_dict, extract_tags,
    parse_title, TitleParseResult,
)
from tutubo.download import download, download_playlist
from tutubo.ytmus import MusicTrack, MusicVideo, MusicAlbum, MusicPlaylist, MusicArtist

__all__ = [
    "YoutubeSearch", "YoutubeMusicSearch", "SearchType",
    "search_yt", "search_yt_music",
    "Channel", "Playlist", "Video", "PodcastPreview",
    "ContentType",
    "classify_video", "classify_video_dict", "extract_tags",
    "parse_title", "TitleParseResult",
    "download", "download_playlist",
    "MusicTrack", "MusicVideo", "MusicAlbum", "MusicPlaylist", "MusicArtist",
]
