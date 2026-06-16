import os
import time
import json
import random
import requests
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import execute_values

# Connect to our local Docker database ledger
DB_URL = os.getenv("DATABASE_URL", "postgresql://transparency_admin:secure_procure_pass99@localhost:5432/civil_portal_db")
STREAM_URL = os.getenv("STREAM_URL", "http://localhost:8000/api/v1/contracts/mock-ocds-stream")

def init_db():
    """Initializes the Phase 1 partitioned schema, indexes, and trigger."""
    conn = psycopg2.connect(DB_URL)
    cursor = conn.cursor()
    
    # 1. Drop existing tables if they exist
    cursor.execute("DROP TABLE IF EXISTS procurement_contracts CASCADE;")
    cursor.execute("DROP TABLE IF EXISTS contractor_registry CASCADE;")
    
    # 2. Create the centralized registry table
    cursor.execute("""
        CREATE TABLE contractor_registry (
            company_name VARCHAR(150) PRIMARY KEY,
            registration_date DATE NOT NULL
        );
    """)
    
    # 3. Create the main parent table partitioned by range on award_date
    cursor.execute("""
        CREATE TABLE procurement_contracts (
            id SERIAL,
            tender_id VARCHAR(150) NOT NULL,
            title TEXT NOT NULL,
            ministry_department TEXT,
            contractor_name TEXT,
            contractor_reg_date DATE,
            award_date DATE,
            amount_allocated NUMERIC(15, 2) NOT NULL,
            bidders_count INT NOT NULL,
            is_red_flagged BOOLEAN DEFAULT FALSE,
            red_flag_reason TEXT,
            ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            tender_status VARCHAR(20) DEFAULT 'AWARDED',
            submission_deadline DATE,
            CONSTRAINT unique_tender_award UNIQUE NULLS NOT DISTINCT (tender_id, award_date)
        ) PARTITION BY RANGE (award_date);
    """)
    
    # 4. Create partitions for years 2025, 2026, and a DEFAULT fallback partition
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS procurement_contracts_y2025 PARTITION OF procurement_contracts
            FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');
            
        CREATE TABLE IF NOT EXISTS procurement_contracts_y2026 PARTITION OF procurement_contracts
            FOR VALUES FROM ('2026-01-01') TO ('2027-01-01');
            
        CREATE TABLE IF NOT EXISTS procurement_contracts_default PARTITION OF procurement_contracts DEFAULT;
    """)
    
    # 5. Create the PL/pgSQL function and trigger to calculate red flags at the database tier
    cursor.execute("""
        CREATE OR REPLACE FUNCTION check_procurement_anomalies()
        RETURNS TRIGGER AS $$
        DECLARE
            reasons TEXT[];
            is_flagged BOOLEAN := FALSE;
            reg_date DATE;
        BEGIN
            -- Guard clause for open tenders
            IF NEW.tender_status = 'OPEN' THEN
                NEW.is_red_flagged := FALSE;
                NEW.red_flag_reason := 'Active Bidding Stage';
                RETURN NEW;
            END IF;

            -- Centralized Registry Lookup: maintain absolute company registration date consistency
            SELECT registration_date INTO reg_date 
            FROM contractor_registry 
            WHERE company_name = NEW.contractor_name;
            
            IF reg_date IS NULL THEN
                -- First encounter: register the contractor using the provided date or fallback
                IF NEW.contractor_reg_date IS NOT NULL THEN
                    reg_date := NEW.contractor_reg_date;
                ELSE
                    reg_date := NEW.award_date - INTERVAL '90 days';
                END IF;
                
                INSERT INTO contractor_registry (company_name, registration_date)
                VALUES (NEW.contractor_name, reg_date)
                ON CONFLICT (company_name) DO NOTHING;
            ELSIF NEW.contractor_reg_date IS NOT NULL AND NEW.contractor_reg_date < reg_date THEN
                -- Found an earlier registration date: back-propagate in registry
                reg_date := NEW.contractor_reg_date;
                UPDATE contractor_registry 
                SET registration_date = reg_date 
                WHERE company_name = NEW.contractor_name;
            ELSIF NEW.award_date < reg_date THEN
                -- The award date is prior to registered date (chronological mismatch). Pull registry date back.
                IF NEW.contractor_reg_date IS NOT NULL AND NEW.contractor_reg_date < NEW.award_date THEN
                    reg_date := NEW.contractor_reg_date;
                ELSE
                    reg_date := NEW.award_date - INTERVAL '90 days';
                END IF;
                UPDATE contractor_registry 
                SET registration_date = reg_date 
                WHERE company_name = NEW.contractor_name;
            END IF;
            
            -- Force consistent registration date in contract record
            NEW.contractor_reg_date := reg_date;

            -- Rule A: Single Bidder Anomaly
            IF NEW.bidders_count = 1 THEN
                is_flagged := TRUE;
                reasons := array_append(reasons, 'Single-bidder non-competitive assignment.');
            END IF;

            -- Rule B: Shell Company Detection (Registration-to-award interval between 0 and 29 days)
            IF (NEW.award_date - NEW.contractor_reg_date) >= 0 AND (NEW.award_date - NEW.contractor_reg_date) < 30 THEN
                is_flagged := TRUE;
                reasons := array_append(reasons, 'High risk: Company registered just ' || (NEW.award_date - NEW.contractor_reg_date) || ' days prior to award.');
            END IF;

            IF is_flagged THEN
                NEW.is_red_flagged := TRUE;
                NEW.red_flag_reason := array_to_string(reasons, ' | ');
            ELSE
                NEW.is_red_flagged := FALSE;
                NEW.red_flag_reason := 'Clean clearance profile.';
            END IF;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    cursor.execute("""
        CREATE OR REPLACE TRIGGER trg_check_procurement_anomalies
        BEFORE INSERT OR UPDATE ON procurement_contracts
        FOR EACH ROW
        EXECUTE FUNCTION check_procurement_anomalies();
    """)
    
    # 5. Create B-Tree indexes on high-lookup columns
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_contracts_flagged_date ON procurement_contracts(is_red_flagged, award_date DESC);
        CREATE INDEX IF NOT EXISTS idx_contracts_contractor ON procurement_contracts(contractor_name);
    """)
    
    conn.commit()
    cursor.close()
    conn.close()
    print("[⚙️ System] Database schema partitioning, trigger, and indexes initialized successfully.")

def fetch_and_process_stream():
    """
    Connects to the live OCDS stream, parses the release packages,
    and returns processed records ready for DB ingestion.
    """
    print(f"[📡 Stream] Connecting to stream at: {STREAM_URL}")
    processed_records = []
    
    try:
        # Connect to stream
        response = requests.get(STREAM_URL, stream=True, timeout=10)
        if response.status_code != 200:
            print(f"[❌ Stream Error] Failed to connect: HTTP {response.status_code}")
            return []
            
        for line in response.iter_lines(decode_unicode=True):
            if not line:
                continue
                
            try:
                payload = json.loads(line)
                release = payload.get("compiledRelease", {})
                
                # Extract tender metadata
                tender = release.get("tender", {})
                tender_id = tender.get("id")
                title = tender.get("title")
                
                # Extract buyer metadata
                buyer = release.get("buyer", {})
                buyer_name = buyer.get("name", "Unknown Buyer")
                
                # Extract award metadata
                awards = release.get("awards", [])
                if not awards:
                    continue
                award = awards[0]
                amount = float(award.get("value", {}).get("amount", 0.0))
                
                # Extract supplier/contractor metadata
                suppliers = award.get("suppliers", [])
                if not suppliers:
                    continue
                supplier = suppliers[0]
                contractor_name = supplier.get("name", "Unknown Contractor")
                
                # Establish competitors metric
                tenderers = tender.get("tenderers", [])
                bidders_count = len(tenderers)
                
                # Date parsing
                award_date_str = award.get("date")
                if award_date_str:
                    award_date = datetime.strptime(award_date_str.split("T")[0], "%Y-%m-%d").date()
                else:
                    award_date = datetime.now().date()
                    
                # Fault-Tolerance logic for contractor registration date
                reg_date_str = supplier.get("registration_date")
                if reg_date_str:
                    contractor_reg_date = datetime.strptime(reg_date_str.split("T")[0], "%Y-%m-%d").date()
                else:
                    # Omitted: apply 15% probability trap for testing triggers
                    if random.random() < 0.15:
                        # 15% chance: registered within 14 days prior to award date
                        delta = random.randint(0, 14)
                        contractor_reg_date = award_date - timedelta(days=delta)
                        print(f"[⚠️ Trap Triggered] Simulated shell company for '{contractor_name}': registered {delta} days before award.")
                    else:
                        # 85% chance: registered 90 to 365 days prior to award date
                        delta = random.randint(90, 365)
                        contractor_reg_date = award_date - timedelta(days=delta)
                        
                # Algorithmic Auditing for Corruption/Vulnerability Red Flags
                is_red_flagged = False
                reasons = []
                
                # Rule A: Single Bidder Anomaly
                if bidders_count == 1:
                    is_red_flagged = True
                    reasons.append("Single-bidder non-competitive assignment.")
                    
                # Rule B: Shell Company Detection (Contract awarded within 30 days of registration)
                registration_delta = (award_date - contractor_reg_date).days
                if registration_delta < 30:
                    is_red_flagged = True
                    reasons.append(f"High risk: Company registered just {registration_delta} days prior to award.")
                    
                reason_string = " | ".join(reasons) if is_red_flagged else "Clean clearance profile."
                
                processed_records.append((
                    tender_id, title, buyer_name,
                    contractor_name, contractor_reg_date, award_date,
                    amount, bidders_count, is_red_flagged, reason_string
                ))
                
            except json.JSONDecodeError as e:
                print(f"[❌ JSON Error] Failed to parse line: {e}")
            except Exception as e:
                print(f"[❌ Processing Error] Failed to process release: {e}")
                
    except Exception as e:
        print(f"[❌ Connection Error] Stream interrupted or could not connect: {e}")
        
    return processed_records

def load_records_to_db(records):
    """Upserts processed records into the database ledger, merging shifts on conflict."""
    if not records:
        print("[📊 Data Sync] No records retrieved to stream.")
        return
        
    conn = psycopg2.connect(DB_URL)
    cursor = conn.cursor()
    
    # ON CONFLICT Upsert Rule
    insert_query = """
        INSERT INTO procurement_contracts 
        (tender_id, title, ministry_department, contractor_name, contractor_reg_date, award_date, amount_allocated, bidders_count, is_red_flagged, red_flag_reason)
        VALUES %s
        ON CONFLICT (tender_id, award_date) DO UPDATE SET
            title = EXCLUDED.title,
            ministry_department = EXCLUDED.ministry_department,
            contractor_name = EXCLUDED.contractor_name,
            contractor_reg_date = EXCLUDED.contractor_reg_date,
            amount_allocated = EXCLUDED.amount_allocated,
            bidders_count = EXCLUDED.bidders_count,
            is_red_flagged = EXCLUDED.is_red_flagged,
            red_flag_reason = EXCLUDED.red_flag_reason,
            ingested_at = CURRENT_TIMESTAMP;
    """
    
    execute_values(cursor, insert_query, records)
    conn.commit()
    
    print(f"[📊 Data Sync] Successfully ingested/merged {len(records)} OCDS streaming records into the database.")
    cursor.close()
    conn.close()

if __name__ == "__main__":
    print("[🚀 Control Center] Activating Phase 1 OCDS Data Stream Ingestion...")
    init_db()
    records = fetch_and_process_stream()
    load_records_to_db(records)