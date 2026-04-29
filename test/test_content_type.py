"""In-depth tests for tutubo.content_type — classify_video() and ContentType.

Coverage:
  - Every ContentType value
  - Every regex pattern (positive and negative)
  - Priority ordering (what wins when multiple patterns fire)
  - Duration boundary conditions
  - Channel-tag enrichment signals
  - Audiobook classification
  - TRAILER duration hard limit
  - Known false positives (documented)
  - Real-world titles from recorded fixtures
  - Direct VideoPreview.content_type via conftest patch_innertube
"""
import pytest
from tutubo.content_type import (
    ContentType, classify_video,
    _MOVIE_MIN_SECONDS, _TRAILER_MAX_SECONDS, _SHORT_FILM_MAX_SECONDS,
)


# ===========================================================================
# Helpers
# ===========================================================================

def _ct(title, *, length=300, is_live=False, is_upcoming=False,
        is_official_artist=False, is_podcast=False, channel_tags=None, description=""):
    """Shorthand for classify_video with named-only overrides."""
    return classify_video(
        title=title,
        description=description,
        length=length,
        is_live=is_live,
        is_upcoming=is_upcoming,
        is_official_artist=is_official_artist,
        is_podcast=is_podcast,
        channel_tags=channel_tags,
    )


# ===========================================================================
# LIVE — highest priority
# ===========================================================================

class TestLive:
    def test_is_live_flag(self):
        assert _ct("anything", is_live=True) == ContentType.LIVE

    def test_live_beats_trailer(self):
        assert _ct("Official Trailer 2024", is_live=True) == ContentType.LIVE

    def test_live_beats_movie(self):
        assert _ct("Full Movie", length=7200, is_live=True) == ContentType.LIVE

    def test_live_beats_podcast(self):
        assert _ct("Episode 400", is_live=True, is_podcast=True) == ContentType.LIVE

    def test_live_beats_official_artist(self):
        assert _ct("Song Name", is_live=True, is_official_artist=True) == ContentType.LIVE

    def test_not_live_without_flag(self):
        assert _ct("Live at Wembley") != ContentType.LIVE


# ===========================================================================
# UPCOMING — second priority
# ===========================================================================

class TestUpcoming:
    def test_is_upcoming_flag(self):
        assert _ct("anything", is_upcoming=True) == ContentType.UPCOMING

    def test_upcoming_beats_trailer(self):
        assert _ct("Official Trailer", is_upcoming=True) == ContentType.UPCOMING

    def test_upcoming_beats_movie(self):
        assert _ct("Full Movie HD", length=7200, is_upcoming=True) == ContentType.UPCOMING

    def test_live_beats_upcoming(self):
        assert _ct("x", is_live=True, is_upcoming=True) == ContentType.LIVE


# ===========================================================================
# SOCIAL_CLIP — duration < 62 seconds (YouTube Shorts / Reels)
# ===========================================================================

class TestSocialClip:
    def test_1_second(self):
        assert _ct("clip", length=1) == ContentType.SOCIAL_CLIP

    def test_61_seconds(self):
        assert _ct("clip", length=61) == ContentType.SOCIAL_CLIP

    def test_boundary_62_is_not_short(self):
        assert _ct("clip", length=62) != ContentType.SOCIAL_CLIP

    def test_zero_length_is_not_short(self):
        assert _ct("clip", length=0) != ContentType.SOCIAL_CLIP

    def test_short_beats_trailer_title(self):
        assert _ct("Quick Trailer", length=30) == ContentType.SOCIAL_CLIP

    def test_short_beats_music_video(self):
        assert _ct("Song Snippet", length=20, is_official_artist=True) == ContentType.SOCIAL_CLIP

    def test_known_short_from_fixture(self):
        assert _ct("how programmers overprepare for job interviews", length=60) == ContentType.SOCIAL_CLIP

    def test_known_short_61s_from_fixture(self):
        assert _ct("Google vs. Microsoft", length=61) == ContentType.SOCIAL_CLIP


# ===========================================================================
# TRAILER — regex patterns + duration hard limit
# ===========================================================================

class TestTrailer:
    # --- Positive matches ---
    def test_official_trailer(self):
        assert _ct("Dune: Part Two — Official Trailer") == ContentType.TRAILER

    def test_official_trailer_numbered(self):
        assert _ct("Avengers: Endgame - Official Trailer #2") == ContentType.TRAILER

    def test_bare_trailer_keyword(self):
        assert _ct("AZRAEL Trailer (2024) Post Rapture Movie") == ContentType.TRAILER

    def test_trailer_in_parens(self):
        assert _ct("The Batman (Trailer)") == ContentType.TRAILER

    def test_case_insensitive_trailer(self):
        assert _ct("SPIDER-MAN OFFICIAL TRAILER") == ContentType.TRAILER

    def test_teaser_word(self):
        assert _ct("Stranger Things Season 5 — Teaser") == ContentType.TRAILER

    def test_teaser_trailer_combo(self):
        assert _ct("Bob Marley: One Love - Teaser Trailer (2024 Movie)") == ContentType.TRAILER

    def test_real_fixture_relive(self):
        assert _ct("RELIVE Official Trailer (2026)", length=137) == ContentType.TRAILER

    def test_real_fixture_megalopolis(self):
        assert _ct("Megalopolis (2024) Official Trailer - Adam Driver, Giancarlo Esposito,", length=129) == ContentType.TRAILER

    def test_real_fixture_slingshot(self):
        assert _ct("SLINGSHOT Official Trailer (2024)", length=160) == ContentType.TRAILER

    def test_real_fixture_bob_marley_teaser(self):
        assert _ct("Bob Marley: One Love - Teaser Trailer (2024 Movie)", length=179) == ContentType.TRAILER

    # --- Duration hard limit: > 600s → not a single trailer (compilation) ---
    def test_trailer_compilation_above_600s_is_video(self):
        result = _ct("NEW MOVIE TRAILERS 2024", length=2684)
        assert result != ContentType.TRAILER

    def test_best_trailers_compilation(self):
        result = _ct("20 BEST MOVIE TRAILERS 2025 (February) 4K ULTRA HD", length=2195)
        assert result != ContentType.TRAILER

    def test_upcoming_movies_trailers(self):
        result = _ct("BEST UPCOMING MOVIES 2024 (Trailers)", length=1925)
        assert result != ContentType.TRAILER

    def test_trailer_at_600s_accepted(self):
        assert _ct("Official Trailer Extended", length=600) == ContentType.TRAILER

    def test_trailer_at_601s_rejected(self):
        result = _ct("Official Trailer Extended", length=601)
        assert result != ContentType.TRAILER

    def test_trailer_unknown_length_accepted(self):
        assert _ct("Official Trailer Extended", length=0) == ContentType.TRAILER

    # --- "TRAILERS" plural does NOT match \btrailer\b ---
    def test_trailers_plural_is_not_trailer(self):
        result = _ct("NEW MOVIE TRAILERS 2024", length=200)
        assert result != ContentType.TRAILER

    # --- Known false positive ---
    def test_trailer_park_boys_is_false_positive(self):
        # With unknown duration (0) the hard limit doesn't fire — documents the regex FP
        result = _ct("Trailer Park Boys S01E01", length=0)
        assert result == ContentType.TRAILER  # documenting known FP


