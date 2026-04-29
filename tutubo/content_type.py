"""Content-type classification for YouTube VideoPreview objects.

Uses duration heuristics, badge analysis, channel tags, and locale-loaded
keyword phrases to classify videos into semantic categories without additional
network fetches.

Classification is English by default.  To classify non-English content, call
``tutubo.set_lang("es-es")`` (or set the ``TUTUBO_LANG`` env var) before
searching.  Locale files live in ``tutubo/locale/<lang>/``.  Adding a new
language requires only creating the corresponding ``.voc`` files — no Python
changes needed.
"""
import enum
import re
from typing import List, Optional

from tutubo import _locale

# ---------------------------------------------------------------------------
# Structural patterns — not translatable; stay in Python
# ---------------------------------------------------------------------------

# TV episode: S01E02 / Season 1 … Episode 2  (number-based, language-neutral)
_TV_EPISODE_STRUCT_RE = re.compile(
    r'\bS\d{1,2}\s*E\d{1,3}\b'
    r'|\bSeason\s+\d{1,2}\b.*?\bEpisode\s+\d{1,3}\b',
    re.IGNORECASE,
)

# Compilation: "Top 10", "Top 5" etc.
_COMPILATION_TOP_N_RE = re.compile(r'\bTop\s+\d+\b', re.IGNORECASE)

# Movie: "Full <adjective> Movie/Film" — one qualifying word between full and movie/film
_MOVIE_FULL_ADJ_RE = re.compile(r'\bfull\s+\w+\s+(?:movie|film)\b', re.IGNORECASE)

# Silent-era: year in 1910s or 1920s
_SILENT_ERA_YEAR_RE = re.compile(r'\b191\d\b|\b192\d\b')

# ---------------------------------------------------------------------------
# Duration hard limits
# ---------------------------------------------------------------------------

_MOVIE_MIN_SECONDS = 60 * 60
_TRAILER_MAX_SECONDS = 600
_SHORT_FILM_MAX_SECONDS = 3600
_MUSIC_VIDEO_MAX_SECONDS = 900

# ---------------------------------------------------------------------------
# Tag manifest  — (output_label, voc_file_stem_inside_tags/)
# ---------------------------------------------------------------------------

_TAG_MANIFEST = [
    # Audio format sub-labels
    ("narrated",    "tags/narrated"),
    ("full-cast",   "tags/full-cast"),
    ("radio-play",  "tags/radio-play"),
    # Music release format
    ("full-album",  "tags/full-album"),
    ("ep",          "tags/ep"),
    ("premiere",    "tags/premiere"),
    ("mix",         "tags/mix"),
    # Genre
    ("horror",      "tags/horror"),
    ("sci-fi",      "tags/sci-fi"),
    ("fantasy",     "tags/fantasy"),
    ("thriller",    "tags/thriller"),
    ("romance",     "tags/romance"),
    ("comedy",      "tags/comedy"),
    ("action",      "tags/action"),
    ("crime",       "tags/crime"),
    ("war",         "tags/war"),
    ("western",     "tags/western"),
    ("animation",   "tags/animation"),
    ("superhero",   "tags/superhero"),
    # Music genre
    ("classical",   "tags/classical"),
    ("jazz",        "tags/jazz"),
    ("metal",       "tags/metal"),
    ("hip-hop",     "tags/hip-hop"),
    ("electronic",  "tags/electronic"),
    ("folk",        "tags/folk"),
    ("reggae",      "tags/reggae"),
    ("punk",        "tags/punk"),
    ("country",     "tags/country"),
    ("r&b",         "tags/r-and-b"),
    # Sports
    ("football",    "tags/football"),
    ("basketball",  "tags/basketball"),
    ("baseball",    "tags/baseball"),
    ("tennis",      "tags/tennis"),
    ("motorsport",  "tags/motorsport"),
    ("combat",      "tags/combat"),
    ("esports",     "tags/esports"),
    # Spoken word format
    ("debate",      "tags/debate"),
    ("ted-talk",    "tags/ted-talk"),
    ("panel",       "tags/panel"),
    # Production / era flags
    ("silent-era",  "tags/silent-era"),
    ("classic",     "tags/classic"),
    ("colorized",   "tags/colorized"),
    ("4k",          "tags/4k"),
    ("short",       "tags/short"),
    # Audience
    ("kids",        "tags/kids"),
    ("educational", "tags/educational"),
    # Niche
    ("lovecraft",   "tags/lovecraft"),
    ("wayne-june",  "tags/wayne-june"),
]


class ContentType(str, enum.Enum):
    """Semantic content type for a YouTube video, derived from metadata + title analysis."""

    VIDEO = "video"
    SOCIAL_CLIP = "social_clip"
    SHORT_FILM = "short_film"
    LIVE = "live"
    UPCOMING = "upcoming"
    LIVE_RADIO = "live_radio"
    LIVE_NEWS = "live_news"
    IPTV = "iptv"
    MOVIE = "movie"
    TRAILER = "trailer"
    BEHIND_THE_SCENES = "behind_the_scenes"
    DOCUMENTARY = "documentary"
    ANIME = "anime"
    TV_EPISODE = "tv_episode"
    AUDIOBOOK = "audiobook"
    PODCAST = "podcast"
    STAND_UP = "stand_up"
    INTERVIEW = "interview"
    LECTURE = "lecture"
    CONCERT = "concert"
    NEWS = "news"
    SPORT = "sport"
    GAMING = "gaming"
    TUTORIAL = "tutorial"
    REACTION = "reaction"
    COMPILATION = "compilation"
    KIDS = "kids"
    MUSIC_VIDEO = "music_video"
    MUSIC_AUDIO = "music_audio"


