import os
import json
import random
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import execute_values

DB_URL = os.getenv("DATABASE_URL", "postgresql://transparency_admin:secure_procure_pass99@localhost:5432/civil_portal_db")
FILE_PATH = "historical_data.jsonl"

def generate_mock_historical_data(filepath, count=2500):
    """Generates a mock historical OCDS jsonl dataset file for testing bulk ingestion."""
    print(f"[✏️ Setup] Generating {count} mock OCDS releases in '{filepath}'...")
    
    # Pre-defined mock data pools
    contractors = [
        "Apex Construction Group Ltd.", "Himalayan Builders Ltd.", 
        "Siddharth Infra Corp", "Janaki Tube-well & Boring Contractors",
        "Karnali Infra Ventures", "Rara Highway Construction",
        "Bagmati Drainage Solutions", "Everest Hydro Power JV"
    ]
    buyers = [
        "Department of Roads - Ministry of Physical Infrastructure",
        "Lalitpur Metropolitan City Office",
        "Ministry of Water Supply",
        "Department of Health Services",
        "Kathmandu Metropolitan City Office",
        "Nepal Electricity Authority"
    ]
    project_types = [
        "Rehabilitation of Expressway Section", "Installation of smart traffic systems",
        "Rural Water Supply Tube-well Drilling", "Construction of Hospital Ward Building",
        "Electrification Grid Expansion", "Sewerage Line Construction",
        "Repaving of Urban Corridors", "Suspension Bridge Installation"
    ]
    
    with open(filepath, 'w', encoding='utf-8') as f:
        start_date = datetime(2024, 1, 1)
        for i in range(count):
            tender_id = f"TENDER-HIST-{i:04d}"
            title = f"{random.choice(project_types)} - Part {i}"
            buyer = random.choice(buyers)
            contractor = random.choice(contractors)
            
            # 10% chance of single bidder
            bidders = 1 if random.random() < 0.10 else random.randint(2, 6)
            
            # Award date spread across 2024, 2025 and 2026
            award_days_offset = random.randint(0, 1000)
            award_dt = start_date + timedelta(days=award_days_offset)
            
            # Cap the generated date at 2026-06-16 (basic chronology integrity)
            max_date = datetime(2026, 6, 16)
            if award_dt > max_date:
                valid_days = (max_date - start_date).days
                award_dt = start_date + timedelta(days=random.randint(0, valid_days))
            
            release = {
                "compiledRelease": {
                    "tender": {
                        "id": tender_id,
                        "title": title,
                        "tenderers": [{"id": f"SUPL-{j}", "name": f"Supplier {j}"} for j in range(bidders)]
                    },
                    "buyer": {
                        "name": buyer
                    },
                    "awards": [
                        {
                            "id": f"AWARD-HIST-{i:04d}",
                            "status": "active",
                            "date": award_dt.strftime("%Y-%m-%d"),
                            "value": {
                                "amount": float(random.randint(50, 5000) * 10000),
                                "currency": "NPR"
                            },
                            "suppliers": [
                                {
                                    "id": f"SUPL-{random.randint(0, 100)}", 
                                    "name": contractor
                                }
                            ]
                        }
                    ]
                }
            }
            f.write(json.dumps(release) + "\n")
    print(f"[⚙️ Setup] Mock historical dataset generated successfully.")

def stream_and_ingest_historical_data(filepath):
    """Reads OCDS jsonl releases line-by-line using a generator and commits in batches of 1,000."""
    print(f"[📡 Ingestion] Beginning memory-optimized historical ingestion from: {filepath}")
    
    conn = psycopg2.connect(DB_URL)
    cursor = conn.cursor()
    
    batch = []
    batch_size = 1000
    total_ingested = 0
    
    # ON CONFLICT Upsert Rule
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
            for line in f:
                if not line.strip():
                    continue
                    
                try:
                    payload = json.loads(line)
                    release = payload.get("compiledRelease", {})
                    
                    # Extract OCDS fields
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
                        
                    # 15% probability trap for missing contractor_reg_date
                    reg_date_str = supplier.get("registration_date")
                    if reg_date_str:
                        contractor_reg_date = datetime.strptime(reg_date_str, "%Y-%m-%d").date()
                    else:
                        if random.random() < 0.15:
                            delta = random.randint(0, 14)
                            contractor_reg_date = award_date - timedelta(days=delta)
                        else:
                            delta = random.randint(90, 365)
                            contractor_reg_date = award_date - timedelta(days=delta)
                            
                    batch.append((
                        tender_id, title, buyer_name,
                        contractor_name, contractor_reg_date, award_date,
                        amount, bidders_count
                    ))
                    
                    # Commit in batches of 1,000
                    if len(batch) >= batch_size:
                        execute_values(cursor, insert_query, batch)
                        conn.commit()
                        total_ingested += len(batch)
                        print(f"  [⚡ Batch Commit] Ingested {total_ingested} records...")
                        batch = []
                        
                except Exception as e:
                    print(f"  [❌ Row Error] Skipping line due to parse failure: {e}")
                    
            # Ingest remaining
            if batch:
                execute_values(cursor, insert_query, batch)
                conn.commit()
                total_ingested += len(batch)
                print(f"  [⚡ Batch Commit] Ingested remaining {len(batch)} records (Total: {total_ingested}).")
                
    except Exception as e:
        print(f"[❌ Ingestion Error] Bulk commit interrupted: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()
        
    print(f"[⚙️ System] Ingestion process completed. Total: {total_ingested} OCDS records ingested.")

if __name__ == "__main__":
    print("[🚀 Control Center] Activating Phase 1 Historical Ingestion Core...")
    if not os.path.exists(FILE_PATH):
        generate_mock_historical_data(FILE_PATH, count=2500)
    stream_and_ingest_historical_data(FILE_PATH)
