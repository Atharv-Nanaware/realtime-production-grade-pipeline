import logging
import re
from pyspark.sql.functions import col, when, length, regexp_extract, lit
from pyspark.sql.types import StringType

from constants.validation import *

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def apply_data_quality_checks(df):
    logger.info("Applying data quality checks...")

    metrics = {
        "total_records": df.count(),
        "invalid_records": 0,
        "validation_failures": {
            "required_fields": 0,
            "email_format": 0,
            "date_format": 0,
            "gender_values": 0,
            "username_length": 0
        }
    }

    validated_df = df.withColumn("_is_valid", lit(True))

    for field in REQUIRED_FIELDS:
        validated_df = validated_df.withColumn(
            "_is_valid",
            when((col(field).isNull() | (col(field) == "")), lit(False)).otherwise(col("_is_valid"))
        )
        req_field_failures = validated_df.filter((col(field).isNull() | (col(field) == "")) & col("_is_valid") == False).count()
        metrics["validation_failures"]["required_fields"] += req_field_failures

    validated_df = validated_df.withColumn(
        "_is_valid",
        when(
            (~col("email").isNull() & (col("email") != "")) &
            (regexp_extract(col("email"), EMAIL_PATTERN, 0) != col("email")),
            lit(False)
        ).otherwise(col("_is_valid"))
    )
    email_failures = validated_df.filter(
        (~col("email").isNull() & (col("email") != "")) &
        (regexp_extract(col("email"), EMAIL_PATTERN, 0) != col("email")) &
        col("_is_valid") == False
    ).count()
    metrics["validation_failures"]["email_format"] += email_failures

    validated_df = validated_df.withColumn(
        "_is_valid",
        when(
            (~col("registered_date").isNull() & (col("registered_date") != "")) &
            (regexp_extract(col("registered_date"), DATE_PATTERN, 0) != col("registered_date")),
            lit(False)
        ).otherwise(col("_is_valid"))
    )
    date_failures = validated_df.filter(
        (~col("registered_date").isNull() & (col("registered_date") != "")) &
        (regexp_extract(col("registered_date"), DATE_PATTERN, 0) != col("registered_date")) &
        col("_is_valid") == False
    ).count()
    metrics["validation_failures"]["date_format"] += date_failures

    validated_df = validated_df.withColumn(
        "_is_valid",
        when(
            (~col("gender").isNull() & (col("gender") != "")) &
            (~col("gender").isin(GENDER_VALUES)),
            lit(False)
        ).otherwise(col("_is_valid"))
    )
    gender_failures = validated_df.filter(
        (~col("gender").isNull() & (col("gender") != "")) &
        (~col("gender").isin(GENDER_VALUES)) &
        col("_is_valid") == False
    ).count()
    metrics["validation_failures"]["gender_values"] += gender_failures

    validated_df = validated_df.withColumn(
        "_is_valid",
        when(
            (~col("username").isNull() & (col("username") != "")) &
            ((length(col("username")) < 3) | (length(col("username")) > 30)),
            lit(False)
        ).otherwise(col("_is_valid"))
    )
    username_failures = validated_df.filter(
        (~col("username").isNull() & (col("username") != "")) &
        ((length(col("username")) < 3) | (length(col("username")) > 30)) &
        col("_is_valid") == False
    ).count()
    metrics["validation_failures"]["username_length"] += username_failures

    valid_df = validated_df.filter(col("_is_valid") == True).drop("_is_valid")
    invalid_df = validated_df.filter(col("_is_valid") == False).drop("_is_valid")

    metrics["invalid_records"] = invalid_df.count()
    metrics["valid_records"] = valid_df.count()

    logger.info(f"Data quality check results: {metrics['valid_records']} valid records, {metrics['invalid_records']} invalid records")

    return valid_df, invalid_df, metrics

def process_batch_with_quality_checks(batch_df, batch_id):
    try:
        valid_df, invalid_df, metrics = apply_data_quality_checks(batch_df)
        logger.info(f"Batch {batch_id} metrics: {metrics}")
        if metrics["invalid_records"] > 0:
            logger.warning(f"Batch {batch_id} has {metrics['invalid_records']} invalid records")
        return valid_df, metrics
    except Exception as e:
        logger.error(f"Error processing batch {batch_id}: {e}")
        return None, {"error": str(e)}
