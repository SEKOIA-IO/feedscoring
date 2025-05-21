# Opensource CTI feed scoring tool
A tool to assess CTI content delivered as a feed

## Context
Evaluating CTI feeds can be tricky. There is neither a recognized method nor than a tool to  get direct results.
In a research paper  **"ASSESSING THE POTENTIAL VALUE OF CYBER
THREAT INTELLIGENCE (CTI) FEEDS"** , Kimberly Watson proposed some key evaluation metrics that can be interesting to assess a feed.
This paper was written at Applied Physics Laboratory (John Hopkins) and is available on a [CISA webpage](https://www.cisa.gov/sites/default/files/publications/Assessing%2520Cyber%2520Threat%2520Intelligence%2520Threat%2520Feeds_508c.pdf)

## Approach

The assessment relies on two main areas of interest: relevance and usability. For each area, three criterias are listed as being driver of value:

### Relevance
To define how much a feed is relevant, we have to know how much it is:
- Applicable
- Accurate
- Timely

### Usability
To define how much a feed is usable, we have to know how much it is:
- Machine-readable
- Consumable
- Actionable

## Feedscoring tool

Considering it could be interesting to have a tool to leverage this paper, we decided to translate criteria into computed scores.
The Feedscoring tool can use a STIX based feed as input, it ingests it, computes 6 sub-scores and provides the result to the user

### Example

![](resources/feedscoring.svg)



## Computation

We use different methods for each criteria:

### Applicable
   - The data must be applicable for the consuming organization. We can guess the sector association is important for this criteria. STIX defines sector as identities. These identities can be defined as target for some objects (malware, tool, threat_actor, campaigns, intrusion_sets). We count the density of identity-related relationships between source objects and their targets

### Accurate
   - A confidence level must be present and must be trusted by consumer organization.
   - The provider take care to place the confidence level correctly and accept to have a variety of different confidence levels, not only highly trusted levels which could lead to misinterpretation

### Timely
The information must be made available in time for the organization. In order to evaluate that, we measure:
- the delta between public CTI ingestion time and availability time
- the ratio of updates for exclusive intelligence
- how fast intelligence is unveiled after the threat’s first observed activity

### Machine Readable
   - Intelligence is structured and delivered in a format that is recognized by different stakeholders and can be understood by the consumer. We consider using STIX format is part of the answer.
   - The other part of the score comes from best practices enforcement in the way stix modelization is being made. [STIX validator opensource tool](https://github.com/oasis-open/cti-stix-validator) is leveraged for that

### Consumable
   - Intelligence can be used in multiple ways. The variety of information impacts a lot for relevant workflows. Therefore we evaluate the diversity and distribution of CTI objects to cover multiple consumption use-cases
   - Quality is not everything but having access to enough information is necessary to allow contextualization and pivoting activities.

### Actionable

  - We consider the actionability will be good if several parameters are fulfilled:
  - Countermeasures or Courses of Actions must exist, with direct or indirect relationships with  malware, threat actors or TTPs
  - Validity date must be present to not overload the consumer storage or computing engines
  - A killchain stage must be present for indicators to know the risk level they are associated with
  - A relationship  must exist for each indicator to give actionability context
  - The confidence  mus be present for each indicator
  - A pattern must be present for each indicator to operationalize it


## Install

```bash
poetry install
```

## Configuration


| Command Line Argument | Short Form | Environment Variable | Description                                                                 |
|------------|------------|-----------------------|-----------------------------------------------------------------------------|
| `--api-key`           | `-k`       | `API_KEY`            | The API key used to authenticate with the feed provider.                   |
|  `--url`               | `-u`       | `URL`                | The URL of the CTI feed to evaluate.                                       |
| `--feed-type`       | `-t`       | `FEED_TYPE`          | The type of the feed (e.g., `sekoia`, `custom`).                           |
| `--since`             | `-s`       | `SINCE`              | The time range to evaluate the feed (e.g., `1y`, `6m`, `2024-01-01`, ...).                   |
|  `--webhook`           | `-w`       | `WEBHOOK`            | The URL to send evaluation results via HTTP POST.                          |
|  `--every`             | `-e`       | `EVERY`              | The interval in seconds to push updated scores to the webhook.             |
|  `--pir-file`         | `-f`       | `PIR_FILE`           | The file path to a Priority Intelligence Requirements (PIR) YAML file.     |
|  `--verbose`           | `-v`       | `VERBOSE`            | The verbosity level for logging (e.g., `-v`, `-vv`, `-vvv`).               |
|  `--human-readable` | `-H`    | `HUMAN_READABLE`     | Display evaluation progress in a human-readable format.                    |
|  `--save` |     | `SAVE`     | Periodically save state to given file, for incremental runs.                    |
|  `--load` |     | `LOAD`     | Start from a previously saved state from given file.                    |
| `--webhook-header` | | `WEBHOOK_HEADERS` | Additional headers to include in the HTTP POST request to the webhook, in K=V format. Env var may be supplied in K=V,K=V,K=V format |

## Use cases


### As a feed user, just to have an idea if it's good

Evaluate a feed (URL provided as commandline argument). You will be prompted for the feed's API KEY.
Scores and detailed sub-score components will be written to standard output in JSON line format, updated every 2s.
Progress will be logged to stderr.
```bash
poetry run feedscoring --url https://api.sekoia.io/v2/inthreat/collections/d6092c37-d8d7-45c3-8aff-c4dc26030608/objects
```

Evaluate a feed, passing `API_KEY`, `URL` and `FEED_TYPE` as environment variables.
```bash
export API_KEY=<myapikey>
export URL=https://api.sekoia.io/v2/inthreat/collections/d6092c37-d8d7-45c3-8aff-c4dc26030608/objects
export FEED_TYPE=sekoia
```

Evaluate a feed over past year, print realtime evaluation progress in human readable format
```bash
poetry run feedscoring -H --since 1y
```
> Note: keep in mind the foundational core objects of a CTI feed might have been produced at the begining. The parameter "--since" should not be used to get a reliable score.

### As a buyer to compare CTI feeds during RFP stage


Verbose mode, showing all sub-score components used in computing the global feed's score
```bash
poetry run feedscoring -H --since 6m -vvv
```

### As a CTI analyst, you want to check your feeds are relevant and aligned with your PIR

Evaluate a feed using specific Priority Intelligence Requirements from `examples/pir.yaml` (see [examples/pir.yaml](examples/pir.yaml) for expected file format).
Push updated scores every 5 minutes to an HTTP POST webhook with a JSON body
```bash
poetry run feedscoring -H --since 6m -vvv -f examples/pir.yaml --webhook http://localhost:8000/scores --every 300s
```

### As a tool to forward the result to a solution (Threat Intelligence Platform / CTI marketplace)

Evaluate a feed regularly and ush updated scores every 5 minutes to an HTTP POST webhook with a JSON body
```bash
poetry run feedscoring -H --since 6m -vvv --webhook http://localhost:8000/scores --every 300s
```

POSTed payload will look like the following:

```
POST /scores HTTP/1.1
Host: localhost:8000
User-Agent: python-requests/2.32.3
Accept-Encoding: gzip, deflate
Accept: */*
Connection: keep-alive
Content-Length: 1130
Content-Type: application/json

{
   "scores": {"relevance": {"applicability": 74.6894368, "accuracy": 88.312942136990976, "timeliness": 75.987798273897843}, "usability": {"machine_readability": 94.00000000000001, "consumability": 100, "actionability": 80.81166272655635}, "global": {"score": 52.187434143924555}},
   "components": {"relevance": {"avg_confidence": 69.83490566037736, "stddev_confidence": 3.3954893068022955}, "usability": {"consumability_monthly_indicators": 49983.63383556335, "consumability_monthly_campaigns_reports": 0.0, "consumability_monthly_malwares_tools": 0.0, "consumability_monthly_intrusions_threats": 0.0, "consumability_monthly_vulnerabilities": 118.16461899660366, "consumability_monthly_course_of_actions": 0.0, "actionability_countermeasures": 100.0, "actionability_validity": 100.0, "actionability_patterns": 100.0, "actionability_killchain": 100.0, "actionability_confidence": 0, "actionability_relationships": 84.86997635933807}},
   "score": 82.187434143924555,
   "feed_url": "https://api.sekoia.io/v2/inthreat/collections/d6092c37-d8d7-45c3-8aff-c4dc26030608/objects",
   "earliest": "2024-09-28T11:12:18",
   "latest": "2024-09-28T23:23:29",
   "nb_consumed": 848
}
```