# ===========================================================================
# MOVIE — title + channel-tag + duration guard
# ===========================================================================

class TestMovie:
    _MOVIE_MIN = _MOVIE_MIN_SECONDS  # 3600s (60 min)

    def test_full_movie_long(self):
        assert _ct("Inception Full Movie", length=8880) == ContentType.MOVIE

    def test_full_film(self):
        assert _ct("The Matrix Full Film HD", length=8160) == ContentType.MOVIE

    def test_full_length_film(self):
        assert _ct("Blade Runner Full Length Version", length=7020) == ContentType.MOVIE

    def test_complete_film(self):
        assert _ct("Complete Film: Citizen Kane (1941)", length=6120) == ContentType.MOVIE

    def test_real_fixture_ratchet(self):
        assert _ct("Ratchet (2026) | Full Movie | Horror | Thriller", length=7007) == ContentType.MOVIE

    def test_real_fixture_tentacle(self):
        assert _ct("Tentacle 8 | Spy Thriller | Full Movie | Secret Missions", length=7481) == ContentType.MOVIE

    def test_real_fixture_toronto(self):
        assert _ct("TORONTO - FULL MOVIE ENGLISH 2023 | action movies 2024 full movie english", length=6205) == ContentType.MOVIE

    def test_real_fixture_hope_springs(self):
        # "Full Comedy Movie" — expanded regex allows one word between "full" and "movie"
        result = _ct("HOPE SPRINGS | Full Comedy Movie | Colin Firth, Minnie Driver, Heather", length=6507)
        assert result == ContentType.MOVIE

    def test_full_movie_unknown_duration(self):
        assert _ct("Watch Full Movie Free", length=0) == ContentType.MOVIE

    def test_full_movie_short_clip_rejected(self):
        assert _ct("Full Movie Preview Clip", length=600) != ContentType.MOVIE

    def test_full_movie_at_2699s_rejected(self):
        assert _ct("Watch Full Movie", length=self._MOVIE_MIN - 1) != ContentType.MOVIE

    def test_full_movie_at_2700s_accepted(self):
        assert _ct("Watch Full Movie", length=self._MOVIE_MIN) == ContentType.MOVIE

    def test_long_video_without_keyword(self):
        result = _ct("Jason Statham Action Thriller 2024", length=7200)
        assert result != ContentType.MOVIE

    def test_description_triggers_movie(self):
        assert _ct("Watch Now", description="Enjoy this full movie in HD", length=5400) == ContentType.MOVIE

    def test_description_without_min_duration_rejected(self):
        assert _ct("Watch Now", description="full movie here", length=300) != ContentType.MOVIE


# ===========================================================================
# DOCUMENTARY
# ===========================================================================

class TestDocumentary:
    def test_documentary_keyword(self):
        assert _ct("Planet Earth Documentary Full", length=2700) == ContentType.DOCUMENTARY

    def test_docuseries(self):
        assert _ct("Making Of: A Docuseries") == ContentType.DOCUMENTARY

    def test_docufilm(self):
        assert _ct("Tiger King Docufilm") == ContentType.DOCUMENTARY

    def test_docudrama(self):
        assert _ct("The Crown Docudrama") == ContentType.DOCUMENTARY

    def test_docu_standalone(self):
        assert _ct("Award-winning Docu") == ContentType.DOCUMENTARY

    def test_case_insensitive(self):
        assert _ct("NATURE DOCUMENTARY 4K") == ContentType.DOCUMENTARY

    def test_real_fixture_attenborough(self):
        assert _ct("David Attenborough | Tasmania | Documentary", length=2997) == ContentType.DOCUMENTARY

    def test_real_fixture_amazon(self):
        assert _ct("UNREAL AMAZON – Nature's Most Dangerous Paradise (Full Documentary)", length=4455) == ContentType.DOCUMENTARY

    def test_real_fixture_our_planet(self):
        result = _ct("Our Planet | Forests | FULL EPISODE | Netflix", length=2820)
        assert result != ContentType.DOCUMENTARY

    def test_nature_video_without_keyword(self):
        result = _ct("The Incredible Wildlife of Hidden Forests | BBC Earth", length=5346)
        assert result == ContentType.VIDEO


# ===========================================================================
# AUDIOBOOK
# ===========================================================================

class TestAudiobook:
    # single-narrator readings
    def test_audiobook_keyword(self):
        assert _ct("Harry Potter Audiobook - Full Book") == ContentType.AUDIOBOOK

    def test_audiobook_keyword_alt(self):
        assert _ct("1984 by George Orwell — Full Audiobook") == ContentType.AUDIOBOOK

    def test_full_audio_book(self):
        assert _ct("Dune Full Audio Book (Unabridged)") == ContentType.AUDIOBOOK

    def test_read_aloud(self):
        assert _ct("Charlotte's Web - Read Aloud") == ContentType.AUDIOBOOK

    def test_read_aloud_alt(self):
        assert _ct("Harry Potter and the Philosopher's Stone — Read Aloud") == ContentType.AUDIOBOOK

    def test_narrated_by(self):
        assert _ct("1984 Narrated by Stephen Fry") == ContentType.AUDIOBOOK

    def test_narrated_by_wayne_june(self):
        assert _ct("At the Mountains of Madness narrated by Wayne June") == ContentType.AUDIOBOOK

    def test_case_insensitive(self):
        assert _ct("GREAT GATSBY AUDIOBOOK") == ContentType.AUDIOBOOK

    def test_description_audiobook(self):
        assert _ct("Free Classic Literature", description="full audiobook narrated by") == ContentType.AUDIOBOOK

    # full-cast audio dramas / radio plays
    def test_audio_drama(self):
        assert _ct("Doctor Who: Audio Drama — The Chimes of Midnight") == ContentType.AUDIOBOOK

    def test_audio_play(self):
        assert _ct("Hamlet — Full Cast Audio Play") == ContentType.AUDIOBOOK

    def test_radio_play(self):
        assert _ct("The Hitchhiker's Guide — Original BBC Radio Play") == ContentType.AUDIOBOOK

    def test_radiodrama(self):
        assert _ct("War of the Worlds Radiodrama 1938") == ContentType.AUDIOBOOK

    def test_full_cast_audio(self):
        assert _ct("Good Omens Full Cast Audio Production") == ContentType.AUDIOBOOK

    def test_dramatized(self):
        assert _ct("Sherlock Holmes — Dramatized by the BBC") == ContentType.AUDIOBOOK

    # priority checks
    def test_audiobook_beats_music_video(self):
        result = _ct("Song Audiobook (Official Music Video)", is_official_artist=False)
        assert result == ContentType.AUDIOBOOK

    def test_audiobook_after_documentary(self):
        result = _ct("Documentary Audiobook Study")
        assert result == ContentType.DOCUMENTARY

    # negative
    def test_not_audiobook_without_keyword(self):
        assert _ct("The Great Gatsby", length=7200) != ContentType.AUDIOBOOK

    def test_not_audiobook_story_alone(self):
        assert _ct("Sherlock Holmes Story") != ContentType.AUDIOBOOK


