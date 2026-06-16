import os
import sys
import json
import random
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import execute_values

DB_URL = os.getenv("DATABASE_URL", "postgresql://transparency_admin:secure_procure_pass99@localhost:5432/civil_portal_db")
FILE_PATH = "historical_data.jsonl"

def ingest_historical_bulk():
    print(f"[📡 Ingestion] Starting historical bulk ingestion from: {FILE_PATH}")
    
    if not os.path.exists(FILE_PATH):
        print(f"[❌ Error] Historical data file not found: {FILE_PATH}")
        sys.exit(1)
        
    conn = psycopg2.connect(DB_URL)
    cursor = conn.cursor()
    
    batch_contracts = []
    batch_registry = {}  # company_name -> registration_date
    batch_size = 1000
    total_ingested = 0
    
    registry_query = """
        INSERT INTO contractor_registry (company_name, registration_date)
        VALUES %s
        ON CONFLICT (company_name) DO UPDATE SET
            registration_date = LEAST(contractor_registry.registration_date, EXCLUDED.registration_date);
    """
    
    insert_query = """
        INSERT INTO procurement_contracts 
        (tender_id, title, ministry_department, contractor_name, contractor_reg_date, award_date, amount_allocated, bidders_count, tender_status, submission_deadline)
        VALUES %s
        ON CONFLICT (tender_id, award_date) DO UPDATE SET
            title = EXCLUDED.title,
            ministry_department = EXCLUDED.ministry_department,
            contractor_name = EXCLUDED.contractor_name,
            contractor_reg_date = EXCLUDED.contractor_reg_date,
            amount_allocated = EXCLUDED.amount_allocated,
            bidders_count = EXCLUDED.bidders_count,
            tender_status = EXCLUDED.tender_status,
            submission_deadline = EXCLUDED.submission_deadline,
            ingested_at = CURRENT_TIMESTAMP;
    """
    
    try:
        with open(FILE_PATH, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                    
                try:
                    payload = json.loads(line)
                    release = payload.get("compiledRelease", {})
                    
                    # 1. Extract tender details
                    tender = release.get("tender", {})
                    tender_id = tender.get("id")
                    title = tender.get("title")
                    
                    # 2. Extract buyer name
                    buyer_name = release.get("buyer", {}).get("name", "Unknown Buyer")
                    
                    # 3. Extract award details
                    awards = release.get("awards", [])
                    if not awards:
                        continue
                    award = awards[0]
                    amount_allocated = float(award.get("value", {}).get("amount", 0.0))
                    
                    # 4. Extract supplier details
                    suppliers = award.get("suppliers", [])
                    if not suppliers:
                        continue
                    supplier = suppliers[0]
                    contractor_name = supplier.get("name", "Unknown Contractor")
                    
                    # 5. Determine bidders count
                    bidders_count = tender.get("numberOfBidders")
                    if bidders_count is None:
                        bidders_count = len(tender.get("tenderers", []))
                    if bidders_count == 0:
                        bidders_count = 1
                        
                    # 6. Parse award date
                    award_date_str = award.get("date")
                    if award_date_str:
                        award_date = datetime.strptime(award_date_str.split("T")[0], "%Y-%m-%d").date()
                    else:
                        award_date = datetime.now().date()
                        
                    # 7. Fault-tolerance registration date
                    reg_date_str = supplier.get("registration_date")
                    if reg_date_str:
                        contractor_reg_date = datetime.strptime(reg_date_str.split("T")[0], "%Y-%m-%d").date()
                    else:
                        # Fallback registration date
                        contractor_reg_date = award_date - timedelta(days=90)
                        
                    # 8. Set past submission deadline
                    submission_deadline = award_date - timedelta(days=30)
                    
                    # Collect registry and contract data
                    if contractor_name:
                        if contractor_name not in batch_registry or contractor_reg_date < batch_registry[contractor_name]:
                            batch_registry[contractor_name] = contractor_reg_date
                            
                    batch_contracts.append((
                        tender_id, title, buyer_name,
                        contractor_name, contractor_reg_date, award_date,
                        amount_allocated, bidders_count, 'AWARDED', submission_deadline
                    ))
                    
                    # Flush batch when size is reached
                    if len(batch_contracts) >= batch_size:
                        # Insert registry batch first (deduplicated)
                        registry_data = [(name, reg_date) for name, reg_date in batch_registry.items()]
                        execute_values(cursor, registry_query, registry_data)
                        
                        # Insert contracts batch
                        execute_values(cursor, insert_query, batch_contracts)
                        conn.commit()
                        
                        total_ingested += len(batch_contracts)
                        print(f"  [⚡ Batch Commit] Ingested {total_ingested} records...")
                        batch_contracts = []
                        batch_registry = {}
                        
                except Exception as row_err:
                    print(f"  [❌ Row Error] Skipping record due to error: {row_err}")
                    
            # Flush remaining records
            if batch_contracts:
                registry_data = [(name, reg_date) for name, reg_date in batch_registry.items()]
                if registry_data:
                    execute_values(cursor, registry_query, registry_data)
                    
                execute_values(cursor, insert_query, batch_contracts)
                conn.commit()
                total_ingested += len(batch_contracts)
                print(f"  [⚡ Batch Commit] Ingested remaining {len(batch_contracts)} records (Total: {total_ingested}).")
                
    except Exception as e:
        print(f"[❌ Ingestion Error] Bulk commit failed: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        cursor.close()
        conn.close()
        
    print(f"[⚙️ System] Historical bulk ingestion completed. Total: {total_ingested} records processed.")

if __name__ == "__main__":
    print("[🚀 Control Center] Activating Historical Bulk Ingest...")
    ingest_historical_bulk()
