from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import os
import  sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from pipelines.etl_pipeline import extract_data,transform_data,load_data,validate_data

default_args = {
    'owner': 'data_engineer',
    'start_date': datetime(2025, 2, 11, 11, 0),
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
}

with DAG('realtime_user_streaming_pipeline',
         default_args=default_args,
         schedule_interval='@daily',
         catchup=False) as dag:

    extract_task = PythonOperator(
        task_id='extract_data',
        python_callable=extract_data,
        provide_context=True
    )

    transform_task = PythonOperator(
        task_id='transform_data',
        python_callable=transform_data,
        provide_context=True
    )

    validation_task=PythonOperator(
        task_id= 'data_validation',
        python_callable=validate_data,
        provide_context=True
    )

    streaming_task = PythonOperator(
        task_id='load_data',
        python_callable=load_data,
        provide_context=True
    )

    extract_task >> transform_task >> validation_task >> streaming_task