# ===========================================================================
# PODCAST — publisher-defined only (is_podcast=True)
# ===========================================================================

class TestPodcast:
    def test_publisher_defined_flag(self):
        assert _ct("Episode Title", is_podcast=True) == ContentType.PODCAST

    def test_title_alone_no_longer_triggers_podcast(self):
        # Regex-based podcast detection is removed; title keywords alone won't classify as PODCAST
        assert _ct("Lex Fridman Podcast #400") != ContentType.PODCAST

    def test_podcast_keyword_in_title_is_just_video(self):
        assert _ct("My Podcast Episode 5") != ContentType.PODCAST

    def test_is_podcast_flag_beats_music_video(self):
        # podcast priority is below documentary/movie/trailer/audiobook but above music_video
        result = _ct("Official Music Video Podcast", is_podcast=True)
        assert result == ContentType.PODCAST

    def test_movie_beats_podcast_flag(self):
        result = _ct("Full Movie", length=7200, is_podcast=True)
        assert result == ContentType.MOVIE

    def test_documentary_beats_podcast_flag(self):
        result = _ct("A Documentary", is_podcast=True)
        assert result == ContentType.DOCUMENTARY

    def test_audiobook_beats_podcast_flag(self):
        result = _ct("Full Audiobook", is_podcast=True)
        assert result == ContentType.AUDIOBOOK

    def test_live_beats_podcast_flag(self):
        result = _ct("Episode 5", is_podcast=True, is_live=True)
        assert result == ContentType.LIVE


# ===========================================================================
# Channel-tag enrichment
# ===========================================================================

class TestChannelTags:
    def test_movie_channel_tag_without_title_keyword(self):
        # No "full movie" in title, but channel is tagged as a movie channel
        result = _ct("Inception (2010) HD", length=7200, channel_tags=["full movies", "classic films"])
        assert result == ContentType.MOVIE

    def test_movie_channel_tag_classic_films(self):
        result = _ct("The Dark Knight", length=9000, channel_tags=["classic films", "movie channel"])
        assert result == ContentType.MOVIE

    def test_movie_channel_tag_still_needs_duration(self):
        # Channel tagged as movies, but video is too short → not MOVIE
        result = _ct("Clip from Movie", length=120, channel_tags=["movies"])
        assert result != ContentType.MOVIE

    def test_movie_channel_tag_unknown_duration_allowed(self):
        result = _ct("Classic Film", length=0, channel_tags=["full movie"])
        assert result == ContentType.MOVIE

    def test_doc_channel_tag(self):
        result = _ct("Africa Episode 3", length=3600, channel_tags=["documentary", "nature"])
        assert result == ContentType.DOCUMENTARY

    def test_doc_channel_tag_nature(self):
        result = _ct("Rainforest Special", length=2700, channel_tags=["nature"])
        assert result == ContentType.DOCUMENTARY

    def test_doc_channel_tag_history(self):
        result = _ct("WWII Untold Stories", length=3600, channel_tags=["history"])
        assert result == ContentType.DOCUMENTARY

    def test_music_channel_tag_no_title_keyword(self):
        result = _ct("Track Name - Artist", length=240, channel_tags=["music", "artist"])
        assert result == ContentType.MUSIC_VIDEO

    def test_channel_tags_none_is_ok(self):
        result = _ct("Generic Video", channel_tags=None)
        assert result == ContentType.VIDEO

    def test_channel_tags_empty_is_ok(self):
        result = _ct("Generic Video", channel_tags=[])
        assert result == ContentType.VIDEO

    def test_channel_tag_case_insensitive(self):
        result = _ct("Movie Title", length=7200, channel_tags=["Classic Movies", "Movie Channel"])
        assert result == ContentType.MOVIE

    def test_movie_title_beats_doc_channel_tag(self):
        # "full movie" in title triggers MOVIE before channel_tags check runs for doc
        result = _ct("Full Movie Documentary", length=7200, channel_tags=["documentary"])
        assert result == ContentType.MOVIE


# ===========================================================================
# MUSIC_VIDEO
# ===========================================================================

class TestMusicVideo:
    def test_official_music_video(self):
        assert _ct("Rob Zombie - Dragula (Official Music Video)") == ContentType.MUSIC_VIDEO

    def test_official_video(self):
        assert _ct("Metallica: Enter Sandman (Official Music Video)") == ContentType.MUSIC_VIDEO

    def test_official_video_short(self):
        assert _ct("BLACK SABBATH - 'Paranoid' (Official Video)") == ContentType.MUSIC_VIDEO

    def test_omv_acronym(self):
        assert _ct("Artist - Song (OMV)") == ContentType.MUSIC_VIDEO

    def test_heathen_days_from_fixture(self):
        assert _ct("ROB ZOMBIE - Heathen Days (OFFICIAL MUSIC VIDEO)", length=140) == ContentType.MUSIC_VIDEO

    def test_official_artist_no_title_keyword(self):
        assert _ct("Rob Zombie - Dragula", length=228, is_official_artist=True) == ContentType.MUSIC_VIDEO

    def test_official_artist_beats_music_audio_pattern(self):
        result = _ct("Billie Eilish - Bored (Official Audio)", length=179, is_official_artist=True)
        assert result == ContentType.MUSIC_VIDEO  # OAC overrides MUSIC_AUDIO

    def test_official_artist_beats_lyric_video_pattern(self):
        result = _ct("Billie Eilish - BIRDS OF A FEATHER (Official Lyric Video)", length=212, is_official_artist=True)
        assert result == ContentType.MUSIC_VIDEO

    def test_remastered_track_from_oac(self):
        assert _ct("Paranoid (2012 Remaster)", length=167, is_official_artist=True) == ContentType.MUSIC_VIDEO

    def test_full_album_from_oac(self):
        # "Full Album" keyword → MUSIC_AUDIO, even from an OAC; full album title wins over artist badge
        assert _ct("BLACK SABBATH - Paranoid (Full Album)", length=5010, is_official_artist=True) == ContentType.MUSIC_AUDIO

    def test_real_metallica_official_music_video(self):
        assert _ct(
            "Metallica: Nothing Else Matters (Official Music Video)",
            length=387, is_official_artist=True
        ) == ContentType.MUSIC_VIDEO

    def test_fan_made_music_video_no_keyword(self):
        result = _ct("Rob Zombie - Dragula (Live @ Ozzfest 2005)", length=329)
        assert result == ContentType.VIDEO

    def test_no_artist_flag_no_title_match(self):
        result = _ct("Artist - Some Song", length=200)
        assert result == ContentType.VIDEO


# ===========================================================================
# MUSIC_AUDIO
# ===========================================================================

