import os
import sys
import json
import requests
import psycopg2
from psycopg2.extras import RealDictCursor

DB_URL = os.getenv("DATABASE_URL", "postgresql://transparency_admin:secure_procure_pass99@gov-db:5432/civil_portal_db")
API_URL = "http://backend-api:8000"

def run_db_queries():
    print("==================================================")
    print("   Database Verification - Partitions & Indexes")
    print("==================================================")
    
    try:
        conn = psycopg2.connect(DB_URL, cursor_factory=RealDictCursor)
        cursor = conn.cursor()
        
        # 1. Check Table partitions record distribution
        partitions = ["procurement_contracts_y2025", "procurement_contracts_y2026", "procurement_contracts_default"]
        print("[ℹ️] Querying records per partition:")
        for p in partitions:
            try:
                cursor.execute(f"SELECT COUNT(*) as cnt FROM {p};")
                cnt = cursor.fetchone()["cnt"]
                print(f"  - {p}: {cnt} records")
            except Exception as e:
                print(f"  - Failed to query {p}: {e}")
                
        # 2. Check total records in parent table
        cursor.execute("SELECT COUNT(*) as cnt FROM procurement_contracts;")
        total = cursor.fetchone()["cnt"]
        print(f"\n[ℹ️] Total records in parent 'procurement_contracts' table: {total}")
        
        # 3. Check trigger calculations for Red Flags
        cursor.execute("SELECT COUNT(*) as cnt FROM procurement_contracts WHERE is_red_flagged = TRUE;")
        red_flagged_cnt = cursor.fetchone()["cnt"]
        print(f"[ℹ️] Total red-flagged anomalies: {red_flagged_cnt} ({(red_flagged_cnt / total * 100):.2f}% of total)")
        
        # Verify Single Bidder Anomaly Trigger Invariant
        cursor.execute("SELECT COUNT(*) as cnt FROM procurement_contracts WHERE bidders_count = 1 AND is_red_flagged = FALSE;")
        violators_single = cursor.fetchone()["cnt"]
        if violators_single == 0:
            print("  [SUCCESS] All single-bidder contracts are correctly red-flagged by the trigger.")
        else:
            print(f"  [FAIL] Found {violators_single} single-bidder contracts that are NOT red-flagged!")
            
        # Verify Shell Company Trigger Invariant (Award Date - Contractor Reg Date < 30 days)
        cursor.execute("""
            SELECT COUNT(*) as cnt FROM procurement_contracts 
            WHERE contractor_reg_date IS NOT NULL 
              AND (award_date - contractor_reg_date) < 30 
              AND is_red_flagged = FALSE;
        """)
        violators_shell = cursor.fetchone()["cnt"]
        if violators_shell == 0:
            print("  [SUCCESS] All shell company anomalies (<30 days registration-to-award) are correctly red-flagged by the trigger.")
        else:
            print(f"  [FAIL] Found {violators_shell} shell company anomalies that are NOT red-flagged!")
            
        # Check reasons for flagged records
        cursor.execute("SELECT red_flag_reason, COUNT(*) as cnt FROM procurement_contracts WHERE is_red_flagged = TRUE GROUP BY red_flag_reason;")
        reasons = cursor.fetchall()
        print("\n[ℹ️] Red Flag reasons distribution:")
        for r in reasons:
            print(f"  - [{r['cnt']} records] {r['red_flag_reason']}")
            
        # 4. Check index creation
        print("\n[ℹ️] Verifying index availability:")
        indexes_to_check = ["idx_contracts_flagged_date", "idx_contracts_contractor"]
        for idx in indexes_to_check:
            cursor.execute("""
                SELECT indexname, indexdef 
                FROM pg_indexes 
                WHERE tablename = 'procurement_contracts' AND indexname = %s;
            """, (idx,))
            res = cursor.fetchone()
            if res:
                print(f"  - Index '{idx}' exists: {res['indexdef']}")
            else:
                print(f"  - [FAIL] Index '{idx}' NOT found!")
                
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"[❌ DB Connection Error] {e}")
        sys.exit(1)

