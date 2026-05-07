"""Bridge: convert tutubo objects to mediavocab Work / Release / Entity.

All mapping logic is centralised here.  Each tutubo class delegates to a
function in this module via a thin ``to_work()`` / ``to_release()`` /
``to_entity()`` method — no mapping logic leaks into the model files.

mediavocab is a hard runtime dependency of tutubo (declared in pyproject).
"""
from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional, Tuple

from mediavocab import (
    Work, Release, Entity, EntityRef, Credit,
    MediaType, VariantKind, StreamMode, ReleaseStatus,
    EntityKind, RelationRole, CreditSection,
)
from mediavocab.models.work import AccessibilityTrack, Appearance
from mediavocab.taxonomy.genre import (
    GENRE_SHORT_FILM, GENRE_NEWS, GENRE_TRAILER, GENRE_DOCUMENTARY,
    GENRE_ANIME, GENRE_STAND_UP, GENRE_EDUCATIONAL, GENRE_SPORTS,
    GENRE_CONCERT, GENRE_BEHIND_SCENES,
)

if TYPE_CHECKING:
    from mediavocab.taxonomy import ContentType  # noqa
    from mediavocab.text import TitleParseResult
    from tutubo.channel import Video, Channel, PodcastPreview
    from tutubo.models import VideoPreview, ChannelPreview, PlaylistPreview
    from tutubo.ytmus import MusicTrack, MusicAlbum, MusicPlaylist, MusicArtist


# ---------------------------------------------------------------------------
# ContentType → (MediaType, content_genres, StreamMode)
# ---------------------------------------------------------------------------

def _content_type_to_media_type(
    ct: "ContentType", is_live: bool = False
) -> Tuple["MediaType", List[str], "StreamMode"]:
    """Map a tutubo ContentType to (MediaType, content_genres, StreamMode)."""
    from mediavocab.taxonomy import ContentType as CT

    _MAP = {
        CT.VIDEO:            (MediaType.GENERIC,     [],                              StreamMode.ON_DEMAND),
        CT.SOCIAL_CLIP:      (MediaType.GENERIC,     ["social-clip"],                StreamMode.ON_DEMAND),
        CT.SHORT_FILM:       (MediaType.MOVIE,       [GENRE_SHORT_FILM],             StreamMode.ON_DEMAND),
        CT.LIVE:             (MediaType.GENERIC,     [],                              StreamMode.LIVE),
        CT.UPCOMING:         (MediaType.GENERIC,     [],                              StreamMode.ON_DEMAND),
        CT.LIVE_RADIO:       (MediaType.RADIO,       [],                              StreamMode.CONTINUOUS),
        CT.LIVE_NEWS:        (MediaType.GENERIC,     [GENRE_NEWS],                   StreamMode.LIVE),
        CT.IPTV:             (MediaType.TV,          [],                              StreamMode.CONTINUOUS),
        CT.MOVIE:            (MediaType.MOVIE,       [],                              StreamMode.ON_DEMAND),
        # Trailers and BTS are supplementary material, not primary works (spec §4.1 exclusion table).
        # GENERIC avoids false MOVIE matches in external databases (IMDB, TMDB).
        CT.TRAILER:          (MediaType.GENERIC,     [GENRE_TRAILER],                StreamMode.ON_DEMAND),
        CT.BEHIND_THE_SCENES:(MediaType.GENERIC,     [GENRE_BEHIND_SCENES],          StreamMode.ON_DEMAND),
        CT.DOCUMENTARY:      (MediaType.MOVIE,       [GENRE_DOCUMENTARY],            StreamMode.ON_DEMAND),
        CT.ANIME:            (MediaType.EPISODIC_SERIES, [GENRE_ANIME],               StreamMode.ON_DEMAND),
        CT.TV_EPISODE:       (MediaType.EPISODIC_SERIES, [],                           StreamMode.ON_DEMAND),
        CT.AUDIOBOOK:        (MediaType.AUDIOBOOK,   [],                              StreamMode.ON_DEMAND),
        CT.PODCAST:          (MediaType.PODCAST,     [],                              StreamMode.ON_DEMAND),
        # Stand-up on YouTube is a recording, not a live venue production.
        # Spec §4.1: STAGE is for live-in-venue; "recorded release … is MOVIE/AUDIO_DRAMA".
        CT.STAND_UP:         (MediaType.MOVIE,       [GENRE_STAND_UP],               StreamMode.ON_DEMAND),
        CT.INTERVIEW:        (MediaType.PODCAST,     ["interview"],                   StreamMode.ON_DEMAND),
        CT.LECTURE:          (MediaType.PODCAST,     [GENRE_EDUCATIONAL],            StreamMode.ON_DEMAND),
        CT.CONCERT:          (MediaType.MUSIC_VIDEO, [GENRE_CONCERT],                StreamMode.ON_DEMAND),
        CT.NEWS:             (MediaType.GENERIC,     [GENRE_NEWS],                   StreamMode.ON_DEMAND),
        CT.SPORT:            (MediaType.GENERIC,     [GENRE_SPORTS],                 StreamMode.ON_DEMAND),
        CT.GAMING:           (MediaType.GENERIC,     ["gaming"],                      StreamMode.ON_DEMAND),
        CT.TUTORIAL:         (MediaType.GENERIC,     [GENRE_EDUCATIONAL],            StreamMode.ON_DEMAND),
        CT.REACTION:         (MediaType.GENERIC,     ["reaction"],                    StreamMode.ON_DEMAND),
        CT.COMPILATION:      (MediaType.GENERIC,     ["compilation"],                 StreamMode.ON_DEMAND),
        CT.KIDS:             (MediaType.GENERIC,     ["kids"],                        StreamMode.ON_DEMAND),
        CT.MUSIC_VIDEO:      (MediaType.MUSIC_VIDEO, [],                              StreamMode.ON_DEMAND),
        CT.MUSIC_AUDIO:      (MediaType.MUSIC,       [],                              StreamMode.ON_DEMAND),
    }
    media_type, genres, stream_mode = _MAP.get(ct, (MediaType.GENERIC, [], StreamMode.ON_DEMAND))
    if is_live and stream_mode == StreamMode.ON_DEMAND:
        stream_mode = StreamMode.LIVE
    return media_type, genres, stream_mode


