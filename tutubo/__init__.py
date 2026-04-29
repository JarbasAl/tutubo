"""tutubo — a typed, dependency-light YouTube/YouTube Music search & metadata client.

Public API:
    YoutubeSearch, YoutubeMusicSearch, SearchType, search_yt, search_yt_music
    Channel, Playlist, Video, PodcastPreview
    ContentType, classify_video, extract_tags
    download, download_playlist
    MusicTrack, MusicVideo, MusicAlbum, MusicPlaylist, MusicArtist
    set_lang, get_lang
"""
from tutubo.search import YoutubeSearch, YoutubeMusicSearch, SearchType, search_yt, search_yt_music
from tutubo.channel import Channel, Playlist, Video, PodcastPreview
from tutubo.content_type import ContentType, classify_video, extract_tags
from tutubo.download import download, download_playlist
from tutubo.ytmus import MusicTrack, MusicVideo, MusicAlbum, MusicPlaylist, MusicArtist
from tutubo._locale import set_lang, get_lang