class TestMusicAudio:
    def test_official_audio(self):
        assert _ct("Billie Eilish - idontwannabeyouanymore (Official Audio)", length=204) == ContentType.MUSIC_AUDIO

    def test_official_audio_from_fixture(self):
        assert _ct("Black Sabbath - Paranoid (Official Audio)", length=169) == ContentType.MUSIC_AUDIO

    def test_lyric_video(self):
        assert _ct("The Weeknd - Blinding Lights (Lyrics Video)") == ContentType.MUSIC_AUDIO

    def test_lyric_video_no_s(self):
        assert _ct("Artist - Song (Lyric Video)") == ContentType.MUSIC_AUDIO

    def test_lyric_video_from_fixture(self):
        assert _ct("Billie Eilish - BIRDS OF A FEATHER (Official Lyric Video)", length=212, is_official_artist=False) == ContentType.MUSIC_AUDIO

    def test_visualizer(self):
        assert _ct("Tame Impala - Let It Happen (Visualizer)") == ContentType.MUSIC_AUDIO

    def test_visualiser_british_spelling(self):
        assert _ct("Artist - Track (Visualiser)") == ContentType.MUSIC_AUDIO

    def test_auto_generated(self):
        assert _ct("Track Name (Auto-generated by YouTube)") == ContentType.MUSIC_AUDIO

    def test_auto_generated_no_hyphen(self):
        assert _ct("Track Name (Auto generated)") == ContentType.MUSIC_AUDIO

    def test_music_audio_not_reached_for_oac(self):
        result = _ct("Song (Official Audio)", length=200, is_official_artist=True)
        assert result == ContentType.MUSIC_VIDEO

    def test_paranoid_lyrics_is_just_video(self):
        result = _ct("BLACK SABBATH - Paranoid (Lyrics)", length=167)
        assert result == ContentType.VIDEO


# ===========================================================================
# Default VIDEO — nothing matches
# ===========================================================================

class TestDefaultVideo:
    def test_generic_how_to(self):
        assert _ct("How to Cook Pasta", length=900) == ContentType.TUTORIAL

    def test_generic_commentary(self):
        assert _ct("My Thoughts on the New iPhone", length=600) == ContentType.VIDEO

    def test_empty_title(self):
        assert _ct("", length=300) == ContentType.VIDEO

    def test_live_concert_no_keywords(self):
        assert _ct("Metallica - Enter Sandman Live Moscow 1991 HD", length=374) == ContentType.VIDEO

    def test_lyrics_cover_no_keyword(self):
        assert _ct("Black Sabbath - Paranoid (Lyrics)", length=167) == ContentType.VIDEO

    def test_full_concert_classifies_as_concert(self):
        # "full concert" → CONCERT, not VIDEO
        assert _ct("Metallica - Live in Moscow 1991 [Full Concert] | Remastered 4K 60FPS", length=4639) == ContentType.CONCERT


# ===========================================================================
# TV_EPISODE
# ===========================================================================

class TestTVEpisode:
    def test_s01e02_format(self):
        assert _ct("Breaking Bad S01E02") == ContentType.TV_EPISODE

    def test_season_episode_words(self):
        assert _ct("Game of Thrones Season 3 Episode 9") == ContentType.TV_EPISODE

    def test_full_episode(self):
        assert _ct("How Native Americans Read the Stars | Full Episode | Native America") == ContentType.TV_EPISODE

    def test_case_insensitive(self):
        assert _ct("my show s2e5 recap") == ContentType.TV_EPISODE

    def test_not_tv_episode_without_marker(self):
        assert _ct("Breaking Bad — best scenes", length=600) != ContentType.TV_EPISODE

    def test_documentary_beats_tv_episode(self):
        # "Full Episode" in a documentary context — doc fires first
        result = _ct("Planet Earth Full Episode Documentary", length=2700)
        assert result == ContentType.DOCUMENTARY


# ===========================================================================
# SHORT_FILM
# ===========================================================================

class TestShortFilm:
    def test_short_film_keyword(self):
        assert _ct("Sci-Fi Short Film: The Beacon | DUST", length=900) == ContentType.SHORT_FILM

    def test_short_movie_keyword(self):
        assert _ct("Award-Winning Short Movie") == ContentType.SHORT_FILM

    def test_case_insensitive(self):
        assert _ct("AWARD-WINNING SHORT FILM 2023") == ContentType.SHORT_FILM

    def test_short_film_channel_tag(self):
        result = _ct("In a World Where Everyone Is Invisible", channel_tags=["short film", "sci-fi"])
        assert result == ContentType.SHORT_FILM

    def test_short_film_not_youtube_short(self):
        # YouTube Short (< 62s) takes priority over SHORT_FILM keyword
        assert _ct("Quick Short Film", length=45) == ContentType.SOCIAL_CLIP

    def test_feature_length_short_film_rejected(self):
        # "short film" in title but 2+ hours → probably mislabeled; SHORT_FILM requires < 60 min
        result = _ct("This Short Film Changed Cinema", length=7200)
        assert result != ContentType.SHORT_FILM

    def test_short_film_unknown_duration_allowed(self):
        assert _ct("My Short Film Entry", length=0) == ContentType.SHORT_FILM

    def test_short_film_tag_overrides_movie_tag(self):
        # Channel has movie-like and short-film tags; SHORT_FILM wins over MOVIE
        result = _ct("The Endless Road", channel_tags=["short film", "cinema"])
        assert result == ContentType.SHORT_FILM


# ===========================================================================
# INTERVIEW
# ===========================================================================

class TestInterview:
    def test_interview_with(self):
        assert _ct("Interview with Elon Musk") == ContentType.INTERVIEW

    def test_in_conversation_with(self):
        assert _ct("In Conversation with Noam Chomsky", length=3600) == ContentType.INTERVIEW

    def test_talks_with(self):
        assert _ct("Obama Talks with David Letterman") == ContentType.INTERVIEW

    def test_talks_to(self):
        assert _ct("Senator Talks to Press About Policy") == ContentType.INTERVIEW

    def test_sits_down_with(self):
        assert _ct("CEO Sits Down with Bloomberg") == ContentType.INTERVIEW

    def test_bare_interview_no_with(self):
        # "interview" alone without "with" should NOT match (too generic)
        assert _ct("Tech Interview Prep Course", length=600) != ContentType.INTERVIEW

    def test_documentary_beats_interview(self):
        # "Talks with" + "documentary" in title → DOCUMENTARY fires first
        result = _ct("A Documentary: Talks with Survivors", length=3600)
        assert result == ContentType.DOCUMENTARY


# ===========================================================================
# LECTURE
# ===========================================================================

class TestLecture:
    def test_lecture_keyword(self):
        assert _ct("MIT Lecture: Introduction to Algorithms", length=3600) == ContentType.LECTURE

    def test_ted_talk(self):
        assert _ct("TED Talk: The Power of Vulnerability") == ContentType.LECTURE

    def test_tedx(self):
        assert _ct("Why We Do What We Do | TEDx Boston") == ContentType.LECTURE

    def test_masterclass(self):
        assert _ct("Gordon Ramsay Masterclass: Cooking Fundamentals") == ContentType.LECTURE

    def test_open_course(self):
        assert _ct("Open Course: Machine Learning 101") == ContentType.LECTURE

    def test_online_course(self):
        assert _ct("Online Course Introduction — Python Basics") == ContentType.LECTURE

    def test_lecture_not_triggered_by_ted_as_name(self):
        # "Ted" as a first name should not trigger (no "Talk" or "x" suffix)
        assert _ct("Ted's Birthday Party Planning Tips") != ContentType.LECTURE

    def test_tedx_triggers_lecture(self):
        assert _ct("TEDx: Rethinking Education") == ContentType.LECTURE