def run_api_tests():
    print("\n==================================================")
    print("      FastAPI pagination API tests")
    print("==================================================")
    
    # Test 1: Root endpoint
    try:
        r = requests.get(f"{API_URL}/")
        print(f"[ℹ️] Root endpoint status: {r.status_code}")
        print(f"    Body: {r.json()}")
    except Exception as e:
        print(f"[❌ API Request Error] {e}")
        return
        
    # Test 2: Standard pagination request (limit=20, offset=0)
    try:
        r = requests.get(f"{API_URL}/api/v1/contracts?limit=20&offset=0")
        res = r.json()
        print(f"\n[ℹ️] Contracts API (limit=20, offset=0) status: {r.status_code}")
        print(f"  - total_records: {res.get('total_records')}")
        print(f"  - limit: {res.get('limit')}")
        print(f"  - offset: {res.get('offset')}")
        print(f"  - data length: {len(res.get('data', []))}")
        if len(res.get('data', [])) > 0:
            first = res['data'][0]
            print(f"  - First record: Tender ID {first['tender_id']}, Award Date {first['award_date']}, Contractor {first['contractor_name']}")
    except Exception as e:
        print(f"[❌ API Request Error] {e}")
        
    # Test 3: Pagination Offset test (limit=10, offset=10)
    try:
        r1 = requests.get(f"{API_URL}/api/v1/contracts?limit=10&offset=0")
        r2 = requests.get(f"{API_URL}/api/v1/contracts?limit=10&offset=10")
        res1 = r1.json()
        res2 = r2.json()
        print(f"\n[ℹ️] Pagination Offset Verification:")
        print(f"  - Page 1 (limit=10, offset=0) returned {len(res1.get('data', []))} records.")
        print(f"  - Page 2 (limit=10, offset=10) returned {len(res2.get('data', []))} records.")
        
        # Ensure Page 1 and Page 2 contain different records
        page1_ids = {item['tender_id'] for item in res1.get('data', [])}
        page2_ids = {item['tender_id'] for item in res2.get('data', [])}
        overlap = page1_ids.intersection(page2_ids)
        if not overlap:
            print("  [SUCCESS] No overlap between Page 1 and Page 2 records. Pagination offsets are working perfectly!")
        else:
            print(f"  [FAIL] Found overlapping records between Page 1 and Page 2: {overlap}")
    except Exception as e:
        print(f"[❌ API Request Error] {e}")
        
    # Test 4: Red Flag query pagination (red_flags_only=true)
    try:
        r = requests.get(f"{API_URL}/api/v1/contracts?limit=15&offset=0&red_flags_only=true")
        res = r.json()
        print(f"\n[ℹ️] Red Flags Only (limit=15, offset=0) status: {r.status_code}")
        print(f"  - total_records (flagged): {res.get('total_records')}")
        print(f"  - data length: {len(res.get('data', []))}")
        non_flagged = [item for item in res.get('data', []) if not item.get('is_red_flagged')]
        if not non_flagged:
            print("  [SUCCESS] All records returned in red_flags_only mode are correctly flagged.")
        else:
            print(f"  [FAIL] Found non-flagged records in red_flags_only response: {len(non_flagged)}")
    except Exception as e:
        print(f"[❌ API Request Error] {e}")
        
    # Test 5: Leaderboard API
    try:
        r = requests.get(f"{API_URL}/api/v1/contracts/leaderboard")
        res = r.json()
        leaderboard = res.get('leaderboard', [])
        print(f"\n[ℹ️] Leaderboard status: {r.status_code}")
        print(f"  - Leaderboard length: {len(leaderboard)}")
        if leaderboard:
            top = leaderboard[0]
            print(f"  - Top Contractor: {top['contractor_name']}")
            print(f"    Total Funding: NPR {float(top['total_funding_allocated']):,.2f}")
            print(f"    Contracts Won: {top['contracts_won_count']}")
            print(f"    Flagged Anomalies: {top['flagged_anomalies_count']}")
    except Exception as e:
        print(f"[❌ API Request Error] {e}")

if __name__ == "__main__":
    run_db_queries()
    run_api_tests()
