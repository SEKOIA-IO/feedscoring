from collections import Counter, defaultdict
from datetime import datetime, timedelta
import json
import logging
import math
from pathlib import Path
import pickle
from random import random
from sys import stderr
from time import time

import requests
from feedscoring.consumer import consumer
from feedscoring.pretty import print_scores

from feedscoring.settings import PIR, SETTINGS
from feedscoring.stix_validator import stix_validity_score
from feedscoring.utils import minmax, normalize_between, parse_datetime

logging.basicConfig(level=logging.INFO)


TRACKED_CTI_OBJECT_TYPES = {
    "attack-pattern",
    "campaign",
    "course-of-action",
    "identity",
    "indicator",
    "infrastructure",
    "intrusion-set",
    "location",
    "malware",
    "report",
    "threat-actor",
    "tool",
    "vulnerability",
}

scores = {
    "relevance": {
        "applicability": 0.0,
        "accuracy": 0.0,
        "timeliness": 0.0,
    },
    "usability": {
        "machine_readability": 0.0,
        "consumability": 0.0,
        "actionability": 0.0,
    },
    "global": {
        "score": 0.0,
    },
}

counters = defaultdict(Counter)
components = defaultdict(dict)


# Initialize counters
sum_confidence = 0.0
sum_confidence_2 = 0.0
nb_objects = 0
report_publish_to_create_hours = 0.0
nb_indicators_updated = 0
indicator_delay_hours = 0.0
stix_validity = 0.0
nb_validated_objects = 0
indicators_confidence = 0.0
indicators_having_pattern = 0.0
indicators_having_validity = 0.0
indicators_having_killchain = 0.0
min_date: datetime | None = None
max_date: datetime | None = None
start_time = time()


# Load saved state if asked
if SETTINGS.load and Path(SETTINGS.load).is_file():
    with open(SETTINGS.load, "rb") as f:
        data = pickle.load(f)
        for k, v in data.get("counters", {}).items():
            counters[k].update(v)
        for k, v in data.get("components", {}).items():
            components[k].update(v)
        for k, v in data.get("scores", {}).items():
            scores[k].update(v)
        min_date = parse_datetime(data["min_date"])
        max_date = parse_datetime(data["max_date"])
        nb_objects = data["nb_objects"]
        sum_confidence = data["sum_confidence"]
        sum_confidence_2 = data["sum_confidence_2"]
        report_publish_to_create_hours = data["report_publish_to_create_hours"]
        nb_indicators_updated = data["nb_indicators_updated"]
        indicator_delay_hours = data["indicator_delay_hours"]
        stix_validity = data["stix_validity"]
        nb_validated_objects = data["nb_validated_objects"]
        indicators_confidence = data["indicators_confidence"]
        indicators_having_pattern = data["indicators_having_pattern"]
        indicators_having_validity = data["indicators_having_validity"]
        indicators_having_killchain = data["indicators_having_killchain"]
        SETTINGS.since = max_date + timedelta(microseconds=1) if max_date else None
    logging.info(f"Loaded state from {SETTINGS.load}, start consuming from {SETTINGS.since}")

SECTORS = {}


def collect_sectors():
    """
    Collect sectors by consuming the feed filtered on identity objects
    """
    logging.info("Collecting sectors from the feed...")
    for o in consumer(types=["identity"], since=None):
        if o.get("identity_class") == "class" and o.get("sectors"):
            SECTORS[o["id"]] = o["sectors"][0]
    logging.info(f"Collected {len(SECTORS)} sectors")
    return SECTORS


def save_state():
    with open(SETTINGS.save, "wb") as f:
        pickle.dump(
            {
                "counters": counters,
                "components": counters,
                "scores": scores,
                "min_date": min_date.isoformat() if min_date else None,
                "max_date": max_date.isoformat() if max_date else None,
                "nb_objects": nb_objects,
                "sum_confidence": sum_confidence,
                "sum_confidence_2": sum_confidence_2,
                "report_publish_to_create_hours": report_publish_to_create_hours,
                "nb_indicators_updated": nb_indicators_updated,
                "indicator_delay_hours": indicator_delay_hours,
                "stix_validity": stix_validity,
                "nb_validated_objects": nb_validated_objects,
                "indicators_confidence": indicators_confidence,
                "indicators_having_pattern": indicators_having_pattern,
                "indicators_having_validity": indicators_having_validity,
                "indicators_having_killchain": indicators_having_killchain,
            },
            f,
        )
    logging.debug(f"Saved state to {SETTINGS.save}")


