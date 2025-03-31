import os
from unittest import skipIf
from feedscoring.consumer import consumer
from feedscoring.stix_validator import stix_validity_score


def test_stix_validator():
    assert stix_validity_score({}) == 0.0


@skipIf(
    not os.getenv("URL") or not os.getenv("API_KEY"),
    "No URL or API_KEY environment variables set",
)
def test_stix_validator_on_consumer():
    for i, o in enumerate(
        consumer(
            os.getenv("FEED_TYPE", "TAXII"),
            url=os.getenv("URL"),
            api_key=os.getenv("API_KEY"),
            page_size=int(os.getenv("PAGE_SIZE", 10000)),
        )
    ):
        assert stix_validity_score(o) >= 0.0
        if i > 10:
            break
