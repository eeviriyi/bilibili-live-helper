from fans_medal_helper.bilibili import _is_live


def test_recognizes_current_and_legacy_live_status_fields():
    assert _is_live(1)
    assert _is_live("1")
    assert _is_live(True)
    assert not _is_live(0)
    assert not _is_live(None)