def update_scores():
    nb_indicators = counters["type"]["indicator"]
    nb_campaigns = counters["type"]["campaign"]
    nb_reports = counters["type"]["report"]
    nb_vulnerabilities = counters["type"]["vulnerability"]
    nb_course_of_actions = counters["type"]["course-of-action"]
    nb_intrusion_sets = counters["type"]["intrusion-set"]
    nb_threat_actors = counters["type"]["threat-actor"]
    nb_malwares = counters["type"]["malware"]
    nb_tools = counters["type"]["tool"]

    ###
    # Compute applicability score as the ratio of objects linked to a sector
    # over the total number of objects, weighted by sector PIR distribution
    sector_weights = {s.lower(): float(w) for s, w in PIR.items() if s.startswith("sector_distribution_")}
    if not sector_weights:
        # If no sector weights are provided, we consider all sectors to have the same weight (sector-agnostic feed)
        sector_weights = {s.lower(): 1.0 for s in SECTORS.values()}
    total_weight = sum(sector_weights.values()) or 1.0
    scores["relevance"]["applicability"] = minmax(
        (0, 100),
        sum(
            (n / counters["type"][src_type]) * (sector_weights.get(sector.lower(), 1.0) / total_weight)
            for (src_type, sector), n in counters["sector_targeted_by"].items()
            if src_type not in ("relationship", "indicator", "vulnerability") and counters["type"][src_type] > 0.0
        )
        * 100.0,
    )

    ###
    # Compute accuracy score as the average confidence over all objects
    # modulated by its standard deviation
    # Ex: an very good feed with 80% confidence on all objects with a maximal deviation of 50 yields 90/100
    if nb_objects > 0:
        avg_confidence = sum_confidence / nb_objects
        stddev = (sum_confidence_2 / nb_objects - avg_confidence**2) ** 0.5
        components["relevance"]["avg_confidence"] = avg_confidence
        components["relevance"]["stddev_confidence"] = stddev
        scores["relevance"]["accuracy"] = minmax(
            (0, 100),
            (avg_confidence + stddev * 2) / 2.0,
        )

    ###
    # Compute timeliness scores as a combination of:
    # - the time between report publication and creation
    # - the ratio of updated indicators
    # - the delay between indicator validity and creation
    if counters["type"]["report"] > 0 and nb_indicators > 0:
        components["relevance"]["timeliness_nb_reports"] = counters["type"]["report"]
        components["relevance"]["timeliness_avg_report_publish_create_delay"] = report_publish_to_create_hours / counters["type"]["report"]
        components["relevance"]["timeliness_osint"] = (
            normalize_between(
                (60 * 24),
                (1 * 24),
                267,
            )
            * 100.0
        )
        components["relevance"]["timeliness_update"] = minmax((0, 100), nb_indicators_updated / nb_indicators) * 100.0

        components["relevance"]["avg_indicator_validity_delay"] = indicator_delay_hours / nb_indicators
        components["relevance"]["timeliness_delay"] = minmax(
            (0.0, 100.0),
            100.0
            # We score indicator validity timeliness a decaying
            # exponential function to give more weight to recent indicators
            # 24h yields 97/100
            # 10 days yields 78/100
            # 100 days yields 9/100
            * math.exp(-0.001 * components["relevance"]["avg_indicator_validity_delay"]),
        )

        scores["relevance"]["timeliness"] = minmax(
            (0, 100),
            (components["relevance"]["timeliness_osint"] + components["relevance"]["timeliness_update"] + components["relevance"]["timeliness_delay"]) / 3,
        )

    ###
    # Compute machine readability score as the average of:
    # - STIX format compliance
    # - average STIX validity score
    scores["usability"]["machine_readability"] = minmax(
        (0, 100),
        (
            (
                1.0  # compliance with STIX format already gives 50% of the score
                + stix_validity / nb_validated_objects  # average STIX validity score
            )
            if nb_validated_objects
            else 0.0
        )
        * 50.0,
    )

    ###
    # Compute consumability score as a thresholded combination of:
    # - the indicators production rate (per month)
    # - the campaign+report production rate
    # - the malware+tool production rate
    # - the intrusion-set+threat-actor production rate
    # - the vulnerability production rate
    # - the course-of-action production rate
    # - the total production rate of those objects
    # The respective thresholds are defined in PIR settings
    # When an object type's monthly volume reaches the threshold, the score's component is 100
    # When an object type isn't produced at all, the score's component is 0

    months = (max_date - min_date).total_seconds() / 3600.0 / 24 / 30.0
    if months > 0:
        monthly_indicators = nb_indicators / months
        monthly_campaigns_reports = (nb_campaigns + nb_reports) / months
        monthly_malwares_tools = (nb_malwares + nb_tools) / months
        monthly_intrusions_threats = (nb_intrusion_sets + nb_threat_actors) / months
        monthly_vulnerabilities = nb_vulnerabilities / months
        monthly_course_of_actions = nb_course_of_actions / months
        components["usability"]["consumability_monthly_indicators"] = monthly_indicators
        components["usability"]["consumability_monthly_campaigns_reports"] = monthly_campaigns_reports
        components["usability"]["consumability_monthly_malwares_tools"] = monthly_malwares_tools
        components["usability"]["consumability_monthly_intrusions_threats"] = monthly_intrusions_threats
        components["usability"]["consumability_monthly_vulnerabilities"] = monthly_vulnerabilities
        components["usability"]["consumability_monthly_course_of_actions"] = monthly_course_of_actions

        scores["usability"]["consumability"] = minmax(
            (0, 100),
            (
                # Total monthly volume counts for 50% of the score
                nb_objects / months / PIR.get("monthly_total", 30000) * 100.0
                + (
                    # Indicators production rate counts for 25% of the score
                    minmax((0, 1), monthly_indicators / PIR.get("monthly_indicators", 10000)) * 50.0
                    # Other important objects production rate counts evenly for the remaining 25%
                    + minmax((0, 1), monthly_campaigns_reports / PIR.get("monthly_campaigns_reports", 80)) * 10
                    + minmax((0, 1), monthly_malwares_tools / PIR.get("monthly_malwares_tools", 40)) * 10
                    + minmax((0, 1), monthly_intrusions_threats / PIR.get("monthly_intrusionsets_threatactors", 16) * 10)
                    + minmax((0, 1), monthly_vulnerabilities / PIR.get("monthly_vulnerabilities", 8000)) * 10
                    + minmax((0, 1), monthly_course_of_actions / PIR.get("monthly_courseofactions", 8)) * 10
                )
            )
            / 2.0,
        )

    ###
    # Compute actionability score as a combination of:
    # - the number of countermeasures linked to indicators
    # - the ratio of indicators having a validity period
    # - the ratio of indicators having a pattern
    # - the ratio of indicators having kill chain phases
    # - the average confidence of indicators
    # - the ratio of indicators having relationships to other SDOs

    if nb_indicators > 0:
        components["usability"]["actionability_countermeasures"] = 100.0

        components["usability"]["actionability_validity"] = minmax((0, 100), 100.0 * (indicators_having_validity / nb_indicators))
        components["usability"]["actionability_patterns"] = minmax((0, 100), 100.0 * (indicators_having_pattern / nb_indicators))
        components["usability"]["actionability_killchain"] = minmax((0, 100), 100.0 * (indicators_having_killchain / nb_indicators))
        components["usability"]["actionability_confidence"] = minmax((0, 100), 100.0 * (6.0 - indicators_confidence / nb_indicators))
        components["usability"]["actionability_relationships"] = minmax(
            (0, 100),
            100.0 * (counters["relationships_by_src_type"]["indicator"] / nb_indicators),
        )

        scores["usability"]["actionability"] = minmax(
            (0, 100),
            (
                components["usability"]["actionability_countermeasures"]
                + components["usability"]["actionability_validity"]
                + components["usability"]["actionability_patterns"]
                + components["usability"]["actionability_killchain"]
                + components["usability"]["actionability_confidence"]
                + components["usability"]["actionability_relationships"]
            )
            / 6,
        )

        scores["global"]["score"] = minmax(
            (0, 100),
            (
                scores["relevance"]["applicability"]
                + scores["relevance"]["accuracy"]
                + scores["relevance"]["timeliness"]
                + scores["usability"]["machine_readability"]
                + scores["usability"]["consumability"]
                + scores["usability"]["actionability"]
            )
            / 6,
        )


