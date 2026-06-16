import os
import sys
import json
from datetime import datetime
import psycopg2
from psycopg2.extras import execute_values

DB_URL = os.getenv("DATABASE_URL", "postgresql://transparency_admin:secure_procure_pass99@localhost:5432/civil_portal_db")
FILE_PATH = "real_data_dump.json"

def stream_and_ingest_real_data(filepath):
    print(f"[📡 Ingestion] Beginning authentic OCDS real-data ingestion from: {filepath}")
    
    if not os.path.exists(filepath):
        print(f"[❌ Error] Real data dump file not found: {filepath}")
        sys.exit(1)
        
    conn = psycopg2.connect(DB_URL)
    cursor = conn.cursor()
    
    # Clean the mock simulation data to show only authentic records in the system
    print("[⚙️ System] Clearing existing simulation ledger records...")
    cursor.execute("TRUNCATE TABLE procurement_contracts CASCADE;")
    cursor.execute("TRUNCATE TABLE contractor_registry CASCADE;")
    conn.commit()
    
    batch = []
    
    # ON CONFLICT Upsert Rule matching our unique partition constraints
    insert_query = """
        INSERT INTO procurement_contracts 
        (tender_id, title, ministry_department, contractor_name, contractor_reg_date, award_date, amount_allocated, bidders_count)
        VALUES %s
        ON CONFLICT (tender_id, award_date) DO UPDATE SET
            title = EXCLUDED.title,
            ministry_department = EXCLUDED.ministry_department,
            contractor_name = EXCLUDED.contractor_name,
            contractor_reg_date = EXCLUDED.contractor_reg_date,
            amount_allocated = EXCLUDED.amount_allocated,
            bidders_count = EXCLUDED.bidders_count,
            ingested_at = CURRENT_TIMESTAMP;
    """
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            releases = json.load(f)
            
            for item in releases:
                release = item.get("compiledRelease", {})
                
                # Extract fields dynamically matching standard OCDS schemas
                tender = release.get("tender", {})
                tender_id = tender.get("id")
                title = tender.get("title")
                buyer_name = release.get("buyer", {}).get("name", "Unknown Buyer")
                
                awards = release.get("awards", [])
                if not awards:
                    continue
                award = awards[0]
                amount = float(award.get("value", {}).get("amount", 0.0))
                
                suppliers = award.get("suppliers", [])
                if not suppliers:
                    continue
                supplier = suppliers[0]
                contractor_name = supplier.get("name", "Unknown Contractor")
                
                bidders_count = len(tender.get("tenderers", []))
                
                award_date_str = award.get("date")
                if award_date_str:
                    award_date = datetime.strptime(award_date_str, "%Y-%m-%d").date()
                else:
                    award_date = datetime.now().date()
                    
                reg_date_str = supplier.get("registration_date")
                if reg_date_str:
                    contractor_reg_date = datetime.strptime(reg_date_str, "%Y-%m-%d").date()
                else:
                    contractor_reg_date = None
                    
                batch.append((
                    tender_id, title, buyer_name,
                    contractor_name, contractor_reg_date, award_date,
                    amount, bidders_count
                ))
                
            if batch:
                execute_values(cursor, insert_query, batch)
                conn.commit()
                print(f"[⚡ Commit] Ingested {len(batch)} authentic public procurement records.")
                
    except Exception as e:
        print(f"[❌ Ingestion Error] Real data commit failed: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()
        
    print("[⚙️ System] Real-data ingestion process completed.")

if __name__ == "__main__":
    print("[🚀 Control Center] Activating Real OCDS Data Ingestion Worker...")
    stream_and_ingest_real_data(FILE_PATH)
