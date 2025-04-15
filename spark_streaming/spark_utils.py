import logging
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json
from pyspark.sql.types import StructType, StructField, StringType

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def create_spark_connection():
    try:
        spark = SparkSession.builder \
            .appName("SparkDataStreaming") \
            .config("spark.jars.packages", "com.datastax.spark:spark-cassandra-connector_2.12:3.5.1,"
                                           "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1") \
            .config("spark.cassandra.connection.host", "cassandra_db") \
            .getOrCreate()
        spark.sparkContext.setLogLevel("ERROR")
        logger.info("Spark connection created successfully")
        return spark
    except Exception as e:
        logger.error(f"Error creating Spark connection: {e}")
        return None

def connect_to_kafka(spark_conn):
    try:
        kafka_stream = spark_conn.readStream \
            .format("kafka") \
            .option("kafka.bootstrap.servers", "broker:9092") \
            .option("subscribe", "user_profile_stream") \
            .option("startingOffsets", "earliest") \
            .load()
        logger.info("Kafka dataframe created successfully")
        return kafka_stream
    except Exception as e:
        logger.error(f"Error creating Kafka dataframe: {e}")
        return None

def define_schema():
    return StructType([
        StructField("first_name", StringType(), True),
        StructField("last_name", StringType(), True),
        StructField("gender", StringType(), True),
        StructField("address", StringType(), True),
        StructField("post_code", StringType(), True),
        StructField("email", StringType(), True),
        StructField("username", StringType(), True),
        StructField("dob", StringType(), True),
        StructField("registered_date", StringType(), True),
        StructField("phone", StringType(), True),
        StructField("picture", StringType(), True),
    ])

def create_selection_df_from_kafka(kafka_df):
    schema = define_schema()
    try:
        selection_df = kafka_df.selectExpr("CAST(value AS STRING)") \
            .select(from_json(col("value"), schema).alias("data")) \
            .select("data.*")
        logger.info("Selection dataframe created successfully")
        return selection_df
    except Exception as e:
        logger.error(f"Error creating selection dataframe: {e}")
        return None
