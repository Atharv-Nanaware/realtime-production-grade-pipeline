import logging
from datetime import datetime

from spark_utils import create_spark_connection, connect_to_kafka, create_selection_df_from_kafka
from cassandra_utils import create_cassandra_connection, create_keyspace, create_table
from data_quality import process_batch_with_quality_checks

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def process_batch(batch_df, batch_id):
    try:
        valid_df, metrics = process_batch_with_quality_checks(batch_df, batch_id)
        if valid_df is not None and valid_df.count() > 0:
            valid_df.write \
                .format("org.apache.spark.sql.cassandra") \
                .mode("append") \
                .option("keyspace", "spark_streaming") \
                .option("table", "created_users") \
                .save()
            logger.info(f"Batch {batch_id}: Successfully wrote {valid_df.count()} records to Cassandra")
        else:
            logger.warning(f"Batch {batch_id}: No valid records to write to Cassandra")
    except Exception as e:
        logger.error(f"Error processing batch {batch_id}: {e}")

if __name__ == "__main__":
    spark_conn = create_spark_connection()
    if spark_conn is None:
        logger.error("Failed to establish Spark connection. Exiting...")
        exit(1)

    kafka_df = connect_to_kafka(spark_conn)
    if kafka_df is None:
        logger.error("Failed to connect to Kafka. Exiting...")
        exit(1)

    selection_df = create_selection_df_from_kafka(kafka_df)
    if selection_df is None:
        logger.error("Failed to process Kafka data. Exiting...")
        exit(1)

    cassandra_session = create_cassandra_connection()
    if cassandra_session is None:
        logger.error("Failed to connect to Cassandra. Exiting...")
        exit(1)

    create_keyspace(cassandra_session)
    create_table(cassandra_session)

    try:
        query = selection_df.writeStream \
            .foreachBatch(process_batch) \
            .option("checkpointLocation", "/tmp/checkpoint") \
            .start()
        logger.info("Streaming query started successfully")
        query.awaitTermination()
    except Exception as e:
        logger.error(f"Error running streaming query: {e}")
    finally:
        if cassandra_session:
            cassandra_session.shutdown()
            logger.info("Cassandra session closed")
