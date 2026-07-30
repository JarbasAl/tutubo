# Content classification

Classification runs on multiple axes. `mediavocab.text.classify_video` returns a
`ClassificationResult` with orthogonal fields: `media_type`,
`content_form`, `programme_format`, `content_genres`. It uses only
information already available in search results or channel-page data, with no
extra per-video network fetches.

tutubo's search API is organized around single, human-facing **facets**
("documentaries", "live news", "music videos"), so
`tutubo.classification.Category` collapses a `ClassificationResult` (plus
the live and upcoming flags) to one facet through `classify_category`. Every
video exposes both:

- `Video.classification`: the full `ClassificationResult` (rich, multi-axis)
- `Video.content_type`: a single `Category` facet (for filtering or display)

```python
from tutubo import Category, classify_category, classify_video
result = classify_video(title="Dune: Part Two - Official Trailer")
result.media_type        # MediaType.MOVIE
result.content_form      # ContentForm.TRAILER
classify_category(result)  # Category.TRAILER
```

`Category` is tutubo-owned. mediavocab is the source of truth for the
underlying classification logic: priority order, keyword vocabularies,
duration thresholds. `ContentType` remains as a back-compat alias of
`Category`.

---

## Category facets

`Category` is both a `str` and an `enum.Enum`, so values compare equal to their string representations:

```python
from tutubo import Category
Category.MOVIE == "movie"   # True
Category.MOVIE.value        # "movie"
```

| Value | String | Description | Example title |
|---|---|---|---|
| `VIDEO` | `"video"` | Generic YouTube video, the default when no other type matches | "Random vlog #42" |
| `SOCIAL_CLIP` | `"social_clip"` | Under 62 seconds (YouTube Shorts / social clip format) | Any reel at most 61 s |
| `SHORT_FILM` | `"short_film"` | Narrative short film, distinct from YouTube Shorts | "Dust - Short Film: Parallel" |
| `LIVE` | `"live"` | Currently broadcasting, no sub-classification matched | "Playing chess with viewers" |
| `UPCOMING` | `"upcoming"` | Scheduled premiere or waiting room | "Album Release Party - Premiering Soon" |
| `LIVE_RADIO` | `"live_radio"` | Live radio station or 24/7 music stream | "24/7 Jazz Radio - Smooth Jazz" |
| `LIVE_NEWS` | `"live_news"` | Live news broadcast stream | "BBC News Live" |
| `IPTV` | `"iptv"` | Live TV channel that is not a news channel | "Sky Sports Live TV" |
| `MOVIE` | `"movie"` | Full feature-length film (at least 60 min if duration is known) | "Nosferatu 1922 Full Movie" |
| `TRAILER` | `"trailer"` | Movie or show trailer or teaser (at most 10 min if duration is known) | "Dune Part Two - Official Trailer" |
| `BEHIND_THE_SCENES` | `"behind_the_scenes"` | Making-of, bloopers, deleted scenes, on-set footage | "Making of Oppenheimer - Featurette" |
| `DOCUMENTARY` | `"documentary"` | Documentary, docu-series, docufilm, or docudrama | "Planet Earth III - Full Documentary" |
| `ANIME` | `"anime"` | Anime episode or series | "One Piece Episode 1 - Full English Sub" |
| `TV_EPISODE` | `"tv_episode"` | Scripted TV series episode | "Breaking Bad S01E01 Full Episode" |
| `AUDIOBOOK` | `"audiobook"` | Audiobook, audio drama, or radio play: spoken audio without video (single-narrator readings and full-cast productions) | "1984 George Orwell Full Audiobook Narrated by" |
| `PODCAST` | `"podcast"` | Podcast episode, publisher-defined only, never inferred from title | (see PODCAST note below) |
| `STAND_UP` | `"stand_up"` | Stand-up comedy special or comedy show | "Dave Chappelle - The Closer Comedy Special" |
| `INTERVIEW` | `"interview"` | Dedicated one-on-one or panel interview | "Elon Musk in conversation with Lex Fridman" |
| `LECTURE` | `"lecture"` | Academic lecture, TED Talk, Masterclass, or open course | "Richard Feynman - Lecture on Quantum Mechanics" |
| `CONCERT` | `"concert"` | Live concert recording or full performance | "Metallica Live at Wembley - Full Concert" |
| `NEWS` | `"news"` | Recorded news segment, report, briefing, or recap | "Breaking News: Today's Market Roundup" |
| `SPORT` | `"sport"` | Sports match, highlights reel, or game recap | "Full Match: Arsenal vs Chelsea - Game Highlights" |
| `GAMING` | `"gaming"` | Gameplay footage, let's play, or playthrough | "Minecraft Survival - Let's Play Episode 1" |
| `TUTORIAL` | `"tutorial"` | Instructional how-to, DIY, or step-by-step guide | "How to Build a REST API in Python - Tutorial" |
| `REACTION` | `"reaction"` | Reaction or first-watch video | "First Time Watching 'The Godfather' - Reaction" |
| `COMPILATION` | `"compilation"` | Clip compilation, best-of, or top-N list | "Best of Gordon Ramsay - Top 10 Moments" |
| `KIDS` | `"kids"` | Children's content, cartoons, nursery rhymes | "Baby Shark - Kids Song for Toddlers" |
| `MUSIC_VIDEO` | `"music_video"` | Official music video | "Rob Zombie - Dragula Official Music Video" |
| `MUSIC_AUDIO` | `"music_audio"` | Audio-only: lyric video, visualizer, or official audio track | "Billie Eilish - bad guy (Official Audio)" |

