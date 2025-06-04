import argparse
from ast import parse
import os
from pathlib import Path
import yaml
from feedscoring.utils import flatten_keys, parse_duration
import getpass


parser = argparse.ArgumentParser(description="Feed scoring tool")
parser.add_argument("--url", help="URL of the CTI feed", default=os.getenv("URL"), required=not bool(os.getenv("URL")))
parser.add_argument("-v", "--verbose", action="count", help="Increase verbosity level (e.g., -v, -vv, -vvv)", default=int(os.getenv("VERBOSE", "0")))
parser.add_argument("-l", "--limit", type=int, help="Consume at most n objects", default=os.getenv("VERBOSE", "0") == "1")
parser.add_argument("-f", "--pir-file", help="Path to Priority Intelligence Requirements (PIR) weights YAML file", default=os.getenv("PIR_FILE"))
parser.add_argument("-H", "--human-readable", help="Human-readable output", action="store_true")
parser.add_argument("-s", "--since", help="Consume objects since given date (in ISO format, or relative format like '1y2m3d')", default=os.getenv("SINCE", ""))
parser.add_argument("-t", "--type", help="Feed type", default=os.getenv("FEED_TYPE", "TAXII"))
parser.add_argument("--batch-size", help="Consumption batch size", default=os.getenv("BATCH_SIZE", 10000))
parser.add_argument("--webhook", help="An HTTP POST webhook URL to push results to", default=os.getenv("WEBHOOK"))
parser.add_argument(
    "--webhook-header",
    help="Add an HTTP header to the webhook calls in <header>=<value> format (can be supplied multiple times)",
    action="append",
    default=os.getenv("WEBHOOK_HEADERS", "").split(",") if os.getenv("WEBHOOK_HEADERS") else [],
)
parser.add_argument("--every", type=str, help="Score update frequency", default=os.getenv("EVERY", 2))
parser.add_argument("--load", help="Start from a previously saved state from given file", default=os.getenv("LOAD"))
parser.add_argument("--save", help="Periodically save state to given file", default=os.getenv("SAVE"))
parser.add_argument("--name", help="Name of the feed", default=os.getenv("NAME", ""))
parser.add_argument("--provider-name", help="Name of the feed's provider", default=os.getenv("PROVIDER_NAME", ""))
parser.add_argument("--webhook-graphql", help="A GraphQL webhook URL to push results to", default=os.getenv("WEBHOOK_GRAPHQL"))

SETTINGS = parser.parse_args()

API_KEY = os.getenv("API_KEY", "") or getpass.getpass("Enter your API key: ")

SETTINGS.since = parse_duration(SETTINGS.since) if SETTINGS.since else None
SETTINGS.every = parse_duration(SETTINGS.every).total_seconds() or 2.0

####
# Load Priority Intelligence Requirements (PIR) weights
PIR = {}
# Load PIR weights from YAML file
if SETTINGS.pir_file and Path(SETTINGS.pir_file).is_file():
    with Path(SETTINGS.pir_file).open() as f:
        PIR.update(flatten_keys(yaml.safe_load(f), sep="_", lowercase=True))
# Override PIR weights with environment variables
for k, v in os.environ.items():
    if k.startswith("PIR_"):
        PIR[k.split("PIR_")[1].lower()] = float(v)