# ---------------------------------------------------------------------------
# Shared credit builder
# ---------------------------------------------------------------------------

def _channel_credit(name: str, channel_id: str = "") -> "Credit":
    ext = {"youtube_channel": channel_id} if channel_id else {}
    return Credit(
        entity=EntityRef(name=name, kind=EntityKind.GROUP, external_ids=ext),
        role="channel",
        relation_role=RelationRole.CREATOR,
        section=CreditSection.PRINCIPAL,
    )


# ---------------------------------------------------------------------------
# Video / VideoPreview → Work + Release
# ---------------------------------------------------------------------------

def video_to_work(
    title: Optional[str],
    video_id: str,
    content_type: "ContentType",
    length: int,
    is_live: bool,
    is_upcoming: bool,
    author: str,
    channel_id: str,
    tags: List[str],
) -> "Work":
    from mediavocab.text import parse_title

    parsed = parse_title(title or "")
    media_type, ct_genres, _ = _content_type_to_media_type(content_type, is_live)

    # Deduplicate genres while preserving order
    seen: set = set()
    all_genres: List[str] = []
    for g in ct_genres + tags:
        if g not in seen:
            seen.add(g)
            all_genres.append(g)

    return Work(
        title=parsed.title or title or "",
        media_type=media_type,
        year=parsed.year,
        runtime=float(length) if length else None,
        season=parsed.season,
        episode=parsed.episode,
        variant_kind=parsed.variant_kind,
        edition=parsed.edition or "",
        content_genres=all_genres,
        release_status=ReleaseStatus.ANNOUNCED if is_upcoming else ReleaseStatus.RELEASED,
        aka=parsed.aka,
        external_ids={"youtube": video_id},
        credits=[_channel_credit(author, channel_id)] if author else [],
        extra={"language_hint": parsed.language_hint} if parsed.language_hint else {},
    )