---

## `classify_video()` signature

`mediavocab.text.classify_video`

```python
classify_video(
    title: str,
    description: str = "",
    length: int = 0,
    is_live: bool = False,
    is_upcoming: bool = False,
    is_official_artist: bool = False,
    is_podcast: bool = False,
    channel_tags: list = None,
) -> ContentType
```

| Parameter | Type | Description |
|---|---|---|
| `title` | `str` | Video title. Most patterns match against the title only. |
| `description` | `str` | Description text or snippet. Some patterns (MOVIE, DOCUMENTARY, ANIME, and others) check `"{title} {description}"` combined. |
| `length` | `int` | Duration in seconds. `0` means unknown. Duration gates use `0` as a pass, so an unknown duration never blocks a classification. |
| `is_live` | `bool` | When `True`, activates the live-stream sub-classifier (LIVE_RADIO to LIVE_NEWS to IPTV to LIVE). If `True`, all non-live patterns are skipped entirely. |
| `is_upcoming` | `bool` | When `True` (and `is_live` is `False`), returns `UPCOMING` immediately. |
| `is_official_artist` | `bool` | When `True`, contributes to `MUSIC_VIDEO` classification at the end of the chain (same position as the music-channel tag signal). |
| `is_podcast` | `bool` | When `True`, returns `PODCAST` after audio-drama and audiobook checks. **This must come from publisher-defined data.** Never infer it from title keywords. |
| `channel_tags` | `list` | Channel keyword tags (strings). Used for channel-context boosting, see the section below. Matching is case-insensitive. Values are lowercased internally. |

`VideoPreview.content_type` calls `classify_video()` with `title`, `description_snippet`, `length`, `is_live`, `is_upcoming`, and `is_official_artist` from the search result. It does not pass `channel_tags`, because search results carry no channel keyword data. `Video.content_type` (from channel tabs) calls `classify_video()` with `channel_tags=self.channel_tags` populated from `Channel.keywords`.

---

## Priority chain

The chain runs top to bottom. The first match wins and returns immediately. Items marked **[LIVE ONLY]** only run when `is_live=True`.

