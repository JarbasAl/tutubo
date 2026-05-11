"""Unit tests for model parsing logic — construct models from synthetic raw dicts.

These tests verify that the model properties correctly parse the renderer
structures returned by the YouTube innertube API.  No network or fixtures needed.
"""
from tutubo.models import VideoPreview, ChannelPreview, PlaylistPreview
from mediavocab.taxonomy import ContentType  # noqa


# ---------------------------------------------------------------------------
# Helpers to build minimal renderer dicts
# ---------------------------------------------------------------------------

def _video_renderer(
    video_id="abc123",
    title="Test Video",
    owner="Channel Name",
    length_text=None,
    published="3 years ago",
    view_count="1,234,567",
    short_views="1.2M views",
    badges=None,
    owner_badges=None,
    overlays=None,
    description_runs=None,
    channel_path="/channel/UCtest",
):
    d = {
        "videoId": video_id,
        "title": {"runs": [{"text": title}]},
        "ownerText": {"runs": [{"text": owner, "navigationEndpoint": {
            "commandMetadata": {"webCommandMetadata": {"url": channel_path}}
        }}]},
        "publishedTimeText": {"simpleText": published},
        "viewCountText": {"simpleText": view_count},
        "shortViewCountText": {"simpleText": short_views},
        "badges": badges or [],
        "ownerBadges": owner_badges or [],
        "thumbnailOverlays": overlays or [],
    }
    if length_text:
        d["lengthText"] = {"simpleText": length_text}
    if description_runs:
        d["detailedMetadataSnippets"] = [{"snippetText": {"runs": description_runs}}]
    return d


# ---------------------------------------------------------------------------
# VideoPreview — basic fields
# ---------------------------------------------------------------------------

def test_video_id():
    v = VideoPreview(_video_renderer(video_id="xyz789"))
    assert v.video_id == "xyz789"


def test_watch_url():
    v = VideoPreview(_video_renderer(video_id="abc"))
    assert v.watch_url == "https://www.youtube.com/watch?v=abc"


def test_title():
    v = VideoPreview(_video_renderer(title="My Great Video"))
    assert v.title == "My Great Video"


def test_author():
    v = VideoPreview(_video_renderer(owner="Rob Zombie"))
    assert v.author == "Rob Zombie"


def test_channel_url():
    v = VideoPreview(_video_renderer(channel_path="/channel/UC1234"))
    assert v.channel_url == "https://www.youtube.com/channel/UC1234"


def test_published_time():
    v = VideoPreview(_video_renderer(published="2 years ago"))
    assert v.published_time == "2 years ago"


def test_view_count_parsed():
    v = VideoPreview(_video_renderer(view_count="1,234,567 views"))
    assert v.view_count == 1_234_567


def test_view_count_non_numeric_returns_zero():
    v = VideoPreview(_video_renderer(view_count="No views yet"))
    assert v.view_count == 0


def test_short_view_count():
    v = VideoPreview(_video_renderer(short_views="272M views"))
    assert v.short_view_count == "272M views"


# ---------------------------------------------------------------------------
# VideoPreview — duration parsing
# ---------------------------------------------------------------------------

def test_length_mm_ss():
    v = VideoPreview(_video_renderer(length_text="3:45"))
    assert v.length == 225


def test_length_hh_mm_ss():
    v = VideoPreview(_video_renderer(length_text="1:02:30"))
    assert v.length == 3750


def test_length_missing_is_zero():
    v = VideoPreview(_video_renderer())
    assert v.length == 0


# ---------------------------------------------------------------------------
# VideoPreview — badges and classification
# ---------------------------------------------------------------------------

def test_cc_badge():
    raw = _video_renderer(badges=[{"metadataBadgeRenderer": {"label": "CC"}}])
    v = VideoPreview(raw)
    assert "CC" in v.badges
    assert v.has_captions is True


