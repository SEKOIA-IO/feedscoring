from feedscoring.utils import flatten_keys


def test_flatten_keys():
    assert flatten_keys(
        {"a": {"b": {"C": 1, "d": 7}, "X": 1}},
        sep=".",
        lowercase=True,
    ) == {
        "a.b.c": 1,
        "a.b.d": 7,
        "a.x": 1,
    }