1. **[LIVE ONLY] LIVE_RADIO**: title or description matches a radio or 24/7 music pattern
2. **[LIVE ONLY] LIVE_NEWS**: title or description matches a live-news pattern, or a channel tag contains `"news"`, `"noticias"`, or `"actualidad"`, or `channel_tags & _CHANNEL_NEWS_TAGS`
3. **[LIVE ONLY] IPTV**: title or description matches a live TV or IPTV pattern
4. **[LIVE ONLY] LIVE**: catch-all for any live stream that matched none of the above
5. **UPCOMING**: `is_upcoming=True`
6. **SOCIAL_CLIP**: `0 < length < 62`
7. **TRAILER**: title matches `\b(official\s+)?trailer\b|\bteaser\b`, blocked if `length > 600`
8. **MOVIE** (title): `"{title} {description}"` matches `\bfull\s+\w*\s*(?:movie|film|length)\b` or `\bcomplete\s+film\b`, blocked if `length < 3600` (when `length > 0`)
9. **DOCUMENTARY**: combined text matches `\bdocumentary\b` or `\bdocu…\b`, or `channel_tags & _CHANNEL_DOC_TAGS`
10. **BEHIND_THE_SCENES**: combined text matches making-of, bloopers, or on-set vocabulary
11. **ANIME**: combined text matches `\banime\b`, or `channel_tags & _CHANNEL_ANIME_TAGS`
12. **TV_EPISODE**: combined text matches `S\d\dE\d\d\d?`, `Season N … Episode N`, or `Full Episode`
13. **COMPILATION**: combined text matches `\bcompilation\b`, `\bbest\s+of\b`, or `\btop\s+\d+\b`
14. **SHORT_FILM** (title/tag): combined text matches `\bshort\s+(?:film|movie)\b`, or `channel_tags & _CHANNEL_SHORT_FILM_TAGS`, blocked if `length >= 3600` (when `length > 0`)
15. **MOVIE** (channel tag): `channel_tags & _CHANNEL_MOVIE_TAGS`, blocked if `length < 3600`
16. **AUDIOBOOK**: combined text matches audiobook vocabulary (audiobook, full audio book, read aloud, narrated by) or audio drama / radio play vocabulary (audio drama, audio play, radio play, radiodrama, full cast audio, dramatised/dramatized)
17. **PODCAST**: `is_podcast=True`
18. **STAND_UP**: combined text matches stand-up vocabulary, or `channel_tags & _CHANNEL_STAND_UP_TAGS`
19. **LECTURE**: title matches `\blecture\b`, `\bTEDx?\b`, `\bTED\s+Talk\b`, `\bMasterclass\b`, `\b(online|open)\s+course\b`
20. **INTERVIEW**: title matches interview vocabulary (`interview with`, `in conversation with`, `talks to`, `sits down with`)
21. **CONCERT**: title matches concert vocabulary, or `channel_tags & _CHANNEL_CONCERT_TAGS`
22. **NEWS**: combined text matches news vocabulary, or `channel_tags & _CHANNEL_NEWS_TAGS`
23. **SPORT**: combined text matches sport vocabulary, or `channel_tags & _CHANNEL_SPORT_TAGS`
24. **GAMING**: combined text matches gaming vocabulary, or `channel_tags & _CHANNEL_GAMING_TAGS`
25. **TUTORIAL**: combined text matches tutorial vocabulary
26. **REACTION**: combined text matches reaction vocabulary
27. **KIDS**: combined text matches children's content vocabulary, or `channel_tags & _CHANNEL_KIDS_TAGS`
28. **MUSIC_VIDEO**: title matches `\bofficial\s+(music\s+)?video\b|\bOMV\b`, or `is_official_artist=True`, or `channel_tags & _CHANNEL_MUSIC_TAGS`, blocked if `length > 900` (when `length > 0`)
29. **MUSIC_AUDIO**: title matches audio, lyric, or visualizer vocabulary, or matches full-album, album-premiere, or EP-premiere patterns
30. **VIDEO**: default, nothing else matched

### Key ordering decisions

**COMPILATION before SHORT_FILM (step 13 before 14):** a title like "Top 10 Short Films" would otherwise match the SHORT_FILM regex. tutubo checks COMPILATION first.

**SHORT_FILM (title/tag) before MOVIE (channel tag) (step 14 before 15):** a channel that carries both `"short film"` and `"full movie"` tags (this does happen) should not promote a 45-minute short film to MOVIE. The more specific SHORT_FILM check runs first.

