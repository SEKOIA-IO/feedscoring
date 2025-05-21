from feedscoring.main import collect_sectors


def test_sectors():
    assert collect_sectors() == {}
