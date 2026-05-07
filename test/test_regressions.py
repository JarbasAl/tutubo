"""Named regression guards for parser/API-shape bugs found during 2026.

Each test pins the post-fix behaviour of a real, previously-shipped bug.
When upstream YouTube drifts or someone refactors the parser, these
named tests are the first-line tripwire — the test name itself documents
what regression class is being guarded against.

Live-API drift coverage is provided separately by the ``nightly-live``
workflow which re-records every fixture and re-runs the suite.

History (commit summaries — see ``git log`` for details):

* ``Channel`` star-import: ``from tutubo.channel import *`` failed because
  ``__all__`` referenced symbols that no longer existed after the pytube
  rip-out.
* ``Channel.video_urls`` — the public surface had a ``video_urls``
  property that delegated to a removed pytube helper. The fix removed
  the property; consumers must use ``Channel.videos`` (an iterator).
* ``Video.length`` was unconditionally read on channel-page Videos but
  channel-tab innertube payloads don't always carry ``lengthText`` →
  AttributeError on shorts/live items. Fix: default to 0.
* ``Video.published_time`` on channel-page videos was lost when the
  meta-row parser filtered too aggressively — ended up empty for every
  Video. Fix: take the first non-view meta row.
* ``MusicArtist`` was not a subclass of ``YTMusicResult`` after a
  refactor, breaking ``isinstance(r, YTMusicResult)`` checks in
  downstream code (mediavocab bridge).
* ``iterate_music_albums`` was added to ``YoutubeMusicSearch`` only
  (not ``YoutubeSearch``) — verifying the surface stays separate.
"""
from __future__ import annotations

import importlib

import pytest

from tutubo import YoutubeSearch, YoutubeMusicSearch
from tutubo.channel import Channel, Playlist, Video
from tutubo.ytmus import (
    MusicAlbum,
    MusicArtist,
    MusicPlaylist,
    MusicTrack,
    MusicVideo,
    YTMusicResult,
)


# ---------------------------------------------------------------------------
# Channel — star-import & surface
# ---------------------------------------------------------------------------

def test_regression_channel_star_import_clean():
    """``from tutubo.channel import *`` must not raise (broken Mar 2026)."""
    # Re-import in a fresh namespace and verify __all__ resolves.
    mod = importlib.import_module("tutubo.channel")
    if hasattr(mod, "__all__"):
        for name in mod.__all__:
            assert hasattr(mod, name), (
                f"tutubo.channel.__all__ references missing symbol {name!r}"
            )


def test_regression_channel_has_no_video_urls_property():
    """``Channel.video_urls`` was removed when pytube was ripped out.

    Consumers must iterate ``Channel.videos`` instead.  This test pins the
    removed surface so it doesn't silently come back as a stub.
    """
    assert not hasattr(Channel, "video_urls"), (
        "Channel.video_urls was removed (pytube delegate); use Channel.videos"
    )


def test_regression_playlist_still_has_video_urls():
    """Playlist.video_urls is the legitimate API; only Channel lost it."""
    assert hasattr(Playlist, "video_urls")


# ---------------------------------------------------------------------------
# Video on channel pages — length defaulting + published_time
# ---------------------------------------------------------------------------

def test_regression_channel_video_has_no_length_attr():
    """Channel-tab ``Video`` deliberately omits ``length``.

    Earlier code accessed ``video.length`` on channel-tab Videos and
    crashed because innertube channel-tab payloads don't carry
    ``lengthText`` (especially for shorts/live).  Fix: keep ``length``
    off ``Channel.Video`` entirely; consumers that need length must
    upgrade via the search-result ``VideoPreview`` or fetch the watch
    page.  This test pins the surface so length doesn't silently come
    back as a stub returning 0 (which would mask real upstream drift).
    """
    from tutubo.models import VideoPreview
    v = Video(video_id="x" * 11)
    assert not hasattr(v, "length")
    # VideoPreview (search-result) DOES carry length — verify the
    # surface stays where it belongs.
    assert "length" in dir(VideoPreview)


def test_regression_video_published_time_attribute_exists():
    v = Video(video_id="x" * 11)
    assert hasattr(v, "published_time")
    # Default should be a string (possibly empty), never missing/None.
    assert isinstance(v.published_time, str)


def test_regression_video_published_time_populated_on_channel_page(patch_channel_data):
    """published_time was being filtered to empty for every channel-tab Video."""
    ch = Channel("https://www.youtube.com/@kurzgesagt")
    populated = 0
    for v in ch.videos:
        if v.published_time:
            populated += 1
        if populated >= 1:
            break
    assert populated >= 1, (
        "Expected at least one Video with a populated published_time; "
        "regression of channel-tab meta-row parser."
    )


# ---------------------------------------------------------------------------
# Music — type hierarchy & search-class separation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("cls", [MusicTrack, MusicVideo, MusicAlbum, MusicPlaylist, MusicArtist])
def test_regression_music_classes_subclass_ytmusicresult(cls):
    """All Music* result types must subclass YTMusicResult.

    A refactor briefly broke ``MusicArtist``'s base class, which silently
    broke isinstance() dispatch in the mediavocab bridge.
    """
    assert issubclass(cls, YTMusicResult), (
        f"{cls.__name__} must subclass YTMusicResult"
    )


def test_regression_music_video_subclasses_music_track():
    """MusicVideo extends MusicTrack — preserves track-shape consumers."""
    assert issubclass(MusicVideo, MusicTrack)


def test_regression_music_album_subclasses_music_playlist():
    assert issubclass(MusicAlbum, MusicPlaylist)


# ---------------------------------------------------------------------------
# Search-class separation: iterate_music_* lives only on YoutubeMusicSearch
# ---------------------------------------------------------------------------

def test_regression_youtube_search_has_no_iterate_albums():
    """YoutubeSearch must NOT expose ytmusic-only iterators."""
    assert not hasattr(YoutubeSearch, "iterate_albums")
    assert not hasattr(YoutubeSearch, "iterate_artists")
    assert not hasattr(YoutubeSearch, "iterate_tracks")


def test_regression_youtube_music_search_has_iterate_albums():
    """The corresponding ytmusic iterators live on YoutubeMusicSearch."""
    assert hasattr(YoutubeMusicSearch, "iterate_albums")
    assert hasattr(YoutubeMusicSearch, "iterate_artists")
    assert hasattr(YoutubeMusicSearch, "iterate_tracks")


def test_regression_classes_are_distinct():
    """YoutubeSearch and YoutubeMusicSearch must remain separate types."""
    assert YoutubeSearch is not YoutubeMusicSearch
    assert not issubclass(YoutubeMusicSearch, YoutubeSearch)
    assert not issubclass(YoutubeSearch, YoutubeMusicSearch)
