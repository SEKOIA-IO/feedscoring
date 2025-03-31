from stix2validator import validate_instance
import stix2validator.errors


def stix_validity_score(obj: dict, debug: bool = False) -> float:
    """
    Compute a STIX object validity score between 0 and 1 based
    on stix2validator.validate_instance()'s evaluation
    """
    score = 1.0
    try:
        r = validate_instance(obj)
        if r.is_valid and not r.errors:
            return score
        else:
            for e in r.errors:
                if "'spec_version' is a required property" in e.message:
                    score *= 0.9
                elif "null properties are not allowed in STIX" in e.message:
                    score *= 0.9
                elif "empty arrays are not allowed" in e.message:
                    pass  # Already handled by the next two elifs
                elif "external_references: [] should be non-empty" in e.message:
                    score *= 0.7
                elif "labels: [] should be non-empty" in e.message:
                    score *= 0.7
                elif "'type' is a required property" in e.message:
                    score *= 0.5
                elif "'pattern_type' is a required property" in e.message:
                    score *= 0.5
                elif "'id' is a required property" in e.message:
                    score *= 0.2
                else:
                    if debug:
                        print(e.message)
                    score *= 0.8
        return score
    except stix2validator.errors.ValidationError as e:
        if "Input must be an object with 'id' and 'type' properties" in str(e):
            return 0.0
        return 0.1
    except Exception as e:
        if debug:
            print(e)
        return 0.0