**DOCUMENTARY before BEHIND_THE_SCENES (step 9 before 10):** a title like "Making Of: A Docuseries" would fire both. DOCUMENTARY wins.

**LIVE_RADIO before LIVE_NEWS (step 1 before 2):** "24/7 Radio News" would match both. tutubo checks the radio stream first. If you need live-news radio specifically, check both `LIVE_RADIO` and `LIVE_NEWS`.

---

## Duration hard limits

| Type | Limit | Effect |
|---|---|---|
| `MOVIE` (title) | `length >= 3600` | If `length > 0` and `length < 3600`, tutubo skips the match and classification continues down the chain |
| `MOVIE` (channel tag) | `length >= 3600` | Same gate |
| `TRAILER` | `length <= 600` | If `length > 0` and `length > 600`, tutubo skips the match |
| `SHORT_FILM` | `length < 3600` | If `length > 0` and `length >= 3600`, tutubo skips the match |
| `SOCIAL_CLIP` | `0 < length < 62` | Applied before all regex checks |
| `MUSIC_VIDEO` | `length <= 900` | If `length > 0` and `length > 900`, tutubo skips the match |

When `length == 0` (unknown), duration gates pass and tutubo assigns the type regardless of duration. This lets classification work on live streams and on `VideoPreview` objects that report no duration.

---

## Channel tag signal sets

Channel tags (`_CHANNEL_*_TAGS`) provide context when the video title alone is ambiguous. tutubo checks them against `{t.lower() for t in channel_tags}` using set intersection. All sets are defined in `tutubo/content_type.py`.

| Variable | Used for | Example tags |
|---|---|---|
| `_CHANNEL_MOVIE_TAGS` | `MOVIE` (step 15) | `"full movie"`, `"feature film"`, `"soviet cinema"`, `"hollywood movies"` |
| `_CHANNEL_DOC_TAGS` | `DOCUMENTARY` (step 9) | `"documentary"`, `"nature"`, `"history"`, `"biography"` |
| `_CHANNEL_ANIME_TAGS` | `ANIME` (step 11) | `"anime"`, `"アニメ"`, `"manga"`, `"漫画"` |
| `_CHANNEL_SHORT_FILM_TAGS` | `SHORT_FILM` (step 14) | `"short film"`, `"short films"`, `"short form"` |
| `_CHANNEL_KIDS_TAGS` | `KIDS` (step 28) | `"kids"`, `"nursery rhymes"`, `"baby shark"`, `"preschool"` |
| `_CHANNEL_NEWS_TAGS` | `LIVE_NEWS` (step 2) and `NEWS` (step 23) | `"news"`, `"journalism"`, `"breaking news"`, `"current events"` |
| `_CHANNEL_SPORT_TAGS` | `SPORT` (step 24) | `"football"`, `"nba"`, `"formula 1"`, `"mma"` |
| `_CHANNEL_GAMING_TAGS` | `GAMING` (step 25) | `"gaming"`, `"esports"`, `"let's play"`, `"twitch"` |
| `_CHANNEL_MUSIC_TAGS` | `MUSIC_VIDEO` (step 29) | `"music"`, `"artist"`, `"band"`, `"concerts"` |
| `_CHANNEL_CONCERT_TAGS` | `CONCERT` (step 22) | `"concerts"`, `"live music"`, `"live nation"` |
| `_CHANNEL_STAND_UP_TAGS` | `STAND_UP` (step 19) | `"stand up comedy"`, `"comedy special"`, `"comedian"` |

**Channel tags always carry lower priority than title-based signals for the same type.** For example, MOVIE through the title (step 8) fires before MOVIE through the channel tag (step 15). So a channel tagged `"full movie"` uploading a 2-minute trailer still classifies as TRAILER, not MOVIE, because the TRAILER title check at step 7 wins.

---

## Live stream sub-classification

When `is_live=True`, the first four checks in the chain apply, in order:

