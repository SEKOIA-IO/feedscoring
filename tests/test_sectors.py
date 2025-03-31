from feedscoring.sectors import get_sectors


def test_sectors():
    get_sectors.cache_clear()
    assert len(get_sectors()) > 0
    assert "identity--7119e085-8c5a-4153-bb5c-10c9eb919305" in get_sectors()
    assert (
        get_sectors()["identity--7119e085-8c5a-4153-bb5c-10c9eb919305"] == "Government"
    )