# ===========================================================================
# CONCERT
# ===========================================================================

class TestConcert:
    def test_full_concert(self):
        assert _ct("Metallica - Live in Moscow 1991 [Full Concert]", length=4639) == ContentType.CONCERT

    def test_full_show(self):
        assert _ct("Pink Floyd Full Show at Pompeii", length=5400) == ContentType.CONCERT

    def test_full_performance(self):
        assert _ct("Beyoncé Full Performance at Coachella", length=5400) == ContentType.CONCERT

    def test_live_at_venue(self):
        assert _ct("Led Zeppelin Live at Madison Square Garden", length=7200) == ContentType.CONCERT

    def test_in_concert(self):
        assert _ct("Bob Dylan In Concert - Complete Set", length=4800) == ContentType.CONCERT

    def test_concert_film(self):
        assert _ct("Stop Making Sense — Concert Film (1984)", length=5400) == ContentType.CONCERT

    def test_live_at_no_venue_is_not_concert(self):
        # "live" alone without a venue/context should not match
        assert _ct("Rob Zombie Live (Official Video)", length=300) != ContentType.CONCERT

    def test_movie_beats_concert_if_full_movie_keyword(self):
        result = _ct("Full Movie Concert Film", length=7200)
        assert result == ContentType.MOVIE


# EDUCATIONAL removed — was channel-tag only with no title pattern; too vague.


# ===========================================================================
# Priority ordering — explicit cross-type scenarios
# ===========================================================================

class TestPriority:
    """Verify the documented priority chain:
    live > upcoming > short > trailer > movie(title) > documentary > tv_episode >
    short_film > movie(tag) > audiobook > podcast > lecture > interview > concert >
    educational(tag) > music_video > music_audio > video."""

    def test_short_beats_trailer(self):
        assert _ct("Quick Official Trailer", length=30) == ContentType.SOCIAL_CLIP

    def test_short_beats_documentary(self):
        assert _ct("Short Documentary Clip", length=45) == ContentType.SOCIAL_CLIP

    def test_short_beats_podcast(self):
        assert _ct("Episode Teaser", length=55, is_podcast=True) == ContentType.SOCIAL_CLIP

    def test_trailer_beats_movie(self):
        result = _ct("Official Trailer - Full Movie Preview", length=150)
        assert result == ContentType.TRAILER

    def test_movie_beats_documentary(self):
        result = _ct("Full Movie Documentary Style", length=7200)
        assert result == ContentType.MOVIE

    def test_movie_beats_podcast(self):
        result = _ct("Full Movie", length=7200, is_podcast=True)
        assert result == ContentType.MOVIE

    def test_documentary_beats_podcast(self):
        result = _ct("A Documentary", length=3600, is_podcast=True)
        assert result == ContentType.DOCUMENTARY

    def test_documentary_beats_music_video(self):
        result = _ct("Official Music Video Documentary", length=3600, is_official_artist=False)
        assert result == ContentType.DOCUMENTARY

    def test_audiobook_beats_podcast(self):
        result = _ct("Full Audiobook Read Aloud", is_podcast=True)
        assert result == ContentType.AUDIOBOOK

    def test_audiobook_beats_music_video(self):
        result = _ct("Audiobook Official Music Video", is_official_artist=False)
        assert result == ContentType.AUDIOBOOK

    def test_podcast_beats_music_video(self):
        result = _ct("Official Music Video", length=3600, is_podcast=True)
        assert result == ContentType.PODCAST

    def test_official_artist_with_movie_keyword_is_still_movie(self):
        result = _ct("My Full Movie", length=7200, is_official_artist=True)
        assert result == ContentType.MOVIE


# ===========================================================================
# Duration boundary conditions
# ===========================================================================

class TestDurationBoundaries:
    def test_short_upper_bound_61(self):
        assert _ct("clip", length=61) == ContentType.SOCIAL_CLIP

    def test_not_short_at_62(self):
        assert _ct("clip", length=62) != ContentType.SOCIAL_CLIP

    def test_movie_lower_bound_3600(self):
        assert _ct("Watch Full Movie", length=3600) == ContentType.MOVIE

    def test_movie_below_bound_3599(self):
        assert _ct("Watch Full Movie", length=3599) != ContentType.MOVIE

    def test_movie_at_zero_accepted(self):
        assert _ct("Watch Full Movie", length=0) == ContentType.MOVIE

    def test_very_long_video_with_keyword(self):
        assert _ct("The Godfather Full Film", length=10800) == ContentType.MOVIE

    def test_trailer_hard_limit_at_600(self):
        assert _ct("Official Trailer Extended", length=600) == ContentType.TRAILER

    def test_trailer_hard_limit_at_601_becomes_video(self):
        result = _ct("Official Trailer Extended", length=601)
        assert result != ContentType.TRAILER

    def test_trailer_unknown_duration_ok(self):
        assert _ct("Official Trailer", length=0) == ContentType.TRAILER


# ===========================================================================
# Fixture-based integration: real VideoPreview.content_type property
# ===========================================================================

class TestFixtureClassification:
    """Verify content_type on real VideoPreview objects from recorded fixtures."""

    def test_rob_zombie_official_artist_are_music_videos(self, patch_innertube):
        from tutubo import YoutubeSearch
        vs = list(YoutubeSearch("rob zombie").iterate_videos(max_res=15))
        oac = [v for v in vs if v.is_official_artist_channel]
        assert len(oac) >= 2
        for v in oac:
            assert v.content_type == ContentType.MUSIC_VIDEO, (
                f"OAC video misclassified as {v.content_type}: {v.title!r}"
            )

    def test_full_movie_search_classifies_movies(self, patch_innertube):
        from tutubo import YoutubeSearch
        vs = list(YoutubeSearch("full movie free 2023").iterate_videos(max_res=20))
        movies = [v for v in vs if v.content_type == ContentType.MOVIE]
        assert len(movies) >= 3

    def test_official_trailer_search_has_trailers(self, patch_innertube):
        from tutubo import YoutubeSearch
        vs = list(YoutubeSearch("official trailer 2024").iterate_videos(max_res=20))
        trailers = [v for v in vs if v.content_type == ContentType.TRAILER]
        assert len(trailers) >= 5

    def test_trailer_search_short_duration(self, patch_innertube):
        from tutubo import YoutubeSearch
        vs = list(YoutubeSearch("official trailer 2024").iterate_videos(max_res=20))
        trailers = [v for v in vs if v.content_type == ContentType.TRAILER]
        for t in trailers:
            assert t.length < 600, f"Trailer too long ({t.length}s): {t.title!r}"

    def test_documentary_search_has_documentaries(self, patch_innertube):
        from tutubo import YoutubeSearch
        vs = list(YoutubeSearch("nature documentary full").iterate_videos(max_res=20))
        docs = [v for v in vs if v.content_type == ContentType.DOCUMENTARY]
        assert len(docs) >= 2

    def test_lofi_live_streams_classified_live(self, patch_innertube):
        from tutubo import YoutubeSearch
        vs = list(YoutubeSearch("lofi hip hop").iterate_videos(max_res=20))
        live = [v for v in vs if v.is_live]
        assert len(live) >= 2
        live_types = {ContentType.LIVE, ContentType.LIVE_RADIO, ContentType.LIVE_NEWS, ContentType.IPTV}
        for v in live:
            assert v.content_type in live_types, (
                f"Live stream misclassified as {v.content_type}: {v.title!r}"
            )

    def test_black_sabbath_official_audio_is_music_audio(self, patch_innertube):
        from tutubo import YoutubeSearch
        vs = list(YoutubeSearch("black sabbath paranoid").iterate_videos(max_res=20))
        audio = next(
            (v for v in vs if "Official Audio" in (v.title or "")),
            None
        )
        assert audio is not None, "Expected an 'Official Audio' result"
        if not audio.is_official_artist_channel:
            assert audio.content_type == ContentType.MUSIC_AUDIO

    def test_content_type_is_always_valid_enum(self, patch_innertube):
        from tutubo import YoutubeSearch
        for query in ["rob zombie", "full movie free 2023", "official trailer 2024"]:
            for v in YoutubeSearch(query).iterate_videos(max_res=10):
                assert isinstance(v.content_type, ContentType), (
                    f"content_type is not a ContentType: {v.content_type!r}"
                )

    def test_content_type_serialises_as_string(self, patch_innertube):
        import json
        from tutubo import YoutubeSearch
        vs = list(YoutubeSearch("rob zombie").iterate_videos(max_res=3))
        for v in vs:
            d = v.as_dict
            assert isinstance(d["content_type"], str)
            json.dumps(d)


