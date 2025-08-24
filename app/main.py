"""
Store Monitoring API
Clean and simple API endpoints
"""

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import pytz

from .database import engine, SessionLocal
from .models import Base, StoreTimezone, StoreHours, StoreStatus
from .services.background_service import create_report_job, start_report_generation, get_report_status
from .services.search_service import search_report, get_store_details, get_report_summary

# Initialize FastAPI app
app = FastAPI(title="Store Monitoring API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files (frontend)
app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.on_event("startup")
def on_startup() -> None:
    """Create database tables on startup"""
    Base.metadata.create_all(bind=engine)


# ===== CORE API ENDPOINTS (Required by specs) =====

@app.post("/trigger_report")
def trigger_report():
    """
    Trigger report generation from the data provided (stored in DB)
    Returns report_id for polling status
    """
    try:
        # Create report job
        report_id = create_report_job()
        
        # Start generation in background
        start_report_generation(report_id)
        
        return {"report_id": report_id}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error triggering report: {str(e)}")


@app.get("/get_report")
def get_report(report_id: str):
    """
    Get report status or CSV data
    Returns "Running" if not complete, or CSV file if complete
    """
    try:
        result = get_report_status(report_id)
        
        if result.get("error"):
            raise HTTPException(status_code=result["status_code"], detail=result["error"])
        
        if result["status"] == "Running":
            return {"status": "Running"}
        elif result["status"] == "Complete":
            return PlainTextResponse(
                content=result["csv_data"],
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=report_{report_id}.csv"}
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving report: {str(e)}")


# ===== RESTAURANT ENDPOINTS (Simple!) =====

@app.get("/restaurants")
def list_restaurants(report_id: str):
    """
    Get list of all restaurants in a report
    
    Simple list for frontend - click on any restaurant to get details
    """
    try:
        result = search_report(report_id)  # No filters, just get all
        
        if result.get("status_code") != 200:
            raise HTTPException(status_code=result["status_code"], detail=result.get("error", "Failed to get restaurants"))
        
        # Simplify response - just the restaurant list
        restaurants = []
        for store in result["results"]["stores"]:
            restaurants.append({
                "store_id": store["store_id"],
                "uptime_last_hour": store["uptime_percentage"]["last_hour"],
                "uptime_last_day": store["uptime_percentage"]["last_day"], 
                "uptime_last_week": store["uptime_percentage"]["last_week"],
                "average_uptime": round((
                    store["uptime_percentage"]["last_hour"] +
                    store["uptime_percentage"]["last_day"] +
                    store["uptime_percentage"]["last_week"]
                ) / 3, 1)
            })
        
        return {
            "report_id": report_id,
            "total_restaurants": len(restaurants),
            "restaurants": restaurants
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting restaurants: {str(e)}")


@app.get("/restaurant/{store_id}")
def get_restaurant_details(store_id: str, report_id: str):
    """
    Get detailed information for a specific restaurant
    
    Perfect when user clicks on a restaurant from the list
    """
    try:
        result = get_store_details(report_id, store_id)
        
        if result.get("status_code") != 200:
            raise HTTPException(status_code=result["status_code"], detail=result.get("error", "Restaurant not found"))
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting restaurant details: {str(e)}")


@app.get("/reports")
def list_all_reports():
    """
    Get list of all report IDs and their status
    
    Perfect for frontend to show available reports
    """
    try:
        db = SessionLocal()
        
        # Get all reports ordered by creation date (newest first)
        from .models import ReportJob
        reports = db.query(ReportJob).order_by(ReportJob.created_at.desc()).all()
        
        report_list = []
        for report in reports:
            report_list.append({
                "report_id": report.report_id,
                "status": report.status,
                "created_at": report.created_at.isoformat(),
                "completed_at": report.completed_at.isoformat() if report.completed_at else None,
                "has_data": report.status == "Complete" and report.json_data is not None
            })
        
        db.close()
        
        return {
            "total_reports": len(report_list),
            "reports": report_list
        }
        
    except Exception as e:
        if 'db' in locals():
            db.close()
        raise HTTPException(status_code=500, detail=f"Error getting reports: {str(e)}")


# ===== HELPER ENDPOINTS =====

@app.get("/")
def read_root():
    """Root endpoint"""
    return {"message": "Store Monitoring API is running"}


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now(pytz.UTC).isoformat()}


@app.get("/stats")
def get_stats():
    """Get basic statistics about the data"""
    try:
        db = SessionLocal()
        
        # Count records in each table
        timezone_count = db.query(StoreTimezone).count()
        hours_count = db.query(StoreHours).count()
        status_count = db.query(StoreStatus).count()
        
        # Get latest timestamp
        latest_status = db.query(StoreStatus).order_by(StoreStatus.timestamp_utc.desc()).first()
        latest_timestamp = latest_status.timestamp_utc if latest_status else None
        
        db.close()
    
        return {
            "store_timezones": timezone_count,
            "store_hours": hours_count,
            "store_status": status_count,
            "latest_status_timestamp": latest_timestamp.isoformat() if latest_timestamp else None
        }
        
    except Exception as e:
        if 'db' in locals():
            db.close()
        raise HTTPException(status_code=500, detail=f"Error getting stats: {str(e)}")


@app.post("/ingest")
def trigger_ingestion(background_tasks: BackgroundTasks):
    """Trigger data ingestion from CSV files"""
    def _run_ingestion_job() -> None:
        from scripts.ingest_data import ingest_data
        ingest_data()
    
    background_tasks.add_task(_run_ingestion_job)
    return {"message": "Ingestion started"}