import pytest

from bilibili_live_helper.notify import validate_sequence_id


@pytest.mark.parametrize(
    "sequence_id",
    ["bilibili-2026-07-11-1", "bilibili_watch_2026-07-11"],
)
def test_accepts_ntfy_safe_sequence_ids(sequence_id):
    validate_sequence_id(sequence_id)


@pytest.mark.parametrize(
    "sequence_id", ["fans-medal:2026-07-11:1", "", "contains space"]
)
def test_rejects_ntfy_unsafe_sequence_ids(sequence_id):
    with pytest.raises(ValueError):
        validate_sequence_id(sequence_id)