# ===========================================================================
# Behind the scenes
# ===========================================================================

class TestBehindTheScenes:
    def test_making_of(self):
        assert _ct("Making-of: The Dark Knight") == ContentType.BEHIND_THE_SCENES

    def test_bloopers(self):
        assert _ct("Avengers Bloopers 2023") == ContentType.BEHIND_THE_SCENES

    def test_on_set(self):
        assert _ct("On-Set with the Cast of Dune") == ContentType.BEHIND_THE_SCENES

    def test_featurette(self):
        assert _ct("Exclusive Featurette — The Making of Oppenheimer") == ContentType.BEHIND_THE_SCENES

    def test_behind_the_scenes(self):
        assert _ct("Behind the Scenes of Interstellar") == ContentType.BEHIND_THE_SCENES

    def test_not_bts_just_movie(self):
        assert _ct("Full Movie: The Dark Knight", length=9000) == ContentType.MOVIE

    def test_docuseries_beats_making_of(self):
        # "docuseries" is a stronger documentary signal than "making of"
        assert _ct("Making Of: A Docuseries") == ContentType.DOCUMENTARY


# ===========================================================================
# Anime
# ===========================================================================

class TestAnime:
    def test_anime_keyword(self):
        assert _ct("Attack on Titan Anime Season 4") == ContentType.ANIME

    def test_anime_case_insensitive(self):
        assert _ct("ANIME Full Episode — Naruto S01E01") == ContentType.ANIME

    def test_anime_channel_tag(self):
        assert _ct("One Piece Episode 1000", channel_tags=["anime", "manga"]) == ContentType.ANIME

    def test_anime_japanese_tag(self):
        assert _ct("Dragon Ball Super Episode 5", channel_tags=["アニメ"]) == ContentType.ANIME

    def test_non_anime_no_tag(self):
        # "Episode 5" alone doesn't trigger TV_EPISODE (needs S01E02 / Season X Episode Y / Full Episode)
        result = _ct("Dragon Ball Super Episode 5")
        assert result == ContentType.VIDEO


# ===========================================================================
# Stand-up comedy
# ===========================================================================

class TestStandUp:
    def test_standup_comedy_special(self):
        assert _ct("Dave Chappelle: Stand-Up Comedy Special") == ContentType.STAND_UP

    def test_comedy_special(self):
        assert _ct("John Mulaney: Baby J — Comedy Special") == ContentType.STAND_UP

    def test_comedy_hour(self):
        assert _ct("Gabriel Iglesias: Comedy Hour") == ContentType.STAND_UP

    def test_comedy_tour(self):
        assert _ct("Kevin Hart: Irresponsible Comedy Tour") == ContentType.STAND_UP

    def test_standup_no_type_word(self):
        result = _ct("Stand-Up Night at the Apollo")
        assert result == ContentType.STAND_UP


# ===========================================================================
# News
# ===========================================================================

class TestNews:
    def test_breaking_news(self):
        assert _ct("Breaking News: Earthquake Hits Turkey") == ContentType.NEWS

    def test_news_report(self):
        assert _ct("BBC News Report — Climate Summit") == ContentType.NEWS

    def test_news_briefing(self):
        assert _ct("Daily News Briefing — March 2024") == ContentType.NEWS

    def test_news_channel_tag(self):
        assert _ct("Tonight's Top Stories", channel_tags=["news", "journalism"]) == ContentType.NEWS

    def test_breaking_news_channel_tag(self):
        assert _ct("Live Coverage", channel_tags=["breaking news"]) == ContentType.NEWS

    def test_no_false_positive_on_generic(self):
        result = _ct("My Year in Review")
        assert result not in (ContentType.NEWS,)


# ===========================================================================
# Sport
# ===========================================================================

class TestSport:
    def test_full_match(self):
        assert _ct("Manchester United vs Arsenal — Full Match") == ContentType.SPORT

    def test_game_highlights(self):
        assert _ct("NBA Game Highlights — Lakers vs Celtics") == ContentType.SPORT

    def test_match_highlights(self):
        assert _ct("Champions League Match Highlights 2024") == ContentType.SPORT

    def test_game_recap(self):
        assert _ct("NFL Playoff Game Recap — Chiefs vs Ravens") == ContentType.SPORT

    def test_sport_channel_tag(self):
        assert _ct("Sunday's Best Plays", channel_tags=["nfl", "sports"]) == ContentType.SPORT

    def test_full_race(self):
        assert _ct("Monaco Grand Prix — Full Race 2023") == ContentType.SPORT


# ===========================================================================
# Gaming
# ===========================================================================

class TestGaming:
    def test_gameplay(self):
        assert _ct("Elden Ring Gameplay — First Boss Fight") == ContentType.GAMING

    def test_lets_play(self):
        assert _ct("Let's Play Minecraft — Episode 12") == ContentType.GAMING

    def test_lets_play_alternate_apostrophe(self):
        assert _ct("Lets Play Stardew Valley") == ContentType.GAMING

    def test_playthrough(self):
        assert _ct("God of War Complete Playthrough") == ContentType.GAMING

    def test_gaming_channel_tag(self):
        assert _ct("New Video!", channel_tags=["gaming", "gamer"]) == ContentType.GAMING

    def test_esports_channel_tag(self):
        assert _ct("Tournament Highlights", channel_tags=["esports"]) == ContentType.GAMING


