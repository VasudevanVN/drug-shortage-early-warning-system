import os
import time
import logging
import requests
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

load_dotenv()

API_KEY = os.getenv("FDA_API_KEY")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

DB_URI = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
engine = create_engine(DB_URI)
BASE_URL = "https://api.fda.gov/drug"

def fetch_fda_data_paginated(endpoint, search_query, total_records_needed=200):
    results = []
    limit = 100
    skip = 0
    
    while skip < total_records_needed:
        url = f"{BASE_URL}/{endpoint}.json"
        params = {
            'api_key': API_KEY,
            'limit': limit,
            'skip': skip
        }
        if search_query:
            params['search'] = search_query
        logging.info(f"🔍 Requesting {limit} records from '{endpoint}' (skip: {skip})...")
        
        try:
            response = requests.get(url, params=params, timeout=30)
            if response.status_code == 200:
                data = response.json()
                batch = data.get('results', [])
                results.extend(batch)
                if len(batch) < limit:
                    break
                skip += limit
                time.sleep(0.3)
            elif response.status_code == 404:
                logging.warning(f"⚠️ No records found for query on '{endpoint}'.")
                break
            else:
                logging.error(f"❌ API Error {response.status_code}: {response.text}")
                break
        except Exception as e:
            logging.error(f"❌ Connection error: {e}")
            break
            
    return results

def run_ingestion_pipeline():
    logging.info("🚀 Starting openFDA Ingestion Fix...")

    # --- 1. RECALLS ---
    recall_query = 'report_date:[20230101 TO 20251231] AND (classification:"Class I" OR classification:"Class II")'
    raw_recalls = fetch_fda_data_paginated('enforcement', recall_query, total_records_needed=200)
    if raw_recalls:
        df_recalls = pd.json_normalize(raw_recalls)
        keep_cols = ['recall_number', 'status', 'classification', 'product_description', 'reason_for_recalls', 'report_date', 'openfda.generic_name', 'openfda.manufacturer_name']
        df_recalls = df_recalls[[c for c in keep_cols if c in df_recalls.columns]]
        df_recalls.to_sql('stg_fda_recalls', engine, if_exists='replace', index=False)
        logging.info(f"✅ Staged {len(df_recalls)} records to 'stg_fda_recalls'.")

    # --- 2. ADVERSE EVENTS ---
    # Shifted to a highly stable historical year (2023) and removed complex sub-array filters
    event_query = 'receivedate:[20230101 TO 20231231]'
    raw_events = fetch_fda_data_paginated('event', event_query, total_records_needed=200)
    if raw_events:
        df_events_raw = pd.json_normalize(raw_events)
        if 'patient.drug' in df_events_raw.columns:
            df_events_exploded = df_events_raw.explode('patient.drug')
            df_events = pd.json_normalize(df_events_exploded['patient.drug'])
            df_events['safetyreportid'] = df_events_exploded['safetyreportid'].values
            df_events['receivedate'] = df_events_exploded['receivedate'].values
            
            event_keep = ['safetyreportid', 'receivedate', 'medicinalproduct', 'openfda.generic_name', 'openfda.manufacturer_name']
            df_events = df_events[[c for c in event_keep if c in df_events.columns]]
            df_events.to_sql('stg_fda_events', engine, if_exists='replace', index=False)
            logging.info(f"✅ Staged {len(df_events)} records to 'stg_fda_events'.")

    # --- 3. DRUG SHORTAGES ---
    # Passing None for search_query pulls all available historical shortage records directly
    raw_shortages = fetch_fda_data_paginated('shortage', search_query=None, total_records_needed=200)
    if raw_shortages:
        df_shortages = pd.json_normalize(raw_shortages)
        df_shortages.to_sql('stg_fda_shortages', engine, if_exists='replace', index=False)
        logging.info(f"✅ Staged {len(df_shortages)} records to 'stg_fda_shortages'.")

    logging.info("🏁 Phase 1 Ingestion Completed Cleanly.")

if __name__ == "__main__":
    run_ingestion_pipeline()