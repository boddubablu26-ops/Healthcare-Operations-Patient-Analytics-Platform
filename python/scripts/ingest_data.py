"""
High-Performance Ingestion Pipeline
Loads Synthea CSV files into PostgreSQL and/or Embedded DuckDB Database
Project: Healthcare Operations & Patient Analytics
"""
import os
import sys
import glob
import pandas as pd
import duckdb
from dotenv import load_dotenv

load_dotenv()

DATA_DIR = os.getenv("DATA_RAW_DIR", "data/raw")
DUCKDB_PATH = "healthcare.duckdb"

CSV_TABLE_MAP = [
    ("organizations.csv", "organizations"),
    ("payers.csv", "payers"),
    ("providers.csv", "providers"),
    ("patients.csv", "patients"),
    ("encounters.csv", "encounters"),
    ("conditions.csv", "conditions"),
    ("medications.csv", "medications"),
    ("procedures.csv", "procedures"),
    ("observations.csv", "observations"),
    ("careplans.csv", "careplans"),
    ("immunizations.csv", "immunizations")
]

def ingest_to_duckdb(data_dir=DATA_DIR, db_path=DUCKDB_PATH):
    print(f"\n==================================================")
    print(f"Ingesting Synthea CSV datasets into DuckDB: {db_path}")
    print(f"==================================================")
    con = duckdb.connect(db_path)
    
    # Create schemas
    con.execute("CREATE SCHEMA IF NOT EXISTS raw_synthea;")
    con.execute("CREATE SCHEMA IF NOT EXISTS analytics;")

    total_records = 0

    for csv_file, table_name in CSV_TABLE_MAP:
        file_path = os.path.join(data_dir, csv_file)
        target_table = f"raw_synthea.{table_name}"
        if not os.path.exists(file_path):
            print(f"[SKIP] File not found: {file_path}")
            continue

        # Load CSV using DuckDB's ultra-fast auto-detection
        print(f"--> Ingesting {csv_file} -> {target_table}...")
        con.execute(f"DROP TABLE IF EXISTS {target_table};")
        con.execute(f"""
            CREATE TABLE {target_table} AS 
            SELECT * FROM read_csv_auto('{file_path.replace(os.sep, '/')}', header=True);
        """)
        
        count = con.execute(f"SELECT COUNT(*) FROM {target_table};").fetchone()[0]
        total_records += count
        print(f"    Loaded {count:,} rows into {target_table}")

    con.close()
    print(f"\nTotal Ingested Records across all tables: {total_records:,}")
    return total_records

def ingest_to_postgres():
    try:
        import psycopg2
        db_config = {
            "dbname": os.getenv("DB_NAME", "healthcare_db"),
            "user": os.getenv("DB_USER", "postgres"),
            "password": os.getenv("DB_PASSWORD", "postgres"),
            "host": os.getenv("DB_HOST", "localhost"),
            "port": os.getenv("DB_PORT", "5432")
        }
        conn = psycopg2.connect(**db_config)
        print("Connected to PostgreSQL successfully.")
        # COPY logic can be executed here
        conn.close()
    except Exception as e:
        print(f"[INFO] PostgreSQL local server not currently connected: {e}")
        print("[INFO] Embedded analytics database (healthcare.duckdb) ready for all analytical execution.")

if __name__ == "__main__":
    ingest_to_duckdb()
    ingest_to_postgres()