# ===========================================================================
# Tutorial
# ===========================================================================

class TestTutorial:
    def test_tutorial_keyword(self):
        assert _ct("Python Pandas Tutorial for Beginners") == ContentType.TUTORIAL

    def test_how_to(self):
        assert _ct("How to Cook Perfect Risotto") == ContentType.TUTORIAL

    def test_how_to_hyphen(self):
        assert _ct("How-to: Set Up a Home Server") == ContentType.TUTORIAL

    def test_diy(self):
        assert _ct("DIY Bookshelf from Pallet Wood") == ContentType.TUTORIAL

    def test_step_by_step(self):
        assert _ct("Step-by-Step Guide to Sourdough Bread") == ContentType.TUTORIAL


# ===========================================================================
# Reaction
# ===========================================================================

class TestReaction:
    def test_reaction_to(self):
        assert _ct("My Reaction to Billie Eilish's New Album") == ContentType.REACTION

    def test_reaction_video(self):
        assert _ct("Stranger Things S4 Finale — Reaction Video") == ContentType.REACTION

    def test_reacting_to(self):
        assert _ct("Reacting to the Funniest TikToks") == ContentType.REACTION

    def test_first_time_watching(self):
        assert _ct("First Time Watching Pulp Fiction!") == ContentType.REACTION

    def test_first_time_listening(self):
        assert _ct("First Time Listening to Led Zeppelin") == ContentType.REACTION


# ===========================================================================
# Compilation
# ===========================================================================

class TestCompilation:
    def test_compilation(self):
        assert _ct("Best Goals Compilation 2023") == ContentType.COMPILATION

    def test_best_of(self):
        assert _ct("Best of Gordon Ramsay Kitchen Nightmares") == ContentType.COMPILATION

    def test_top_n(self):
        assert _ct("Top 10 Scariest Horror Movies") == ContentType.COMPILATION

    def test_top_5(self):
        assert _ct("Top 5 Guitar Solos of All Time") == ContentType.COMPILATION

    def test_top_100(self):
        assert _ct("Top 100 Classic Rock Songs") == ContentType.COMPILATION


# ===========================================================================
# Kids
# ===========================================================================

class TestKids:
    def test_for_kids(self):
        assert _ct("Learn Colors for Kids — Fun Cartoon") == ContentType.KIDS

    def test_for_toddlers(self):
        assert _ct("ABC Song for Toddlers") == ContentType.KIDS

    def test_nursery_rhymes(self):
        assert _ct("Nursery Rhymes Collection — Baby Songs") == ContentType.KIDS

    def test_kids_cartoon(self):
        assert _ct("Peppa Pig Kids Cartoon") == ContentType.KIDS

    def test_childrens_song(self):
        assert _ct("Children's Song: Wheels on the Bus") == ContentType.KIDS

    def test_kids_channel_tag(self):
        assert _ct("Episode 12", channel_tags=["kids", "preschool"]) == ContentType.KIDS

    def test_nursery_rhyme_channel_tag(self):
        assert _ct("New Video", channel_tags=["nursery rhymes", "baby songs"]) == ContentType.KIDS

    def test_kids_music_video_stays_kids(self):
        # kids signal fires before music_video in priority chain
        result = _ct("Kids Song: Baby Shark Official Video", channel_tags=["kids"])
        assert result == ContentType.KIDS


# SILENT_FILM and BLACK_AND_WHITE removed — incomplete coverage without metadata.


# ===========================================================================
# Live radio
# ===========================================================================

class TestLiveRadio:
    def test_radio_stream(self):
        assert _ct("lofi hip hop radio – beats to relax/study to", is_live=True) == ContentType.LIVE_RADIO

    def test_24_7_radio(self):
        assert _ct("24/7 Jazz Radio — Classic Smooth Jazz", is_live=True) == ContentType.LIVE_RADIO

    def test_fm_radio(self):
        assert _ct("BBC Radio 4 FM Live Stream", is_live=True) == ContentType.LIVE_RADIO

    def test_24_7_music(self):
        assert _ct("24/7 Music — Chill Beats Non-Stop", is_live=True) == ContentType.LIVE_RADIO

    def test_not_radio_if_not_live(self):
        # A recorded radio show wouldn't be classified LIVE_RADIO without is_live=True
        result = _ct("Radio Show Episode 12")
        assert result != ContentType.LIVE_RADIO


# ===========================================================================
# Live news
# ===========================================================================

class TestLiveNews:
    def test_live_news(self):
        assert _ct("BBC Live News — Breaking Coverage", is_live=True) == ContentType.LIVE_NEWS

    def test_news_live(self):
        assert _ct("CNN News Live", is_live=True) == ContentType.LIVE_NEWS

    def test_24_7_news(self):
        assert _ct("24/7 News — Latest Updates", is_live=True) == ContentType.LIVE_NEWS

    def test_live_news_stream(self):
        assert _ct("Al Jazeera Live News Stream", is_live=True) == ContentType.LIVE_NEWS

    def test_live_news_beats_iptv(self):
        # Live news is more specific than generic IPTV
        result = _ct("Sky News Live", is_live=True)
        assert result == ContentType.LIVE_NEWS


# ===========================================================================
# IPTV / live TV (non-news)
# ===========================================================================

class TestIPTV:
    def test_live_tv(self):
        assert _ct("CNN Live TV Stream", is_live=True) == ContentType.IPTV

    def test_iptv_keyword(self):
        assert _ct("IPTV Free Channels Playlist", is_live=True) == ContentType.IPTV

    def test_24_7_tv(self):
        assert _ct("24/7 TV — Movies and Shows", is_live=True) == ContentType.IPTV

    def test_generic_live_not_tv(self):
        # Concert live stream → LIVE (not IPTV)
        result = _ct("Metallica Live Concert Stream — Download Festival", is_live=True)
        assert result == ContentType.LIVE


# ===========================================================================
# extract_tags — freeform label extraction
# ===========================================================================

from tutubo.content_type import extract_tags