def display_progress():
    if SETTINGS.human_readable:
        print("\x1b[H\x1b[2J", end="")  # Clear terminal output

    print(
        f"Consumed: {nb_objects} objects (created between {min_date} and {max_date}) in {time() - start_time:.2f}s [{nb_objects / (time() - start_time):.2f}obj/s]",
        file=stderr,
    )

    if SETTINGS.human_readable:
        if not SETTINGS.verbose:
            print_scores(scores)
        elif SETTINGS.verbose == 1:
            print_scores({"scores": scores, "components": components, "counters": counters})
        else:
            print_scores({"scores": scores, "components": components})
    else:

        def stringify_keys(d):
            if isinstance(d, dict):
                return {str(k): stringify_keys(v) for k, v in d.items()}
            elif isinstance(d, (list, tuple)):
                return [stringify_keys(i) for i in d]
            else:
                return d

        print(
            json.dumps(
                stringify_keys({"scores": scores, "components": components, "counters": counters}),
                default=str,
            ),
            flush=True,
        )


def post_webhook():
    r = requests.post(
        SETTINGS.webhook,
        json={
            "scores": scores,
            "components": components,
            "score": scores["global"]["score"],
            "feed_url": SETTINGS.url,
            "earliest": min_date.isoformat() if min_date else None,
            "latest": max_date.isoformat() if max_date else None,
            "nb_consumed": nb_objects,
        },
        headers={
            "Content-Type": "application/json",
            **{k: v for h in SETTINGS.webhook_header for k, v in [h.split("=")]},
        },
    )
    r.raise_for_status()
    return r