def video_to_release(
    work: "Work",
    video_id: str,
    watch_url: str,
    thumbnail_url: str,
    is_live: bool,
    is_upcoming: bool,
    has_captions: bool,
    regions_available: Optional[List[str]],
    container: str = "",
) -> "Release":
    from mediavocab.taxonomy import ContentType as CT

    # Live linear / IPTV broadcast (RADIO and TV) is continuous by definition
    if work.media_type in (MediaType.RADIO, MediaType.TV):
        stream_mode = StreamMode.CONTINUOUS
    elif is_live:
        stream_mode = StreamMode.LIVE
    else:
        stream_mode = StreamMode.ON_DEMAND

    accessibility = []
    if has_captions:
        accessibility.append(AccessibilityTrack(kind="captions", language=""))

    return Release(
        work=work,
        uri=watch_url,
        image=thumbnail_url,
        container=container,
        platform="youtube",
        stream_mode=stream_mode,
        release_status=ReleaseStatus.ANNOUNCED if is_upcoming else ReleaseStatus.RELEASED,
        accessibility=accessibility,
        regions_available=regions_available or [],
        external_ids={"youtube": video_id},
    )


# ---------------------------------------------------------------------------
# MusicTrack → Work + Release
# ---------------------------------------------------------------------------

def music_track_to_work(track: "MusicTrack") -> "Work":
    media_type = MediaType.MUSIC_VIDEO if track.is_music_video else MediaType.MUSIC
    genres = ["explicit"] if track.is_explicit else []
    credits = []
    if track.artist:
        ext = {"youtube_channel": track.artist_browse_id} if track.artist_browse_id else {}
        credits.append(Credit(
            entity=EntityRef(name=track.artist, kind=EntityKind.GROUP, external_ids=ext),
            role="performer",
            relation_role=RelationRole.PERFORMER,
            section=CreditSection.PRINCIPAL,
        ))
    ext_ids = {}
    if track.video_id:
        ext_ids["youtube"] = track.video_id
    if track.album_browse_id:
        ext_ids["youtube_album_browse"] = track.album_browse_id

    return Work(
        title=track.title or "",
        media_type=media_type,
        year=track.year,
        runtime=float(track.length) if track.length else None,
        content_genres=genres,
        release_status=ReleaseStatus.RELEASED,
        credits=credits,
        external_ids=ext_ids,
        extra={k: v for k, v in {
            "track_number": track.track_number,
            "album": track.album,
            "youtube_video_type": track.video_type,
        }.items() if v is not None},
    )


def music_track_to_release(track: "MusicTrack", work: "Work") -> "Release":
    return Release(
        work=work,
        uri=track.watch_url,
        image=track.thumbnail_url or "",
        platform="youtube_music",
        stream_mode=StreamMode.ON_DEMAND,
        external_ids={"youtube": track.video_id} if track.video_id else {},
    )


def music_video_to_release(track: "MusicTrack", work: "Work") -> "Release":
    """Like music_track_to_release but uses youtube.com URIs (for MusicVideo)."""
    return Release(
        work=work,
        uri=f"https://www.youtube.com/watch?v={track.video_id}" if track.video_id else "",
        image=track.thumbnail_url or "",
        platform="youtube",
        stream_mode=StreamMode.ON_DEMAND,
        external_ids={"youtube": track.video_id} if track.video_id else {},
    )


# ---------------------------------------------------------------------------
# MusicPlaylist / MusicAlbum → Work + Release
# ---------------------------------------------------------------------------

def music_playlist_to_work(pl: "MusicPlaylist") -> "Work":
    credits = []
    if pl.artist:
        ext = {"youtube_channel": pl.artist_browse_id} if pl.artist_browse_id else {}
        credits.append(Credit(
            entity=EntityRef(name=pl.artist, kind=EntityKind.GROUP, external_ids=ext),
            role="performer",
            relation_role=RelationRole.PERFORMER,
            section=CreditSection.PRINCIPAL,
        ))
    ext_ids = {}
    if pl.browse_id:
        ext_ids["youtube_browse"] = pl.browse_id
    if pl.playlist_id:
        ext_ids["youtube_playlist"] = pl.playlist_id

    tracklist = []
    for i, track in enumerate(pl.tracks, start=1):
        try:
            tw = music_track_to_work(track)
            tracklist.append(Appearance(work=tw, position=track.track_number or i))
        except Exception:
            pass

    return Work(
        title=pl.title or "",
        media_type=MediaType.MUSIC,
        year=pl.year,
        runtime=float(pl.duration_seconds) if pl.duration_seconds else None,
        content_genres=["explicit"] if pl.is_explicit else [],
        release_status=ReleaseStatus.RELEASED,
        credits=credits,
        external_ids=ext_ids,
        tracklist=tracklist,
    )