def classify_video(
    title: str,
    description: str = "",
    length: int = 0,
    is_live: bool = False,
    is_upcoming: bool = False,
    is_official_artist: bool = False,
    is_podcast: bool = False,
    channel_tags: Optional[List[str]] = None,
) -> ContentType:
    """Classify a video into a ContentType.

    Language of keyword matching is controlled by ``tutubo.set_lang()`` (default: en-us).

    ``is_podcast`` must come from publisher-defined data — never inferred from title.

    ``channel_tags`` boost MOVIE, DOCUMENTARY, ANIME, SHORT_FILM, KIDS, NEWS, SPORT,
    GAMING, CONCERT, STAND_UP when the title carries no explicit keyword.

    ``VideoPreview.content_type`` does NOT forward channel_tags (search results don't
    include them). For channel-tag-boosted classification use ``Channel.videos`` and
    pass ``channel_tags=v.channel_tags`` explicitly.
    """
    # --- live sub-classification ----------------------------------------
    if is_live:
        combined_live = f"{title} {description}"
        live_tags = {t.lower() for t in (channel_tags or [])}

        live_radio_re = _locale.voc_regex("live_radio_keywords")
        if live_radio_re and live_radio_re.search(combined_live):
            return ContentType.LIVE_RADIO

        live_news_re = _locale.voc_regex("live_news_keywords")
        channel_news_re = _locale.voc_regex("channel_news_tags")
        tags_str = " ".join(live_tags)
        if (
            (live_news_re and live_news_re.search(combined_live))
            or (channel_news_re and channel_news_re.search(tags_str))
        ):
            return ContentType.LIVE_NEWS

        iptv_re = _locale.voc_regex("iptv_keywords")
        if iptv_re and iptv_re.search(combined_live):
            return ContentType.IPTV

        return ContentType.LIVE

    if is_upcoming:
        return ContentType.UPCOMING

    if 0 < length < 62:
        return ContentType.SOCIAL_CLIP

    tags_lower = {t.lower() for t in (channel_tags or [])}
    combined = f"{title} {description}"

    # TRAILER
    trailer_re = _locale.voc_regex("trailer_keywords")
    if trailer_re and trailer_re.search(title):
        if length == 0 or length <= _TRAILER_MAX_SECONDS:
            return ContentType.TRAILER

    # MOVIE — title/description keyword
    movie_re = _locale.voc_regex("movie_keywords")
    if (movie_re and movie_re.search(combined)) or _MOVIE_FULL_ADJ_RE.search(combined):
        if length == 0 or length >= _MOVIE_MIN_SECONDS:
            return ContentType.MOVIE

    # DOCUMENTARY — title keyword OR doc channel tag
    doc_re = _locale.voc_regex("documentary_keywords")
    channel_doc_tags = _locale.voc_set("channel_doc_tags")
    if (doc_re and doc_re.search(combined)) or (tags_lower & channel_doc_tags):
        return ContentType.DOCUMENTARY

    # BEHIND THE SCENES
    bts_re = _locale.voc_regex("behind_the_scenes_keywords")
    if bts_re and bts_re.search(combined):
        return ContentType.BEHIND_THE_SCENES

    # ANIME — title keyword OR anime channel tag
    anime_re = _locale.voc_regex("anime_keywords")
    channel_anime_tags = _locale.voc_set("channel_anime_tags")
    if (anime_re and anime_re.search(combined)) or (tags_lower & channel_anime_tags):
        return ContentType.ANIME

    # TV EPISODE — structural S01E02 + locale "Full Episode" etc.
    tv_ep_re = _locale.voc_regex("tv_episode_keywords")
    if _TV_EPISODE_STRUCT_RE.search(combined) or (tv_ep_re and tv_ep_re.search(combined)):
        return ContentType.TV_EPISODE

    # COMPILATION — locale phrases + structural "Top N"
    comp_re = _locale.voc_regex("compilation_keywords")
    if (comp_re and comp_re.search(combined)) or _COMPILATION_TOP_N_RE.search(combined):
        return ContentType.COMPILATION

    # SHORT FILM — title keyword OR short-film channel tag
    short_film_re = _locale.voc_regex("short_film_keywords")
    channel_short_film_tags = _locale.voc_set("channel_short_film_tags")
    if (short_film_re and short_film_re.search(combined)) or (tags_lower & channel_short_film_tags):
        if length == 0 or length < _SHORT_FILM_MAX_SECONDS:
            return ContentType.SHORT_FILM

    # MOVIE — channel-tag only
    channel_movie_tags = _locale.voc_set("channel_movie_tags")
    if tags_lower & channel_movie_tags:
        if length == 0 or length >= _MOVIE_MIN_SECONDS:
            return ContentType.MOVIE

    # AUDIOBOOK
    audiobook_re = _locale.voc_regex("audiobook_keywords")
    if audiobook_re and audiobook_re.search(combined):
        return ContentType.AUDIOBOOK

    # PODCAST — publisher-defined only
    if is_podcast:
        return ContentType.PODCAST

    # STAND-UP COMEDY
    stand_up_re = _locale.voc_regex("stand_up_keywords")
    channel_stand_up_tags = _locale.voc_set("channel_stand_up_tags")
    if (stand_up_re and stand_up_re.search(combined)) or (tags_lower & channel_stand_up_tags):
        return ContentType.STAND_UP

    # LECTURE
    lecture_re = _locale.voc_regex("lecture_keywords")
    if lecture_re and lecture_re.search(title):
        return ContentType.LECTURE

    # INTERVIEW
    interview_re = _locale.voc_regex("interview_keywords")
    if interview_re and interview_re.search(title):
        return ContentType.INTERVIEW

    # CONCERT
    concert_re = _locale.voc_regex("concert_keywords")
    channel_concert_tags = _locale.voc_set("channel_concert_tags")
    if (concert_re and concert_re.search(title)) or (tags_lower & channel_concert_tags):
        return ContentType.CONCERT

    # NEWS
    news_re = _locale.voc_regex("news_keywords")
    channel_news_tags = _locale.voc_set("channel_news_tags")
    if (news_re and news_re.search(combined)) or (tags_lower & channel_news_tags):
        return ContentType.NEWS

    # SPORT
    sport_re = _locale.voc_regex("sport_keywords")
    channel_sport_tags = _locale.voc_set("channel_sport_tags")
    if (sport_re and sport_re.search(combined)) or (tags_lower & channel_sport_tags):
        return ContentType.SPORT

    # GAMING
    gaming_re = _locale.voc_regex("gaming_keywords")
    channel_gaming_tags = _locale.voc_set("channel_gaming_tags")
    if (gaming_re and gaming_re.search(combined)) or (tags_lower & channel_gaming_tags):
        return ContentType.GAMING

    # TUTORIAL
    tutorial_re = _locale.voc_regex("tutorial_keywords")
    if tutorial_re and tutorial_re.search(combined):
        return ContentType.TUTORIAL

    # REACTION
    reaction_re = _locale.voc_regex("reaction_keywords")
    if reaction_re and reaction_re.search(combined):
        return ContentType.REACTION

    # KIDS
    kids_re = _locale.voc_regex("kids_keywords")
    channel_kids_tags = _locale.voc_set("channel_kids_tags")
    if (kids_re and kids_re.search(combined)) or (tags_lower & channel_kids_tags):
        return ContentType.KIDS

    # MUSIC_AUDIO (release format) — always wins over MUSIC_VIDEO, even for OAC.
    # "Full Album", "Album Premiere", "Full EP" etc. are content-format signals:
    # a 40-min album upload is never a music video regardless of channel status.
    music_release_re = _locale.voc_regex("music_release_keywords")
    if music_release_re and music_release_re.search(title):
        return ContentType.MUSIC_AUDIO

    # MUSIC_VIDEO — title keyword OR official artist OR music channel tag; duration gate
    music_video_re = _locale.voc_regex("music_video_keywords")
    channel_music_tags = _locale.voc_set("channel_music_tags")
    if (music_video_re and music_video_re.search(title)) or is_official_artist or (tags_lower & channel_music_tags):
        if length == 0 or length <= _MUSIC_VIDEO_MAX_SECONDS:
            return ContentType.MUSIC_VIDEO

    # MUSIC_AUDIO (production type) — "Official Audio", "Lyric Video", "Visualizer".
    # Checked after MUSIC_VIDEO so OAC flag correctly promotes these to MUSIC_VIDEO above.
    music_audio_re = _locale.voc_regex("music_audio_keywords")
    if music_audio_re and music_audio_re.search(title):
        return ContentType.MUSIC_AUDIO

    return ContentType.VIDEO


def extract_tags(
    title: str,
    description: str = "",
    channel_tags: Optional[List[str]] = None,
) -> List[str]:
    """Return sorted list of freeform labels inferred from title and description.

    Labels are orthogonal to ContentType — they capture genre, era, format sub-type,
    audience, and other signals intentionally excluded from the main taxonomy.
    New labels may be added; treat the list as open-ended.

    Labels are driven by locale-loaded .voc files in ``tutubo/locale/<lang>/tags/``.
    Adding a new language's genre vocabulary requires only adding .voc files.
    """
    combined = f"{title} {description}"
    found = []

    for label, voc_name in _TAG_MANIFEST:
        rx = _locale.voc_regex(voc_name)
        if rx and rx.search(combined):
            found.append(label)

    # Structural supplement for silent-era: year patterns not expressible as phrases
    if _SILENT_ERA_YEAR_RE.search(combined) and "silent-era" not in found:
        found.append("silent-era")

    return sorted(found)
