FROM apache/airflow:2.8.4-python3.11

USER airflow

# Install dependencies
COPY requirements.txt /requirements.txt
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r /requirements.txt

#PYTHONPATH for custom code
ENV PYTHONPATH="/opt/airflow/constants:/opt/airflow/pipelines:${PYTHONPATH}"
