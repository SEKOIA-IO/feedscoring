from datetime import datetime, timedelta
from time import sleep
from tkinter import SE
import requests

from feedscoring.settings import API_KEY, SETTINGS
from feedscoring.utils import parse_datetime


def taxii_consumer(
    url: str,
    api_key: str | None = None,
    page_size=10000,
    since: datetime | None = None,
    types: list[str] | None = None,
):
    """A consumer for standard TAXII feeds."""
    from taxii2client import Collection

    c = Collection(url)
    if api_key:
        c._conn.session.headers.update({"Authorization": f"Bearer {api_key}"} if api_key else {})

    for page in c.get_objects(
        as_pages=True,
        page_size=page_size,
        modified_after=since,
        type=types,
    ):
        for obj in page.get("objects", []):
            yield obj


def sekoia_feed_consumer(
    url,
    api_key: str,
    page_size: int = 10000,
    since: datetime | None = None,
    types: list[str] | None = None,
):
    """A consumer for Sekoia.io CTI feeds."""
    session = requests.Session()
    session.headers.update({"Authorization": f"Bearer {api_key}"})
    cursor = None

    params = {
        "limit": page_size,
    }
    if types:
        params["match[type]"] = types
    if since:
        params["modified_after"] = since.replace(microsecond=0, tzinfo=None).isoformat() + "Z"

    while True:
        # Cursor and modieifed_after are mutually exclusive
        if cursor:
            params.pop("modified_after", None)

        for _ in range(25):
            r = session.get(url, params={**params, "cursor": cursor})
            if r.status_code < 400:
                break
            if _ == 24:
                raise ValueError(f"Error fetching data from {url}: {r.text}")
            sleep(10)
        r = r.json()
        if r.get("next_cursor", cursor) == cursor:
            return
        for obj in r.get("items", []):
            if not since or parse_datetime(obj.get("created")) >= since:
                yield obj
        cursor = r.get("next_cursor")


CONSUMERS = {
    "taxii": taxii_consumer,
    "sekoia": sekoia_feed_consumer,
}


def consumer(
    type: str = SETTINGS.type,
    url: str = SETTINGS.url,
    api_key: str = API_KEY,
    page_size: int = SETTINGS.batch_size,
    since: datetime | timedelta | None = None,
    types: list[str] | None = None,
):
    """A factory function or consumers. Consumers are generators that yield STIX objects from a CTI feed."""
    since = since or SETTINGS.since
    if isinstance(since, timedelta):
        since = datetime.now() - since
    elif isinstance(since, str):
        since = datetime.fromisoformat(SETTINGS.since)

    try:
        c = CONSUMERS[type.lower()]
    except KeyError:
        raise ValueError(f"Unknown CTI feed type: {type} " + f"(supported: {', '.join(CONSUMERS.keys())})")
    yield from c(url, api_key, page_size=page_size, since=since, types=types)