class TestExtractTags:
    def test_horror_genre(self):
        assert "horror" in extract_tags("Top 10 Scariest Horror Movies")

    def test_sci_fi_genre(self):
        assert "sci-fi" in extract_tags("Best Sci-Fi Films of the Decade")

    def test_narrated_sub_label(self):
        assert "narrated" in extract_tags("Lovecraft narrated by Wayne June")

    def test_wayne_june_tag(self):
        assert "wayne-june" in extract_tags("At the Mountains of Madness narrated by Wayne June")

    def test_lovecraft_tag(self):
        assert "lovecraft" in extract_tags("H.P. Lovecraft — The Shadow over Innsmouth")

    def test_full_cast_tag(self):
        assert "full-cast" in extract_tags("Good Omens — Full Cast Audio Production")

    def test_radio_play_tag(self):
        assert "radio-play" in extract_tags("Sherlock Holmes BBC Radio Play")

    def test_classic_tag(self):
        assert "classic" in extract_tags("Nosferatu 1922 Restored 4K")

    def test_4k_tag(self):
        assert "4k" in extract_tags("Casablanca 4K UHD Remaster")

    def test_football_sport(self):
        assert "football" in extract_tags("Premier League Full Match Highlights")

    def test_motorsport_tag(self):
        assert "motorsport" in extract_tags("F1 2024 Full Race Monaco Grand Prix")

    def test_electronic_music(self):
        assert "electronic" in extract_tags("Lo-Fi Hip Hop Radio - Beats to Study/Relax")

    def test_hip_hop_music(self):
        assert "hip-hop" in extract_tags("Best Hip-Hop Rap Mixtape 2024")

    def test_kids_audience(self):
        assert "kids" in extract_tags("Baby Shark | Nursery Rhymes for Kids")

    def test_ted_talk_tag(self):
        assert "ted-talk" in extract_tags("TED Talk: How Great Leaders Inspire Action")

    def test_no_false_positives(self):
        tags = extract_tags("Rob Zombie — Dragula (Official Music Video)")
        assert "horror" not in tags  # "Zombie" alone doesn't trigger horror
        assert "kids" not in tags

    def test_multiple_tags(self):
        tags = extract_tags("Top 10 Scariest Horror Sci-Fi Films — 4K Restored Classic")
        assert "horror" in tags
        assert "sci-fi" in tags
        assert "4k" in tags
        assert "classic" in tags

    def test_returns_sorted_list(self):
        tags = extract_tags("Horror Sci-Fi Thriller Full Movie")
        assert tags == sorted(tags)

    def test_empty_title(self):
        assert extract_tags("") == []

    def test_description_used(self):
        tags = extract_tags("Untitled Video", description="narrated by the author — for kids")
        assert "narrated" in tags
        assert "kids" in tags

    def test_tags_on_video_preview(self, patch_innertube):
        from tutubo import YoutubeSearch
        v = list(YoutubeSearch("lovecraft narrated by wayne june").iterate_videos(max_res=1))[0]
        assert isinstance(v.tags, list)
        assert "narrated" in v.tags or "lovecraft" in v.tags

    def test_tags_in_as_dict(self, patch_innertube):
        from tutubo import YoutubeSearch
        d = list(YoutubeSearch("rob zombie").iterate_videos(max_res=1))[0].as_dict
        assert "tags" in d
        assert isinstance(d["tags"], list)

    def test_full_album_tag(self):
        assert "full-album" in extract_tags("Black Sabbath - Paranoid (Full Album)")

    def test_ep_tag(self):
        assert "ep" in extract_tags("Annapurna - LAM (2026) (new full EP)")

    def test_premiere_tag(self):
        assert "premiere" in extract_tags("Hajduk - Хвърковата чета (Full Album Premiere)")

    def test_action_tag_no_false_positive(self):
        # bare "action" in a non-film context should not produce the tag
        tags = extract_tags("How to take action on climate change")
        assert "action" not in tags

    def test_action_tag_film_context(self):
        assert "action" in extract_tags("Best Action Movie Compilation 2024")

    def test_dc_tag_no_false_positive(self):
        # "DC" in electronics context should not produce superhero tag
        tags = extract_tags("DC motor control tutorial")
        assert "superhero" not in tags

    def test_dc_comics_tag(self):
        assert "superhero" in extract_tags("DC Comics - Batman Animated Series")


# ===========================================================================
# MUSIC_VIDEO duration gate
# ===========================================================================

class TestMusicVideoDurationGate:
    def test_oac_short_is_music_video(self):
        assert _ct("Artist - Song", length=240, is_official_artist=True) == ContentType.MUSIC_VIDEO

    def test_oac_at_limit_is_music_video(self):
        assert _ct("Artist - Long Mix", length=900, is_official_artist=True) == ContentType.MUSIC_VIDEO

    def test_oac_over_limit_falls_through(self):
        # OAC but > 900 s and no music_video keyword → falls through to VIDEO (no match below)
        assert _ct("Artist - Extended Set", length=901, is_official_artist=True) == ContentType.VIDEO

    def test_full_album_title_beats_oac(self):
        # "Full Album" → MUSIC_AUDIO regardless of OAC flag or duration
        assert _ct("Black Sabbath - Master of Reality (Full Album)", length=5010, is_official_artist=True) == ContentType.MUSIC_AUDIO

    def test_official_music_video_keyword_within_gate(self):
        # keyword "Official Music Video" within gate → MUSIC_VIDEO
        assert _ct("Artist - Song (Official Music Video)", length=240) == ContentType.MUSIC_VIDEO

    def test_official_music_video_keyword_over_gate(self):
        # keyword + over gate → falls through (a 20-min "music video" is really something else)
        assert _ct("Long Form Official Music Video", length=1201) != ContentType.MUSIC_VIDEO

    def test_channel_music_tag_long_upload_not_music_video(self):
        # channel_tags music but >900 s → MUSIC_VIDEO gate rejects; title has no concert keyword
        # "Full Set" triggers CONCERT via _CONCERT_RE, which is the correct classification
        result = _ct("Stoner Doom Live Full Set 2024", length=3600, channel_tags=["music", "band"])
        assert result == ContentType.CONCERT


# ===========================================================================
# Full-album / EP / premiere → MUSIC_AUDIO
# ===========================================================================

class TestFullAlbumPatterns:
    def test_full_album(self):
        assert _ct("Bad Impression - Vultures (Full Album)") == ContentType.MUSIC_AUDIO

    def test_full_album_premiere(self):
        assert _ct("Hajduk - Хвърковата чета (Full Album Premiere)") == ContentType.MUSIC_AUDIO

    def test_full_ep(self):
        assert _ct("Annapurna - LAM (2026) (new full EP)") == ContentType.MUSIC_AUDIO

    def test_new_full_album(self):
        assert _ct("Jhufus - Horizon I (2026) (New Full Album)") == ContentType.MUSIC_AUDIO

    def test_track_premiere(self):
        assert _ct("Hor - Ecce Mortuus (Track Premiere)") == ContentType.MUSIC_AUDIO

    def test_new_album(self):
        assert _ct("Firmament - New Album 2025") == ContentType.MUSIC_AUDIO

    def test_album_premiere_with_length(self):
        assert _ct("Artist - Debut Album Premiere", length=2700) == ContentType.MUSIC_AUDIO

    def test_full_album_not_triggered_by_partial_word(self):
        # "albumin" should not match
        assert _ct("Albumin protein structure lecture") != ContentType.MUSIC_AUDIO


# ===========================================================================
# SOCIAL_CLIP (formerly SHORT)
# ===========================================================================

class TestSocialClipNaming:
    def test_value_is_social_clip(self):
        assert ContentType.SOCIAL_CLIP.value == "social_clip"

    def test_not_short(self):
        # Ensure old "short" value is gone
        assert not any(ct.value == "short" for ct in ContentType)

    def test_short_film_still_exists(self):
        assert ContentType.SHORT_FILM.value == "short_film"

    def test_social_clip_classified(self):
        assert _ct("quick clip", length=30) == ContentType.SOCIAL_CLIP

    def test_social_clip_boundary(self):
        assert _ct("clip", length=61) == ContentType.SOCIAL_CLIP
        assert _ct("clip", length=62) != ContentType.SOCIAL_CLIP
