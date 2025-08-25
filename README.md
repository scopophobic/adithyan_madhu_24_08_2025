# 🍽️ Store Monitoring System

A Python API that tracks restaurant uptime/downtime from periodic status checks and generates monitoring reports.

## 🚀 Quick Start

```bash
# 1. Setup
git clone <repo>
cd store-monitoring_system
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# 2. Configure PostgreSQL
# Set these environment variables:
# POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, POSTGRES_SERVER, POSTGRES_PORT

# 3. Start server
uvicorn app.main:app --reload

# 4. Open frontend
http://localhost:8000/static/index.html
```

## 🎯 What It Does

**Input**: 3 CSV files with restaurant data
- `store_status.csv` - Active/inactive status every ~1 hour (1.8M records)
- `menu_hours.csv` - Business hours per day (35K records)  
- `timezones.csv` - Store timezones (4.5K records)

**Output**: Uptime/downtime reports
- Last hour (in minutes)
- Last day (in hours)
- Last week (in hours)

**Key Feature**: Extrapolates uptime from sparse data during business hours only.

## 🏗️ Tech Stack

- **Backend**: FastAPI (Python)
- **Database**: PostgreSQL
- **Frontend**: HTML/CSS/JavaScript
- **Data**: Pandas, SQLAlchemy
- **Algorithm**: Custom uptime extrapolation

## 📊 API Workflow

```
1. POST /ingest          → Load CSV data into database
2. POST /trigger_report  → Start report generation (returns report_id)
3. GET /get_report       → Download CSV or check status
4. GET /restaurants      → List restaurants in report
5. GET /restaurant/{id}  → Get detailed restaurant info
```

## 🧮 Core Algorithm

**Problem**: Only ~1 status observation per hour, but need uptime for entire business hours.

**Solution**: Smart extrapolation
- Before first observation → Assume same as first
- Between observations → Previous status continues  
- After last observation → Assume same as last
- No observations → Assume store is operating normally

**Example**:
```
Business: 9 AM - 12 PM (180 minutes)
Data: 10:14 AM (active), 11:15 AM (inactive)

Result:
- 9:00-10:14 → Active (74 min)
- 10:14-11:15 → Active (61 min)
- 11:15-12:00 → Inactive (45 min)
= 75% uptime
```

## 📁 Project Structure

```
app/
├── main.py              # API endpoints
├── models/              # Database models
└── services/            # Business logic
    ├── calculation_service.py    # Core algorithm
    ├── report_service.py         # Report generation
    └── background_service.py     # Async jobs
frontend/                # Simple web UI
data/input/             # CSV files
```

## 🔧 Key Features

- **Background jobs** - Reports generate without blocking API
- **Timezone handling** - Converts UTC to local business hours
- **Clean architecture** - Separated concerns, easy to test
- **Simple frontend** - One-click CSV downloads
- **Robust defaults** - Handles missing data gracefully

## 📄 Output Format

CSV exactly as specified:
```csv
store_id,uptime_last_hour(in minutes),uptime_last_day(in hours),uptime_last_week(in hours),downtime_last_hour(in minutes),downtime_last_day(in hours),downtime_last_week(in hours)
```

## 🎯 That's It

Load data → Generate reports → Download CSV → Done.

Built to handle large datasets (134MB CSV) with accurate uptime calculations.
