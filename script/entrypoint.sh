#!/bin/bash
set -e


if [ -f "/opt/airflow/requirements.txt" ]; then
  python -m pip install --upgrade pip
  pip install -r /opt/airflow/requirements.txt
fi

# Initialize the Airflow database
airflow db upgrade


airflow users list | grep -q "admin" || \
airflow users create \
  --username admin \
  --firstname admin \
  --lastname admin \
  --role Admin \
  --email admin@example.com \
  --password admin

# Starts the Airflow webserver
exec airflow webserver