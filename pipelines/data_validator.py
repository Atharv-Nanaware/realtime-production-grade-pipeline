import logging
import re
from datetime import datetime
import json

from constants.validation import *

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("data_validator")


def validate_required_fields(record):
    for field in REQUIRED_FIELDS:
        if field not in record or not record[field]:
            logger.warning(f"Missing required field: {field}")
            return False
    return True

def validate_email_format(email):
    if not email:
        return False
    return bool(re.match(EMAIL_PATTERN, email))

def validate_date_format(date_str):
    if not date_str:
        return False
    return bool(re.match(DATE_PATTERN, date_str))

def validate_data_types(record):
    invalid_fields = []
    for field, expected_type in FIELD_TYPES.items():
        if field in record:
            if isinstance(expected_type, list):
                if not any(isinstance(record[field], t) for t in expected_type):
                    invalid_fields.append(field)
            elif not isinstance(record[field], expected_type):
                invalid_fields.append(field)
    return len(invalid_fields) == 0, invalid_fields

def validate_value_constraints(record):
    constraint_violations = {}
    for field, allowed_values in {k: v for k, v in VALUE_CONSTRAINTS.items()
                                if isinstance(v, list)}.items():
        if field in record and record[field] not in allowed_values:
            constraint_violations[field] = f"Value must be one of: {', '.join(allowed_values)}"
    for field, constraints in {k: v for k, v in VALUE_CONSTRAINTS.items()
                            if isinstance(v, dict)}.items():
        if field in record:
            value = record[field]
            if "min_length" in constraints and len(value) < constraints["min_length"]:
                constraint_violations[field] = f"Minimum length: {constraints['min_length']}"
            if "max_length" in constraints and len(value) > constraints["max_length"]:
                constraint_violations[field] = f"Maximum length: {constraints['max_length']}"
    return len(constraint_violations) == 0, constraint_violations

def validate_record(record, usernames_seen=None):
    validation_details = {
        "required_fields": validate_required_fields(record)
    }
    if "email" in record:
        validation_details["email_format"] = validate_email_format(record["email"])
    else:
        validation_details["email_format"] = False
    if "registered_date" in record:
        validation_details["date_format"] = validate_date_format(record["registered_date"])
    else:
        validation_details["date_format"] = False
    if usernames_seen is not None and "username" in record and record["username"]:
        validation_details["username_unique"] = record["username"] not in usernames_seen
    else:
        validation_details["username_unique"] = True
    is_valid_types, invalid_fields = validate_data_types(record)
    validation_details["valid_data_types"] = is_valid_types
    if not is_valid_types:
        validation_details["invalid_data_types"] = invalid_fields
    is_valid_constraints, constraint_violations = validate_value_constraints(record)
    validation_details["valid_constraints"] = is_valid_constraints
    if not is_valid_constraints:
        validation_details["constraint_violations"] = constraint_violations
    is_valid = all([
        validation_details["required_fields"],
        validation_details["email_format"],
        validation_details["date_format"],
        validation_details["username_unique"],
        validation_details["valid_data_types"],
        validation_details["valid_constraints"]
    ])
    return is_valid, validation_details

def validate_batch(records):
    valid_records = []
    invalid_records = []
    validation_summary = {
        "total_records": len(records),
        "valid_records": 0,
        "invalid_records": 0,
        "validation_failures": {
            "required_fields": 0,
            "email_format": 0,
            "date_format": 0,
            "username_unique": 0,
            "data_types": 0,
            "value_constraints": 0
        }
    }
    for record in records:
        is_valid, validation_details = validate_record(record, None)
        for rule, passed in validation_details.items():
            if rule in validation_summary["validation_failures"] and not passed:
                validation_summary["validation_failures"][rule] += 1
        if is_valid:
            valid_records.append(record)
            validation_summary["valid_records"] += 1
        else:
            invalid_record = record.copy()
            invalid_record["_validation_details"] = validation_details
            invalid_records.append(invalid_record)
            validation_summary["invalid_records"] += 1
    logger.info(f"Data validation completed: {validation_summary['valid_records']} valid, "
               f"{validation_summary['invalid_records']} invalid records")
    if validation_summary["invalid_records"] > 0:
        logger.warning("Validation failures breakdown: "
                      f"{json.dumps(validation_summary['validation_failures'])}")
    return valid_records, invalid_records, validation_summary

def get_validation_report(invalid_records):
    report = {
        "total_invalid": len(invalid_records),
        "issues_by_field": {},
        "issues_by_rule": {
            "required_fields": 0,
            "email_format": 0,
            "date_format": 0,
            "username_unique": 0,
            "data_types": 0,
            "value_constraints": 0
        }
    }
    for record in invalid_records:
        if "_validation_details" in record:
            details = record["_validation_details"]
            for rule, passed in details.items():
                if rule in report["issues_by_rule"] and not passed:
                    report["issues_by_rule"][rule] += 1
            if "invalid_data_types" in details:
                for field in details["invalid_data_types"]:
                    if field not in report["issues_by_field"]:
                        report["issues_by_field"][field] = {"count": 0, "issues": []}
                    report["issues_by_field"][field]["count"] += 1
                    report["issues_by_field"][field]["issues"].append("Invalid data type")
            if "constraint_violations" in details:
                for field, message in details["constraint_violations"].items():
                    if field not in report["issues_by_field"]:
                        report["issues_by_field"][field] = {"count": 0, "issues": []}
                    report["issues_by_field"][field]["count"] += 1
                    report["issues_by_field"][field]["issues"].append(f"Constraint violation: {message}")
    return report
