"""
Airflow DAG para o pipeline Suri.

Para usar:
  1. Copie este arquivo para a pasta 'dags/' do seu Airflow.
  2. Certifique-se de que os demais módulos (fetch, filter_messages, lgpd, classify, pipeline)
     estão no PYTHONPATH do Airflow (ex: em DAG_FOLDER ou em um pacote instalado).
  3. Configure CHATBOT_URL, API_TOKEN e GOOGLE_API_KEY como Airflow Variables ou no .env
     acessível pelo worker.

Agendamento padrão: toda segunda-feira às 08:00 (semanal).
Para execução diária, substitua schedule_interval por "@daily".
"""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from airflow import DAG
from airflow.operators.python import PythonOperator

import pipeline

with DAG(
    dag_id="suri_pipeline",
    description="Busca, filtra, anonimiza e classifica mensagens de hóspedes (Suri chatbot)",
    schedule_interval="0 8 * * 1",  # toda segunda às 08:00 — "@daily" para diário
    start_date=datetime(2026, 6, 22),
    catchup=False,
    tags=["suri", "hospedagem", "lgpd"],
) as dag:

    run_pipeline = PythonOperator(
        task_id="run_pipeline",
        python_callable=pipeline.run,
    )
