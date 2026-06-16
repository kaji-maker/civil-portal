import os
import json
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import psycopg2
from psycopg2.extras import RealDictCursor

app = FastAPI(
    title="Government Transparency API Engine",
    description="Phase 1: Open Procurement and Contractor Risk Auditing Ledger Core",
    version="1.0.0"
)

# Enable CORS so our upcoming Phase 1 frontend can talk to the backend smoothly
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_URL = os.getenv("DATABASE_URL", "postgresql://transparency_admin:secure_procure_pass99@localhost:5432/civil_portal_db")

def get_db_connection():
    # RealDictCursor allows us to fetch rows as native Python dictionaries (perfect for JSON extraction)
    return psycopg2.connect(DB_URL, cursor_factory=RealDictCursor)

@app.get("/")
def read_root():
    return {
        "status": "Online",
        "system": "Antigravity-Orchestrated Transparency Pipeline",
        "phase": 1.0
    }

@app.get("/api/v1/contracts")
def get_contracts(
    red_flags_only: bool = Query(False, description="Filter exclusively for high-risk single-bidder or shell company anomalies"),
    limit: int = Query(20, description="Number of records to return"),
    offset: int = Query(0, description="Offset of records to return")
):
    """Fetches full transparency procurement tracking data directly from the system ledger with pagination."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if red_flags_only:
        count_query = "SELECT COUNT(*) FROM procurement_contracts WHERE is_red_flagged = TRUE;"
        data_query = "SELECT * FROM procurement_contracts WHERE is_red_flagged = TRUE ORDER BY award_date DESC, tender_id DESC LIMIT %s OFFSET %s;"
    else:
        count_query = "SELECT COUNT(*) FROM procurement_contracts;"
        data_query = "SELECT * FROM procurement_contracts ORDER BY award_date DESC, tender_id DESC LIMIT %s OFFSET %s;"
        
    cursor.execute(count_query)
    total_count = cursor.fetchone()["count"]
    
    cursor.execute(data_query, (limit, offset))
    records = cursor.fetchall()
    
    cursor.close()
    conn.close()
    return {
        "total_records": total_count,
        "limit": limit,
        "offset": offset,
        "data": records
    }

@app.get("/api/v1/contracts/leaderboard")
def get_leaderboard():
    """Compiles a direct contractor leaderboard aggregating government funds allocated per entity."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Aggregates funding sums and count details per corporate entity
    query = """
        SELECT 
            contractor_name,
            SUM(amount_allocated) as total_funding_allocated,
            COUNT(id) as contracts_won_count,
            COUNT(CASE WHEN is_red_flagged = TRUE THEN 1 END) as flagged_anomalies_count
        FROM procurement_contracts
        WHERE contractor_name IS NOT NULL
        GROUP BY contractor_name
        ORDER BY total_funding_allocated DESC;
    """
    cursor.execute(query)
    leaderboard = cursor.fetchall()
    
    cursor.close()
    conn.close()
    return {"leaderboard": leaderboard}

@app.get("/api/v1/contracts/mock-ocds-stream")
def get_mock_ocds_stream():
    """Streams mock OCDS release packages as newline-delimited JSON (JSONL)."""
    def event_generator():
        # Mock OCDS releases from Nepal
        mock_releases = [
            {
                "compiledRelease": {
                    "tender": {
                        "id": "TENDER-2026-NP-8091",
                        "title": "Rehabilitation of Kathmandu-Deukhuri Expressway Section C",
                        "tenderers": [
                            {"id": "SUPPLIER-101", "name": "Apex Construction Group Ltd."},
                            {"id": "SUPPLIER-102", "name": "Himalayan Builders Ltd."},
                            {"id": "SUPPLIER-103", "name": "Siddharth Infra Corp"}
                        ]
                    },
                    "buyer": {
                        "name": "Department of Roads - Ministry of Physical Infrastructure"
                    },
                    "awards": [
                        {
                            "id": "AWARD-2026-8091",
                            "status": "active",
                            "date": "2026-06-14",
                            "value": {
                                "amount": 142000000.00,
                                "currency": "NPR"
                            },
                            "suppliers": [
                                {"id": "SUPPLIER-101", "name": "Apex Construction Group Ltd."}
                            ]
                        }
                    ]
                }
            },
            {
                "compiledRelease": {
                    "tender": {
                        "id": "TENDER-2026-NP-3321",
                        "title": "Procurement and Installation of Lalitpur smart traffic control loops",
                        "tenderers": [
                            {"id": "SUPPLIER-202", "name": "Alpha-Omega Tech Solutions"}
                        ]
                    },
                    "buyer": {
                        "name": "Lalitpur Metropolitan City Office"
                    },
                    "awards": [
                        {
                            "id": "AWARD-2026-3321",
                            "status": "active",
                            "date": "2026-06-15",
                            "value": {
                                "amount": 29800000.00,
                                "currency": "NPR"
                            },
                            "suppliers": [
                                {"id": "SUPPLIER-202", "name": "Alpha-Omega Tech Solutions"}
                            ]
                        }
                    ]
                }
            },
            {
                "compiledRelease": {
                    "tender": {
                        "id": "TENDER-2026-NP-4422",
                        "title": "Rural Water Supply Tube-well Drilling In Sarlahi District",
                        "tenderers": [
                            {"id": "SUPPLIER-303", "name": "Janaki Tube-well & Boring Contractors"}
                        ]
                    },
                    "buyer": {
                        "name": "Ministry of Water Supply"
                    },
                    "awards": [
                        {
                            "id": "AWARD-2026-4422",
                            "status": "active",
                            "date": "2026-06-16",
                            "value": {
                                "amount": 8900000.00,
                                "currency": "NPR"
                            },
                            "suppliers": [
                                {"id": "SUPPLIER-303", "name": "Janaki Tube-well & Boring Contractors"}
                            ]
                        }
                    ]
                }
            },
            {
                "compiledRelease": {
                    "tender": {
                        "id": "TENDER-2026-NP-5501",
                        "title": "Construction of District Hospital Ward Building in Jumla",
                        "tenderers": [
                            {"id": "SUPPLIER-404", "name": "Karnali Infra Ventures"},
                            {"id": "SUPPLIER-102", "name": "Himalayan Builders Ltd."}
                        ]
                    },
                    "buyer": {
                        "name": "Department of Health Services"
                    },
                    "awards": [
                        {
                            "id": "AWARD-2026-5501",
                            "status": "active",
                            "date": "2026-06-10",
                            "value": {
                                "amount": 75000000.00,
                                "currency": "NPR"
                            },
                            "suppliers": [
                                {"id": "SUPPLIER-404", "name": "Karnali Infra Ventures"}
                            ]
                        }
                    ]
                }
            }
        ]
        
        for release in mock_releases:
            yield json.dumps(release) + "\n"
            
    return StreamingResponse(event_generator(), media_type="application/x-ndjson")