```
LIVE_RADIO → LIVE_NEWS → IPTV → LIVE
```

All four checks examine `f"{title} {description}"` (combined) and `{t.lower() for t in channel_tags}`.

**LIVE_RADIO regex** (title/description only):
- `\b(?:live\s+)?(?:24\/7\s+)?(?:radio|fm\s+radio|am\s+radio|radio\s+station)\b`
- `\b24\/7\s+(?:music|jazz|classical|hits)\b`
- `\blive\s+(?:radio|stream)\s+(?:radio|fm|am)\b`

**LIVE_NEWS** (title/description OR channel tags):
- Title/description: `\blive\s+news\b`, `\bnews\s+live\b`, `\b24\/7\s+news\b`, and similar
- Channel tags: any tag containing the substring `"news"`, `"noticias"`, or `"actualidad"`, or `channel_tags & _CHANNEL_NEWS_TAGS`

The substring check (`"news" in tag`) is intentionally broader than a set lookup. It catches tags like `"world news"`, `"bbc news"`, `"sky news"`, and `"noticias en vivo"` without requiring them to be listed explicitly.

**IPTV regex** (title/description only):
- `\blive\s+(?:tv|television)\b`
- `\b24\/7\s+(?:tv|channel)\b`
- `\biptv\b`

**LIVE**: all other live streams.

---

## PODCAST classification

`ContentType.PODCAST` is intentionally publisher-defined only. tutubo never infers it from title keywords such as "podcast", "episode", or "ep", because those words appear in titles of interviews, lectures, and talk shows uploaded to regular video channels rather than podcast shows.

The correct source for `is_podcast=True` is `Channel.podcasts`, which reads from the YouTube Podcasts tab, a tab that appears only when the channel owner has explicitly created podcast shows. You can then classify episodes from that tab as follows:

```python
from mediavocab.text import classify_video
from tutubo import ContentType
ct = classify_video(
    title=ep_title,
    is_podcast=True,
)
assert ct == ContentType.PODCAST
```

---

## AUDIOBOOK: single-narrator and full-cast productions

`ContentType.AUDIOBOOK` covers all spoken-audio content without video, both single-narrator prose readings and multi-cast productions (audio dramas, radio plays). The `_AUDIOBOOK_RE` regex matches:

- Audiobook vocabulary: `audiobook`, `full audio book`, `read aloud`, `narrated by`
- Full-cast / drama vocabulary: `audio drama`, `audio play`, `radio play`, `radiodrama`, `full cast audio`, `dramatised`, `dramatized`

There is no separate `AUDIO_DRAMA` type. Full-cast productions classify as `AUDIOBOOK`.

---

## Auto-tagging

`extract_tags` - `mediavocab.text.extract_tags`

```python
extract_tags(title: str, description: str = "", channel_tags: list = None) -> list[str]
```

Returns a sorted list of freeform string labels derived from the title, description, and channel tags. Tags are orthogonal to `ContentType`. They answer "what genre, era, or format subtype?" rather than "what format is this?". A video classified as `AUDIOBOOK` can carry tags `["full-cast", "horror", "lovecraft"]`.

| Category | Example labels |
|---|---|
| Audio format | `narrated`, `full-cast`, `radio-play` |
| Genres | `horror`, `sci-fi`, `fantasy`, `thriller`, `romance`, `comedy`, `action`, `crime`, `war`, `western`, `animation`, `superhero` |
| Music genres | `classical`, `jazz`, `metal`, `hip-hop`, `electronic`, `folk`, `reggae`, `punk`, `country`, `r&b` |
| Sports | `football`, `basketball`, `baseball`, `tennis`, `motorsport`, `combat`, `esports` |
| Spoken word | `debate`, `ted-talk`, `panel` |
| Production/era | `silent-era`, `classic`, `colorized`, `4k`, `short` |
| Audience | `kids`, `educational` |
| Niche | `lovecraft`, `wayne-june` |

