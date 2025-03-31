from feedscoring.consumer import consumer
from feedscoring.pretty import tqdm_progress
import orjson

from feedscoring.settings import API_KEY, SETTINGS

with open("data/feed.json", "w") as f:
    for o in tqdm_progress(
        consumer(
            SETTINGS.feed_type,
            url=SETTINGS.url,
            api_key=API_KEY,
            page_size=SETTINGS.batch_size,
        ),
        desc="Consumed",
        unit="obj",
    ):
        print(orjson.dumps(o), file=f)
