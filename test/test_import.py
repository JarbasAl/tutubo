def test_import():
    import tutubo
    from tutubo.models import VideoPreview
    from tutubo.search import YoutubeSearch


def test_version():
    from tutubo.version import __version__
    assert __version__