# Consume the CTI feed and update the scores in real-time
def main():
    global sum_confidence
    global sum_confidence_2
    global nb_objects
    global report_publish_to_create_hours
    global nb_indicators_updated
    global indicator_delay_hours
    global stix_validity, nb_validated_objects
    global indicators_confidence
    global indicators_having_pattern
    global indicators_having_validity
    global indicators_having_killchain
    global min_date
    global max_date
    last_score_update = time()

    collect_sectors()
    try:
        for o in consumer():
            try:
                #######################################################
                # Update necessary counters from consumed CTI objects #
                #######################################################

                # Count objects by type
                counters["type"][o["type"]] += 1

                # Track the timespan consumed until now
                min_date = min(
                    min_date or parse_datetime(o["created"]),
                    parse_datetime(o["created"]),
                )
                max_date = max(
                    max_date or parse_datetime(o["created"]),
                    parse_datetime(o["created"]),
                )

                # - Analyse relationships
                if o["type"] == "relationship":
                    src = o["source_ref"]
                    src_type = src.split("--")[0]
                    dst = o["target_ref"]
                    dst_type = dst.split("--")[0]

                    # Count relationships by src type and dst type
                    counters["relationships_by_src_type"][src_type] += 1
                    counters["relationships_by_dst_type"][dst_type] += 1

                    # Count relationships to sectors
                    if dst in SECTORS:
                        counters["sector"][SECTORS[o["target_ref"]]] += 1
                        counters["sector_targeted_by"][(src_type, SECTORS[o["target_ref"]])] += 1

                # - Analyse objects
                else:
                    nb_objects += 1
                    # Consider confidence as an score in percent
                    sum_confidence += o.get("confidence", 0)
                    sum_confidence_2 += o.get("confidence", 0) ** 2
                    created = parse_datetime(o["created"])

                    # Validate STIX object (by default we only validate 10% of objects to speed up the eval)
                    if random() <= PIR.get("validity_sampling_rate", 0.1):
                        stix_validity += stix_validity_score(o)
                        nb_validated_objects += 1

                    # Analyse reports
                    if o["type"] == "report":
                        published = parse_datetime(o["published"])
                        report_publish_to_create_hours += max(0, (created - published).total_seconds() / 3600.0)

                    # Analyse indicators
                    if o["type"] == "indicator":
                        # Count indicators updated at least once
                        if o["created"] != o["modified"]:
                            nb_indicators_updated += 1

                        # Compute delay between validity and creation
                        valid_from = parse_datetime(o["valid_from"])
                        indicator_delay_hours += max(0, (created - valid_from).total_seconds() / 3600.0)

                        # Compute indicator quality
                        indicators_confidence += minmax((0, 100), o.get("confidence", 0))
                        indicators_having_pattern += bool(o.get("pattern"))
                        indicators_having_validity += bool(o.get("valid_from") and o.get("valid_until"))
                        indicators_having_killchain += bool(o.get("kill_chain_phases"))
            except Exception as e:
                if SETTINGS.verbose:
                    logging.error(e)

            ###################################
            # Update scores in near real-time #
            ###################################

            if time() - last_score_update > SETTINGS.every:
                update_scores()
                display_progress()
                # Save state if asked
                if SETTINGS.save:
                    save_state()

                # Send scores to an HTTP POST webhook if asked
                # adding custom headers if they were provided using --webhook-header command line argument
                if SETTINGS.webhook:
                    try:
                        post_webhook()
                    except Exception as e:
                        logging.error(e)

                last_score_update = time()

    except KeyboardInterrupt:
        ...


if __name__ == "__main__":
    main()
