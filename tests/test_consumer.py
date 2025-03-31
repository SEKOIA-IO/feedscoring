from datetime import datetime, timedelta
import inspect
import os
from unittest import skipIf


@skipIf(
    not os.getenv("URL") or not os.getenv("API_KEY"),
    "No URL or API_KEY environment variables set",
)
def test_sekoia_consumer():
    from feedscoring.consumer import sekoia_feed_consumer

    # Test that the function is a generator
    assert inspect.isgeneratorfunction(sekoia_feed_consumer)

    # Test that the function yields STIX objects
    for obj in sekoia_feed_consumer(url=os.getenv("URL"), api_key=os.getenv("API_KEY")):
        assert isinstance(obj, dict)
        assert "created" in obj
        assert "modified" in obj
        assert "id" in obj
        assert "type" in obj
        assert "spec_version" in obj
        assert "name" in obj
        break


@skipIf(
    not os.getenv("URL") or not os.getenv("API_KEY"),
    "No URL or API_KEY environment variables set",
)
def test_consumer():
    from feedscoring.consumer import consumer

    # Test that the function is a generator
    assert inspect.isgeneratorfunction(consumer)

    # Test that the function yields STIX objects
    for obj in consumer("sekoia", url=os.getenv("URL"), api_key=os.getenv("API_KEY")):
        assert isinstance(obj, dict)
        assert "created" in obj
        assert "modified" in obj
        assert "id" in obj
        assert "type" in obj
        assert "spec_version" in obj
        assert "name" in obj
        break


@skipIf(
    not os.getenv("URL") or not os.getenv("API_KEY"),
    "No URL or API_KEY environment variables set",
)
def test_consumer_since():
    from feedscoring.consumer import consumer

    # Test that the function is a generator
    assert inspect.isgeneratorfunction(consumer)

    # Test that the function yields STIX objects
    for obj in consumer(
        "sekoia",
        url=os.getenv("URL"),
        api_key=os.getenv("API_KEY"),
        since=datetime.today() - timedelta(days=15),
    ):
        assert isinstance(obj, dict)
        assert "created" in obj
        assert "modified" in obj
        assert "id" in obj
        assert "type" in obj
        assert "name" in obj
        break


@skipIf(
    not os.getenv("URL") or not os.getenv("API_KEY"),
    "No URL or API_KEY environment variables set",
)
def test_consumer_types():
    from feedscoring.consumer import consumer

    # Test that the function is a generator
    assert inspect.isgeneratorfunction(consumer)

    # Test that the function yields STIX objects
    for obj in consumer(
        "sekoia",
        url=os.getenv("URL"),
        api_key=os.getenv("API_KEY"),
        types=["campaign"],
    ):
        assert isinstance(obj, dict)
        assert "created" in obj
        assert "modified" in obj
        assert "id" in obj
        assert obj["type"] == "campaign"
        assert "name" in obj
        break
