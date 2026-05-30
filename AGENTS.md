# AGENTS.md — tutubo

Dependency-light YouTube / YouTube Music scraper that classifies results by content type and bridges them to typed `mediavocab` `Work` / `Release` / `Entity` models. No pytube dependency.

## Setup

```bash
pip install -e .
pip install -e .[test]      # adds pytest, vcrpy, pytest-vcr
pip install -e .[stealth]   # adds curl-cffi for browser-fingerprinted TLS
```

`mediavocab>=1.0.0` is a hard runtime dependency (not optional). Other runtime deps: `bs4`, `requests`, `ytmusicapi`.

## Test

```bash
pytest test/
```

Tests are fully offline. Raw YouTube/innertube responses live as JSON/HTML fixtures under `test/fixtures/`; `test/conftest.py` monkeypatches `tutubo._innertube._post` so nothing touches the network. Re-record fixtures (network) with:

```bash
TUTUBO_RECORD_DIR=test/fixtures python test/record_fixtures.py
```

## Lint

```bash
ruff check tutubo/
```

Ruff is wired into CI via the shared lint workflow. There is no type-checker configured.

## Layout

- `tutubo/search.py` — `YoutubeSearch` (youtube.com) and `YoutubeMusicSearch` (music.youtube.com); 24 `for_*` intent factories + matching `iterate_*` typed iterators.
- `tutubo/channel.py` — `Channel` (tab iteration: `.videos`, `.shorts`, `.streams`, `.live`, `.playlists`, `.podcasts`), `Playlist`, `Video`, `PodcastPreview`.
- `tutubo/ytmus.py` — YouTube Music models: `MusicTrack`, `MusicVideo`, `MusicAlbum`, `MusicPlaylist`, `MusicArtist`.
- `tutubo/models.py` — search-result preview types: `VideoPreview`, `ChannelPreview`, `PlaylistPreview`, `YoutubeMixPreview`, `RelatedVideoPreview`, `RelatedSearch`.
- `tutubo/mediavocab_bridge.py` — the only place mapping logic lives; `video_to_work`/`video_to_release`, `music_*`, `channel_to_entity`, `podcast_preview_to_*`. Model classes expose thin `to_work()` / `to_release()` / `to_entity()` delegators.
- `tutubo/_innertube.py` — low-level innertube `_post` (stdlib `urllib.request`); the search path.
- `tutubo/transport.py` — pluggable session for channel/playlist HTML fetches; `TUTUBO_TRANSPORT=curl_cffi` swaps in fingerprinted TLS.
- `tutubo/download.py` — optional `download` / `download_playlist` (require yt-dlp).
- `tutubo/_utils.py`, `tutubo/version.py`.
- `examples/` — 11 numbered walkthroughs plus topical scripts (iptv, livestreams, podcasts, music). `docs/` — per-topic reference.

`ContentType`, `classify_video`, `parse_title`, `extract_tags` are re-exported from `mediavocab`, not defined locally.

## Conventions

- Branches: work on `dev`, stable is `master`. Never use `main`.
- Never edit `tutubo/version.py` — gh-automations bumps semver from conventional-commit prefixes (`feat:` / `fix:` / `feat!:`).
- New repos private by default.
- Commit identity: `JarbasAi <jarbasai@mailfence.com>`.
- Reference `OpenVoiceOS/gh-automations` reusable workflows at `@dev`.
- No Neon / `neon-*` references.
- No meta-commentary (no history, dates, or "before times") in code, docs, commits, or PRs — describe current state only.
- CI is provided by OpenVoiceOS/gh-automations.

## Gotchas

- A `Video` from a channel tab has NO `length` field (channel-page renderers omit duration); `view_count` is a human string and `published_time` is relative. A `VideoPreview` from search has `length` as int seconds and `view_count` as an exact int.
- `Channel.live` reads `/@handle/live` (watch-page redirect) and returns one `Video` or `None`; `Channel.streams` reads the `/@handle/streams` browse tab and returns the full lazy list.
- `VideoPreview.content_type` does not use channel tags (search results lack them); `Video.content_type` does and is more accurate for ambiguous titles.
- `_innertube._post` (search) uses stdlib `urllib.request` and ignores `TUTUBO_TRANSPORT`; only channel/playlist HTML fetches honour the stealth transport.
- The bridge forces `MediaType.GENERIC` results to `MediaType.MOVIE` (mediavocab 1.0 rejects sentinel MediaTypes at `Work` construction); `LIVE_NEWS` deliberately emits `MOVIE + ["news"]` rather than `TV` to avoid the EPG schema mismatch — see `_content_type_to_media_type`.
- `pyproject.toml` `Homepage` points at `OpenJarbas/tutubo`; the canonical remote is `TigreGotico/tutubo`.
- `nightly-live.yml` re-records fixtures against live YouTube and re-runs the suite to detect upstream drift (the silent "empty results" failure mode); captured fixtures are NOT committed back.
