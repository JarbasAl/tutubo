# TODO — tutubo

## Open issues

None open.

## Gaps

- [ ] `pyproject.toml` `Homepage` URL points at `https://github.com/OpenJarbas/tutubo`; the canonical remote is `TigreGotico/tutubo` — update it.
- [ ] `pyproject.toml` `description` ("YouTube search and stream wrapper around a bundled pytube fork") is stale — there is no pytube fork anymore; align with the README description.
- [ ] `requires-python = ">=3.8"` in pyproject, but CI build matrix targets 3.10–3.14 — reconcile the floor.
- [ ] No type-checker configured (no mypy/pyright); modules are partially type-hinted but unverified.
- [ ] Committed `.m3u8` artifacts (`youtubeTV*.m3u8`) and `.coverage` sit in repo root — confirm they belong in version control or gitignore them.

## Code TODOs

None found.