def test_4k_badge():
    raw = _video_renderer(badges=[{"metadataBadgeRenderer": {"label": "4K"}}])
    v = VideoPreview(raw)
    assert "4K" in v.badges


def test_live_overlay():
    raw = _video_renderer(
        overlays=[{"thumbnailOverlayTimeStatusRenderer": {"style": "LIVE", "text": {}}}]
    )
    v = VideoPreview(raw)
    assert v.is_live is True


def test_upcoming_overlay():
    raw = _video_renderer(
        overlays=[{"thumbnailOverlayTimeStatusRenderer": {"style": "UPCOMING", "text": {}}}]
    )
    v = VideoPreview(raw)
    assert v.is_upcoming is True


def test_verified_channel():
    raw = _video_renderer(owner_badges=[{"metadataBadgeRenderer": {"style": "BADGE_STYLE_TYPE_VERIFIED"}}])
    v = VideoPreview(raw)
    assert v.is_verified_channel is True


def test_official_artist_channel():
    raw = _video_renderer(owner_badges=[{"metadataBadgeRenderer": {"style": "BADGE_STYLE_TYPE_VERIFIED_ARTIST"}}])
    v = VideoPreview(raw)
    assert v.is_official_artist_channel is True


# ---------------------------------------------------------------------------
# VideoPreview — description snippet
# ---------------------------------------------------------------------------

def test_description_snippet():
    raw = _video_renderer(description_runs=[{"text": "Great video about "}, {"text": "cats"}])
    v = VideoPreview(raw)
    assert v.description_snippet == "Great video about cats"


def test_description_snippet_absent():
    v = VideoPreview(_video_renderer())
    assert v.description_snippet == ""


# ---------------------------------------------------------------------------
# VideoPreview — content_type integration
# ---------------------------------------------------------------------------

def test_content_type_live():
    raw = _video_renderer(
        overlays=[{"thumbnailOverlayTimeStatusRenderer": {"style": "LIVE", "text": {}}}]
    )
    assert VideoPreview(raw).content_type == ContentType.LIVE


def test_content_type_short():
    v = VideoPreview(_video_renderer(length_text="0:45"))
    assert v.content_type == ContentType.SOCIAL_CLIP


def test_content_type_trailer():
    # Provide a non-zero length so is_live (length==0 proxy) doesn't fire first
    v = VideoPreview(_video_renderer(title="The Batman — Official Trailer", length_text="2:30"))
    assert v.content_type == ContentType.TRAILER


def test_content_type_default_video():
    v = VideoPreview(_video_renderer(title="How to Make Pizza", length_text="10:00"))
    assert v.content_type == ContentType.TUTORIAL


def test_content_type_in_as_dict():
    v = VideoPreview(_video_renderer(title="Cooking Show", length_text="20:00"))
    d = v.as_dict
    assert "content_type" in d
    assert d["content_type"] == ContentType.VIDEO


# ---------------------------------------------------------------------------
# ChannelPreview
# ---------------------------------------------------------------------------

def test_channel_preview_title():
    raw = {
        "channelId": "UCtest",
        "title": {"simpleText": "Test Channel"},
        "descriptionSnippet": {"runs": [{"text": "About this channel"}]},
        "videoCountText": {"simpleText": "1.2M subscribers"},
        "thumbnail": {"thumbnails": [{"url": "https://example.com/thumb.jpg"}]},
        "ownerBadges": [],
    }
    ch = ChannelPreview(raw)
    assert ch.title == "Test Channel"
    assert ch.channel_id == "UCtest"
    assert ch.channel_url == "https://www.youtube.com/channel/UCtest"
    assert ch.description == "About this channel"
    assert ch.subscriber_count == "1.2M subscribers"
    assert ch.is_verified is False