def music_playlist_to_release(pl: "MusicPlaylist", work: "Work") -> "Release":
    return Release(
        work=work,
        uri=pl.playlist_url,
        image=pl.thumbnail_url or "",
        platform="youtube_music",
        stream_mode=StreamMode.ON_DEMAND,
        external_ids={k: v for k, v in {
            "youtube_browse": pl.browse_id,
            "youtube_playlist": pl.playlist_id,
        }.items() if v},
    )


def music_album_to_release(album: "MusicAlbum", work: "Work") -> "Release":
    label_ref = None
    if album.label:
        label_ref = EntityRef(name=album.label, kind=EntityKind.ORGANISATION)
    return Release(
        work=work,
        uri=album.playlist_url,
        image=album.thumbnail_url or "",
        platform="youtube_music",
        stream_mode=StreamMode.ON_DEMAND,
        label=label_ref,
        external_ids={k: v for k, v in {
            "youtube_browse": album.browse_id,
            "youtube_playlist": album.playlist_id,
        }.items() if v},
    )


# ---------------------------------------------------------------------------
# Channel / ChannelPreview → Entity
# ---------------------------------------------------------------------------

def channel_to_entity(channel: "Channel") -> "Entity":
    aliases = [channel.vanity_url] if channel.vanity_url else []
    ext = {}
    if channel.channel_id:
        ext["youtube_channel"] = channel.channel_id
    if channel.rss_url:
        ext["youtube_rss"] = channel.rss_url
    return Entity(
        name=channel.channel_name,
        kind=EntityKind.GROUP,
        aliases=aliases,
        external_ids=ext,
        extra={k: v for k, v in {
            "subscribers": channel.subscribers,
            "keywords": channel.keywords,
            "available_countries": channel.available_countries,
        }.items() if v},
    )


def channel_preview_to_entity(preview: "ChannelPreview") -> "Entity":
    ext = {}
    if preview.channel_id:
        ext["youtube_channel"] = preview.channel_id
    return Entity(
        name=preview.title,
        kind=EntityKind.GROUP,
        external_ids=ext,
        extra={"verified": preview.is_verified},
    )


# ---------------------------------------------------------------------------
# MusicArtist → Entity
# ---------------------------------------------------------------------------

def music_artist_to_entity(artist: "MusicArtist") -> "Entity":
    ext = {}
    if artist.browse_id:
        ext["youtube_channel"] = artist.browse_id
    return Entity(
        name=artist.name,
        kind=EntityKind.GROUP,
        external_ids=ext,
        extra={k: v for k, v in {
            "subscribers": artist.subscribers,
        }.items() if v},
    )


# ---------------------------------------------------------------------------
# PodcastPreview → Work + Release
# ---------------------------------------------------------------------------

def podcast_preview_to_work(pod: "PodcastPreview") -> "Work":
    return Work(
        title=pod.title,
        media_type=MediaType.PODCAST,
        release_status=ReleaseStatus.RELEASED,
        external_ids={"youtube_playlist": pod.playlist_id} if pod.playlist_id else {},
        extra={k: v for k, v in {
            "episode_count": pod.episode_count,
            "last_updated": pod.last_updated,
        }.items() if v},
    )


def podcast_preview_to_release(pod: "PodcastPreview", work: "Work") -> "Release":
    return Release(
        work=work,
        uri=pod.playlist_url,
        image=pod.thumbnail_url or "",
        platform="youtube",
        stream_mode=StreamMode.ON_DEMAND,
        external_ids={"youtube_playlist": pod.playlist_id} if pod.playlist_id else {},
    )
