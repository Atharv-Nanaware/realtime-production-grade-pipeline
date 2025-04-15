import logging
from cassandra.cluster import Cluster

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def create_cassandra_connection():
    try:
        cluster = Cluster(["cassandra"])
        session = cluster.connect()
        logger.info("Cassandra connection created successfully")
        return session
    except Exception as e:
        logger.error(f"Error creating Cassandra connection: {e}")
        return None

def create_keyspace(session):
    try:
        session.execute("""
            CREATE KEYSPACE IF NOT EXISTS spark_streaming
            WITH REPLICATION = {'class': 'SimpleStrategy', 'replication_factor': 1}
        """)
        logger.info("Keyspace created successfully")
    except Exception as e:
        logger.error(f"Error creating keyspace: {e}")

def create_table(session):
    try:
        session.execute("""
            CREATE TABLE IF NOT EXISTS spark_streaming.created_users (
                first_name TEXT,
                last_name TEXT,
                gender TEXT,
                address TEXT,
                post_code TEXT,
                email TEXT,
                username TEXT PRIMARY KEY,
                dob TEXT,
                registered_date TEXT,
                phone TEXT,
                picture TEXT
            );
        """)
        logger.info("Table created successfully")
    except Exception as e:
        logger.error(f"Error creating table: {e}")

def save_to_cassandra(batch_df, batch_id):
    try:
        batch_df.write \
            .format("org.apache.spark.sql.cassandra") \
            .mode("append") \
            .option("keyspace", "spark_streaming") \
            .option("table", "created_users") \
            .save()
        
        logger.info(f"Batch {batch_id} saved to Cassandra successfully")
        return True
    except Exception as e:
        logger.error(f"Error saving batch {batch_id} to Cassandra: {e}")
        return False
