import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor

DB_URL = os.getenv("DATABASE_URL", "postgresql://transparency_admin:secure_procure_pass99@gov-db:5432/civil_portal_db")

def main():
    print("==================================================")
    print("       DATA RECONCILIATION & SYNC PASS")
    print("==================================================")
    
    target_tender_id = 'RRM/PAL/W/NCB-07/2082-83'
    target_buyer_name = 'Rainadevi Chhahara Rural Municipality, Palpa'
    
    try:
        print(f"[Connecting] Connecting to database at {DB_URL.split('@')[-1]}...")
        conn = psycopg2.connect(DB_URL, cursor_factory=RealDictCursor)
        conn.autocommit = False
        cursor = conn.cursor()
        
        # 1. Fetch current record state
        print(f"[Select] Searching for record with Tender ID: {target_tender_id}...")
        cursor.execute(
            "SELECT tender_id, title, ministry_department, contractor_name FROM procurement_contracts WHERE tender_id = %s;",
            (target_tender_id,)
        )
        record = cursor.fetchone()
        
        if not record:
            print(f"[Error] No record found matching Tender ID: {target_tender_id}")
            conn.close()
            sys.exit(1)
            
        print(f"  - Title: {record['title']}")
        print(f"  - Current Buyer (ministry_department): '{record['ministry_department']}'")
        print(f"  - Contractor Name: '{record['contractor_name']}'")
        
        # 2. Update buyer name
        print(f"[Update] Reconciling buyer name to: '{target_buyer_name}'...")
        cursor.execute(
            "UPDATE procurement_contracts SET ministry_department = %s WHERE tender_id = %s;",
            (target_buyer_name, target_tender_id)
        )
        updated_rows = cursor.rowcount
        print(f"  - Row(s) updated in procurement_contracts: {updated_rows}")
        
        # 3. Relational Enforcement check on contractor_registry
        contractor = record['contractor_name']
        if contractor:
            print(f"[Select] Checking synchronization for contractor: '{contractor}' in contractor_registry...")
            cursor.execute(
                "SELECT company_name, registration_date FROM contractor_registry WHERE company_name = %s;",
                (contractor,)
            )
            reg_record = cursor.fetchone()
            if reg_record:
                print(f"  - Contractor '{contractor}' is already synchronized in contractor_registry (Reg Date: {reg_record['registration_date']}).")
            else:
                print(f"  - [Warning] Contractor '{contractor}' not found in contractor_registry. Inserting default entry...")
                cursor.execute(
                    "INSERT INTO contractor_registry (company_name, registration_date) VALUES (%s, CURRENT_DATE) ON CONFLICT DO NOTHING;",
                    (contractor,)
                )
                print("  - Inserted default contractor registry entry.")
        
        # Commit transaction
        conn.commit()
        print("[Success] Database transaction committed successfully.")
        
        # Verify update
        cursor.execute(
            "SELECT tender_id, ministry_department FROM procurement_contracts WHERE tender_id = %s;",
            (target_tender_id,)
        )
        verified_record = cursor.fetchone()
        print(f"[Verification] Confirmed updated buyer name in database: '{verified_record['ministry_department']}'")
        
        cursor.close()
        conn.close()
        print("==================================================")
        print("          RECONCILIATION COMPLETED")
        print("==================================================")
        
    except Exception as e:
        print(f"[Failure] Database transaction rolled back due to error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
