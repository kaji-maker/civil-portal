# 🔵 Civil Portal: Public Procurement Transparency Pipeline (Phase 1)

An open-source, automated civic-tech intelligence pipeline that ingests, partitions, and audits public procurement contract data directly from the official Nepal e-GP platform (bolpatra.gov.np) and historical OCDS releases.

## 🚀 Features
- **Live e-GP Scraper:** Playwright (headless Chromium) engine that targets finalized contracts without mock fallbacks.
- **PostgreSQL Time-Series Partitioning:** Range-partitioned ledger tables split by fiscal years (`y2025`, `y2026`) with dynamic routing.
- **Forensic Audit Engine:** Automated PL/pgSQL triggers that flag single-bidder non-competitive assignments instantaneously.
- **In-Memory Citizen Dashboard:** A high-contrast, premium glassmorphic UI displaying dynamic Nepalese compact currency metrics (करोड / लाख).

## 🛠️ Tech Stack
- **Backend/Scrapers:** Python 3.11+, Playwright, BeautifulSoup4, FastAPI
- **Database:** PostgreSQL 15+ (Using native declarative partitioning)
- **Frontend:** HTML5, Premium Muted CSS Grid Layouts, Vanilla JavaScript ($O(1)$ client-side filtering engine)

## ⚙️ Quick Start (Local Deployment)

1. **Clone the repository:**
```bash
   git clone https://github.com/kaji-maker/civil-portal.git
   cd civil-portal
