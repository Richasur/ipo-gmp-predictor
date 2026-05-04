# 📈 IPO GMP Predictor

A production-grade IPO Grey Market Premium (GMP) analytics and prediction system that automatically scrapes, scores, tracks, and alerts on IPO listing opportunities in the Indian stock market.

![GitHub Actions](https://github.com/AdityaSharma2804/ipo-gmp-predictor/actions/workflows/scrape.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.11-blue)
![Streamlit](https://img.shields.io/badge/live-dashboard-brightgreen)

---

## Live Demo

🔴 **Live Dashboard:** [ipo-gmp-predictor-uqlpwgfygnwypgwmgwezo7.streamlit.app](https://ipo-gmp-predictor-uqlpwgfygnwypgwmgwezo7.streamlit.app)

Tracks 60+ IPOs in real-time. Auto-refreshes every 30 minutes via GitHub Actions — no manual intervention needed.

![Dashboard Preview](assets/dashboard.png)

---

## Tech Stack

| Layer      | Technology                        |
|------------|-----------------------------------|
| Backend    | Python 3.11                       |
| Database   | PostgreSQL (Supabase)             |
| Scraping   | BeautifulSoup, Requests           |
| Dashboard  | Streamlit                         |
| Scheduler  | GitHub Actions (cron every 30min) |
| Alerts     | Gmail SMTP                        |

---

## Setup (Fresh Start)

### Step 1 — Create a Supabase project

1. Go to [supabase.com](https://supabase.com) → New project
2. Copy your **Connection Pooler URI** from Settings → Database → Connection string (Transaction mode, port 6543)
3. It looks like: `postgresql://postgres.xxxx:password@aws-0-ap-south-1.pooler.supabase.com:6543/postgres`

### Step 2 — Run the SQL schema

1. Open your Supabase project → SQL Editor
2. Paste the entire contents of `sql/migrations.sql`
3. Click **Run** — this creates all tables, views, and indexes

### Step 3 — Clone and install

```bash
git clone https://github.com/AdityaSharma2804/ipo-gmp-predictor
cd ipo-gmp-predictor
pip install -r requirements.txt
```

### Step 4 — Set environment variables

For local development:
```bash
export DATABASE_URL="postgresql://postgres.xxxx:password@..."
export GMAIL_USER="youremail@gmail.com"
export GMAIL_PASS="xxxx xxxx xxxx xxxx"   # 16-char Gmail App Password
export ALERT_EMAIL="recipient@gmail.com"
```

For a `.env` file (optional, use `python-dotenv`):
```
DATABASE_URL=postgresql://...
GMAIL_USER=youremail@gmail.com
GMAIL_PASS=xxxx xxxx xxxx xxxx
ALERT_EMAIL=recipient@gmail.com
```

### Step 5 — Run pipeline manually

```bash
python pipeline/run_pipeline.py
```

### Step 6 — Run the dashboard

```bash
streamlit run dashboard/app.py
```

---

## GitHub Actions (Automated every 30 min)

1. Push your repo to GitHub
2. Go to Settings → Secrets and variables → Actions → New repository secret
3. Add these 4 secrets:

| Secret Name    | Value                               |
|---------------|--------------------------------------|
| `DATABASE_URL` | Your Supabase connection pooler URI |
| `GMAIL_USER`   | Gmail address for sending alerts    |
| `GMAIL_PASS`   | Gmail App Password (16 digits)      |
| `ALERT_EMAIL`  | Recipient email for STRONG BUY alerts |

The workflow in `.github/workflows/scrape.yml` runs automatically every 30 minutes.

---

## Gmail App Password

1. Go to [myaccount.google.com](https://myaccount.google.com)
2. Security → 2-Step Verification (must be ON)
3. Security → App passwords → Create → "Mail" + "Windows Computer"
4. Copy the 16-digit password — use as `GMAIL_PASS`

---

## Deploy Dashboard to Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Connect your GitHub repo
3. Main file path: `dashboard/app.py`
4. Add secrets (same 4 as above) in the Streamlit Secrets section:

```toml
DATABASE_URL = "postgresql://..."
GMAIL_USER   = "..."
GMAIL_PASS   = "..."
ALERT_EMAIL  = "..."
```

---

## Scoring System

| Factor        | Max Points | Logic                                     |
|---------------|-----------|-------------------------------------------|
| GMP %         | 15        | ≥50% → 15pts, ≥30% → 12pts, etc.         |
| Trend (delta) | 10        | Rising → 10pts, Flat → 5pts, Falling → 0 |
| IPO Status    | 10        | Open → 10pts, Upcoming → 7pts, Closed → 3|
| Est. Gain     | 5         | ≥50% → 5pts, ≥20% → 4pts, etc.           |
| **Total**     | **40**    |                                           |

### Signals
- **STRONG BUY** → Score ≥ 30
- **BUY**        → Score ≥ 22
- **HOLD**       → Score ≥ 15
- **WEAK**       → Score ≥ 8
- **AVOID**      → Score < 8

---

## Project Structure

```
ipo-gmp-predictor/
├── .github/
│   └── workflows/
│       └── scrape.yml           ← GitHub Actions cron (every 30 min)
├── assets/
│   └── dashboard.png            ← Dashboard screenshot
├── scraper/
│   ├── ipowatch_scraper.py      ← Primary data source
│   └── chittorgarh_scraper.py   ← Secondary data source
├── pipeline/
│   ├── db_manager.py            ← PostgreSQL connection + all DB ops
│   ├── run_pipeline.py          ← Main entry point (scrape→score→alert)
│   └── scheduler.py             ← Local APScheduler (optional)
├── scorer/
│   └── scoring_engine.py        ← Scoring + confidence + signals
├── dashboard/
│   └── app.py                   ← Streamlit UI
├── utils/
│   └── email_alerts.py          ← Gmail SMTP alert system
├── sql/
│   ├── migrations.sql           ← Full DB schema
│   └── sample_queries.sql       ← Useful ad-hoc queries
├── data/
│   └── gmp_data.csv             ← Local CSV backup (auto-filled)
└── requirements.txt
```

---

## How It Works

```
GitHub Actions (every 30 min)
        ↓
run_pipeline.py
        ↓
ipowatch.in scrape + chittorgarh.com scrape
        ↓
Merge sources (ipowatch priority)
        ↓
Insert into Supabase (gmp_data)
        ↓
Score every IPO → Insert into ipo_scores
        ↓
Track predicted vs actual → ipo_performance
        ↓
STRONG BUY detected? → Gmail email alert 📧
        ↓
Streamlit dashboard auto-refreshes
```

---

> ⚠️ Data sourced from investorgain.com and chittorgarh.com. For informational purposes only — not financial advice.
