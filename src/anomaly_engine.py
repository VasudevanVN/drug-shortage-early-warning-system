import os
import logging
import pandas as pd
import numpy as np
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment configs
load_dotenv()
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

DB_URI = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
engine = create_engine(DB_URI)

def run_anomaly_detection():
    logging.info("🧠 Initializing Anomaly Detection Engine...")

    # Aggregated monthly event counts from the Star Schema
    # Wrapping raw query strings inside text() is standard practice for modern SQLAlchemy
    query = text("""
        SELECT 
            d.generic_name,
            DATE_TRUNC('month', f.event_date)::DATE as alert_month,
            COUNT(*) as actual_event_count
        FROM fact_regulatory_events f
        JOIN dim_drug d ON f.drug_id = d.drug_id
        GROUP BY d.generic_name, 2
        ORDER BY d.generic_name, alert_month ASC;
    """)
    
    # Securely open an explicit connection block using contextual handlers
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    
    if df.empty:
        logging.warning("No data found in fact table to analyze.")
        return

    logging.info(f"Processing historical timelines for {df['generic_name'].nunique()} unique medications...")

    # Statistical Analysis: Calculate 3-month rolling mean and standard deviation per drug
    df['historical_rolling_mean'] = df.groupby('generic_name')['actual_event_count'].transform(
        lambda x: x.rolling(3, min_periods=1).mean()
    )
    
    df['historical_rolling_std'] = df.groupby('generic_name')['actual_event_count'].transform(
        lambda x: x.rolling(3, min_periods=1).std()
    )

    # Calculate Z-Score safely
    df['historical_rolling_std'] = df['historical_rolling_std'].replace(0, np.nan)
    df['z_score'] = (df['actual_event_count'] - df['historical_rolling_mean']) / df['historical_rolling_std']
    df['z_score'] = df['z_score'].fillna(0)

    # Filter for anomalies (Using >= 1.5 to maximize the signal from our current database pool)
    anomalies = df[df['z_score'] >= 1.5].copy()

    if not anomalies.empty:
        anomalies_to_load = anomalies.drop(columns=['historical_rolling_std'])
        
        # Write back using explicit connection strings to avoid OptionEngine injection issues
        with engine.connect() as conn:
            with conn.begin():
                anomalies_to_load.to_sql('high_risk_alerts', conn, if_exists='append', index=False)
                
        logging.info(f"🚨 SUCCESS: Identified and logged {len(anomalies_to_load)} early-warning anomalies!")
    else:
        logging.info("✅ Scan complete. No active drug anomalies detected this period.")

if __name__ == "__main__":
    run_anomaly_detection()