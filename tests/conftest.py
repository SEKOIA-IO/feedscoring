import os
from pytest import fixture
import requests_mock

# Permanent environment variables for testing
os.environ.update(
    {
        "ENV": "test",
        "API_KEY": "abcd",
        "URL": "http://feed.local",
        "WEBHOOK": "http://webhook.local",
        "WEBHOOK_HEADERS": "x-custom-header=secret",
        "FEED_TYPE": "sekoia",
    }
)


@fixture(scope="session", autouse=True)
def mock_feed():
    with requests_mock.Mocker() as mocker:

        def respond(request, context):
            context.status_code = 200
            context.headers["x-custom-header"] = request.headers["x-custom-header"]
            return {}

        mocker.register_uri(
            "GET",
            "http://feed.local",
            json={
                "items": [
                    {
                        "id": "indicator--12345678-1234-5678-1234-567812345678",
                        "type": "indicator",
                        "created": "2023-01-01T00:00:00Z",
                        "modified": "2023-01-01T00:00:00Z",
                        "name": "Test Indicator",
                    }
                ],
                "next_cursor": None,
            },
        )
        mocker.register_uri("POST", "http://webhook.local", json=respond)
        yield mocker
