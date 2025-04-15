import requests
import logging
import json
from kafka import KafkaProducer

from pipelines.data_validator import *

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def extract_data(**kwargs):
    try:
        num_users = 100
        response = requests.get(f"https://randomuser.me/api/?results={num_users}")
        response.raise_for_status()
        users_data = response.json()['results']
        logging.info(f"Fetched {num_users} users successfully.")
        kwargs['ti'].xcom_push(key='raw_data', value=users_data)
    except requests.RequestException as e:
        logging.error(f"Error fetching data from API: {e}")
        raise


def transform_data(**kwargs):
    try:
        ti = kwargs['ti']
        raw_data_list = ti.xcom_pull(task_ids='extract_data', key='raw_data')

        formatted_users = []
        for raw_data in raw_data_list:
            location = raw_data['location']
            formatted_data = {
                'first_name': raw_data['name']['first'],
                'last_name': raw_data['name']['last'],
                'gender': raw_data['gender'],
                'address': f"{location['street']['number']} {location['street']['name']}, "
                           f"{location['city']}, {location['state']}, {location['country']}",
                'post_code': location['postcode'],
                'email': raw_data['email'],
                'username': raw_data['login']['username'],
                'dob': raw_data['dob']['date'],
                'registered_date': raw_data['registered']['date'],
                'phone': raw_data['phone'],
                'picture': raw_data['picture']['medium'],
            }
            formatted_users.append(formatted_data)

        logging.info(f"Formatted {len(formatted_users)} users successfully.")
        ti.xcom_push(key='formatted_data', value=formatted_users)
    except KeyError as e:
        logging.error(f"Error formatting data: Missing key {e}")
        raise


def validate_data(**kwargs):
    try:
        ti = kwargs['ti']
        formatted_users = ti.xcom_pull(task_ids='transform_data', key='formatted_data')

        valid_users, invalid_users, validation_summary = validate_batch(formatted_users)

        logging.info(f"Data validation summary: {validation_summary['valid_records']} valid, "
                     f"{validation_summary['invalid_records']} invalid records")

        if invalid_users:
            ti.xcom_push(key='invalid_data', value=invalid_users)

            validation_report = get_validation_report(invalid_users)
            logging.warning(f"Validation report: {json.dumps(validation_report, indent=2)}")

            logging.warning(f"Found {len(invalid_users)} invalid records that will not be sent to Kafka")

        ti.xcom_push(key='validated_data', value=valid_users)
        logging.info(f"Data validation completed. {len(valid_users)} records ready for loading.")

    except Exception as e:
        logging.error(f"Error validating data: {e}")
        raise


def load_data(**kwargs):
    producer = KafkaProducer(bootstrap_servers='broker:9092', max_block_ms=5000)
    try:
        ti = kwargs['ti']
        validated_users = ti.xcom_pull(task_ids='data_validation', key='validated_data')

        for user in validated_users:
            producer.send('user_profile_stream', json.dumps(user).encode('utf-8'))
            logging.info(f"Sent user {user['username']} to Kafka.")

        producer.flush()
        logging.info(f"Successfully sent {len(validated_users)} users to Kafka.")
    except Exception as e:
        logging.error(f"Error sending data to Kafka: {e}")
        raise
