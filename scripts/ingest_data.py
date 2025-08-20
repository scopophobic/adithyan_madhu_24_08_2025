# Filename: scripts/ingest_data.py
import pandas as pd
from sqlalchemy.orm import Session
import sys
import os
import logging

# --- Configuration ---
# Set up basic logging to see output in the console
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# This line allows the script to import modules from the parent 'app' directory.
# It adds the project's root directory to Python's path.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# --- Database and Model Imports ---
# We import our database session factory and table models from the app.models module.
try:
    from app.models import SessionLocal, StoreStatus, StoreHours, StoreTimezone, engine, Base
except ImportError:
    logging.error("Could not import from app.models. Make sure the file exists and there are no circular imports.")
    sys.exit(1)

# --- File Paths ---
# Define the paths to your CSV files. Assumes they are in a 'data/input' directory
# relative to the project root.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATUS_CSV_PATH = os.path.join(BASE_DIR, 'data', 'input', 'store_status.csv')
HOURS_CSV_PATH = os.path.join(BASE_DIR, 'data', 'input', 'menu_hours.csv')
TIMEZONE_CSV_PATH = os.path.join(BASE_DIR, 'data', 'input', 'timezones.csv')


def ingest_data():
    """
    Connects to the database, reads data from CSV files, and performs a bulk insert
    into the corresponding tables.
    """
    # Create all tables defined in models.py if they don't already exist.
    # This is safe to run multiple times.
    logging.info("Initializing database tables...")
    Base.metadata.create_all(bind=engine)

    # Obtain a new database session.
    db: Session = SessionLocal()
    logging.info("Database session started.")

    try:
        # --- 1. Ingest Store Timezones ---
        logging.info(f"Reading timezones from {TIMEZONE_CSV_PATH}...")
        tz_df = pd.read_csv(TIMEZONE_CSV_PATH)
        # Ensure the column name matches the model's attribute.
        tz_df.rename(columns={'timezone_str': 'timezone_str'}, inplace=True, errors='ignore')
        # Convert the DataFrame to a list of dictionaries for bulk insertion.
        tz_records = tz_df.to_dict(orient="records")
        if tz_records:
            db.bulk_insert_mappings(StoreTimezone, tz_records)
            logging.info(f"Successfully inserted {len(tz_records)} timezone records.")

        # --- 2. Ingest Store Business Hours ---
        logging.info(f"Reading business hours from {HOURS_CSV_PATH}...")
        hours_df = pd.read_csv(HOURS_CSV_PATH)
        hours_records = hours_df.to_dict(orient="records")
        if hours_records:
            db.bulk_insert_mappings(StoreHours, hours_records)
            logging.info(f"Successfully inserted {len(hours_records)} business hour records.")

        # --- 3. Ingest Store Status ---
        logging.info(f"Reading store status data from {STATUS_CSV_PATH}...")
        status_df = pd.read_csv(STATUS_CSV_PATH)
        # It's crucial to ensure the timestamp column is in the correct format.
        # Pandas' to_datetime can often handle this automatically.
        status_df['timestamp_utc'] = pd.to_datetime(status_df['timestamp_utc'])
        status_records = status_df.to_dict(orient="records")
        if status_records:
            db.bulk_insert_mappings(StoreStatus, status_records)
            logging.info(f"Successfully inserted {len(status_records)} store status records.")

        # If all insertions are successful, commit the transaction to the database.
        db.commit()
        logging.info("All data has been successfully committed to the database.")

    except FileNotFoundError as e:
        logging.error(f"Error: The file was not found - {e}. Please check the file paths.")
        db.rollback() # Rollback any partial changes.
    except Exception as e:
        logging.error(f"An error occurred during data ingestion: {e}")
        # In case of any error, rollback the entire transaction to maintain data integrity.
        db.rollback()
    finally:
        # Always close the session to free up database connections.
        logging.info("Database session closed.")
        db.close()

if __name__ == "__main__":
    ingest_data()