```python
from mediavocab.text import extract_tags
extract_tags("Lovecraft narrated by Wayne June")
# ["lovecraft", "narrated", "wayne-june"]
extract_tags("The War of the Worlds - Full Cast Audio Drama", channel_tags=["sci-fi"])
# ["full-cast", "radio-play", "sci-fi"]
```

`VideoPreview.tags` and `Video.tags` both expose this as a computed property. Both `as_dict` outputs include a `"tags"` key.

---

## MUSIC_AUDIO: full-album and premiere patterns

In addition to lyric, audio, and visualizer vocabulary, `MUSIC_AUDIO` fires when the title indicates a complete album or EP release. tutubo matches these patterns through the `music_audio_keywords.voc` file in each locale:

- Full album: "full album", "álbum completo", "album complet", and similar
- Album premiere: "album premiere", "new album", and similar
- EP premiere: "ep premiere", "new ep", and similar

Full albums typically run 30 to 90 minutes, so the 900-second MUSIC_VIDEO gate naturally pushes longer music content toward MUSIC_AUDIO without a separate duration check.

---

## Locale-driven keyword matching

Most keyword patterns in `classify_video()` come from `.voc` files under `mediavocab/locale/<lang>/` (in the mediavocab package). This makes classification work across multiple languages without changing Python code.

Structural patterns that stay in Python (not in `.voc` files):
- Episode codes (`S01E02`, `Season N Episode N`)
- Top-N compilation pattern (`top \d+`)
- Duration gates (all numeric thresholds)
- `is_live`, `is_upcoming`, `is_podcast` flag checks

These are not translatable. They are either numeric or language-universal.

### Supported languages

| Code | Coverage |
|---|---|
| `en-us` | Full, all `.voc` files present |
| `fr-fr` | Full |
| `it-it` | Full |
| `es` | Full, shared base for all Spanish variants |
| `es-es` | Sparse overrides on top of `es` |
| `es-mx` | Sparse overrides on top of `es` |
| `pt` | Full, shared base for all Portuguese variants |
| `pt-pt` | Sparse overrides on top of `pt` |
| `pt-br` | Sparse overrides on top of `pt` |
| `nl-nl` | Full |

The fallback chain is: exact locale, then language-only code, then `en-us`. For example, `es-mx` falls back to `es`, then to `en-us`.

### Setting the language

```python
from tutubo import classify_video
# Per-call (recommended for concurrent / multi-tenant use):
classify_video("Film complet en français", length=7200, lang="fr-fr")
# Or set the process-wide default at startup:
# MEDIAVOCAB_LANG=fr-fr python my_script.py
```

See [docs/locale.md](locale.md) for the full reference.

---

## Extending: adding a new ContentType

`ContentType` and `classify_video` live in the mediavocab package. To extend them, modify mediavocab directly:

1. Add a value to the `ContentType` enum in mediavocab.
2. Define a compiled regex alongside the other `_*_RE` constants in `mediavocab/text/classify.py`.
3. Optionally define a channel-tag set (`_CHANNEL_*_TAGS = {…}`) for channel-context boosting.
4. Insert the classification block in `classify_video()` at the right priority position. Follow the existing `if` / `return` pattern.
5. Add test cases: at minimum one positive title, one negative title, and one priority-conflict case.

Example: adding `ContentType.COMMENTARY`:

```python
# In content_type.py - after _REACTION_RE definition:
_COMMENTARY_RE = re.compile(
    r'\bcommentary\b'
    r'|\banalysis\b'
    r'|\bbreakdown\b',
    re.IGNORECASE,
)
# In the ContentType enum:
COMMENTARY = "commentary"
# In classify_video() - after REACTION, before COMPILATION:
if _COMMENTARY_RE.search(combined):
    return ContentType.COMMENTARY
```

Choose the priority position carefully. If COMMENTARY sits after COMPILATION, "Top 10 Best Analysis Videos - Compilation" classifies as COMPILATION. If it sits before, the same title classifies as COMMENTARY. Either choice can be correct, depending on your use case.

---
[← Models](models.md) · [Home](index.md) · [mediavocab →](mediavocab.md)