def test_channel_preview_verified():
    raw = {
        "channelId": "UC1",
        "title": {"simpleText": "Verified Channel"},
        "descriptionSnippet": {},
        "videoCountText": {},
        "thumbnail": {"thumbnails": [{"url": "https://x.com/t.jpg"}]},
        "ownerBadges": [{"metadataBadgeRenderer": {"style": "BADGE_STYLE_TYPE_VERIFIED"}}],
    }
    assert ChannelPreview(raw).is_verified is True


# ---------------------------------------------------------------------------
# PlaylistPreview
# ---------------------------------------------------------------------------

def test_playlist_preview():
    raw = {
        "playlistId": "PLabc",
        "title": {"simpleText": "My Playlist"},
        "videoCount": 42,
        "videos": [],
        "thumbnails": [{"thumbnails": [{"url": "https://img.yt/pl.jpg"}]}],
    }
    pl = PlaylistPreview(raw)
    assert pl.playlist_id == "PLabc"
    assert pl.playlist_url == "https://www.youtube.com/playlist?list=PLabc"
    assert pl.title == "My Playlist"
    assert pl.video_count == 42
    assert pl.featured_videos == []


# ---------------------------------------------------------------------------
# VideoPreview → mediavocab Release: rich-output regression
# ---------------------------------------------------------------------------

def test_to_release_resolution_from_4k_badge():
    """4K badge ⇒ Release.resolution = '2160p' (no fabricated default otherwise)."""
    from mediavocab import StreamMode
    raw = _video_renderer(
        title="Some Movie",
        length_text="1:42:00",
        badges=[{"metadataBadgeRenderer": {"label": "4K"}}],
    )
    rel = VideoPreview(raw).to_release()
    assert rel.resolution == "2160p"
    assert rel.platform == "youtube"
    assert rel.stream_mode == StreamMode.ON_DEMAND


def test_to_release_resolution_from_8k_badge():
    raw = _video_renderer(badges=[{"metadataBadgeRenderer": {"label": "8K"}}])
    rel = VideoPreview(raw).to_release()
    assert rel.resolution == "4320p"


def test_to_release_resolution_unknown_when_no_badge():
    """No quality badge ⇒ resolution stays empty (do not invent)."""
    rel = VideoPreview(_video_renderer()).to_release()
    assert rel.resolution == ""


def test_to_release_accessibility_from_cc_badge():
    raw = _video_renderer(badges=[{"metadataBadgeRenderer": {"label": "CC"}}])
    rel = VideoPreview(raw).to_release()
    assert any(t.kind == "captions" for t in rel.accessibility)


def test_to_release_no_accessibility_when_no_cc():
    rel = VideoPreview(_video_renderer()).to_release()
    assert rel.accessibility == []


def test_content_type_routing_uses_mediavocab_table():
    """Routing for non-divergent ContentTypes must match mediavocab.to_routing()."""
    from mediavocab.taxonomy import ContentType
    from tutubo.mediavocab_bridge import _content_type_to_media_type
    for ct in [ContentType.MOVIE, ContentType.DOCUMENTARY, ContentType.SHORT_FILM,
               ContentType.PODCAST, ContentType.MUSIC_VIDEO, ContentType.ANIME]:
        media, genres, _ = _content_type_to_media_type(ct, is_live=False)
        ref_media, _ref_form, ref_genres, _ref_pf = ct.to_routing()
        assert media == ref_media
        assert genres == ref_genres


def test_content_type_routing_live_news_divergence():
    """LIVE_NEWS deliberately diverges: mediavocab=TV, tutubo=MOVIE+news.

    mediavocab 1.0 rejects GENERIC at Work construction (T8), so tutubo
    promotes the GENERIC fallback to MOVIE while keeping the ``news`` genre.
    """
    from mediavocab import MediaType, StreamMode
    from mediavocab.taxonomy import ContentType

    from tutubo.mediavocab_bridge import _content_type_to_media_type
    media, genres, sm = _content_type_to_media_type(ContentType.LIVE_NEWS)
    assert media == MediaType.MOVIE
    assert "news" in genres
    assert sm == StreamMode.LIVE
