from fastapi import FastAPI, BackgroundTasks, HTTPException, Response
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta, time
import pytz
import uuid
import pandas as pd
import io
from sqlalchemy import func

from .database import engine, SessionLocal
from .models import Base, StoreStatus, StoreHours, StoreTimezone, ReportJob

app = FastAPI(title="Store Monitoring API")


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)


def _run_ingestion_job() -> None:
    # Deferred absolute import to avoid heavy deps at import-time
    from scripts.ingest_data import ingest_data  # type: ignore
    ingest_data()


@app.post("/ingest")
def trigger_ingestion(background_tasks: BackgroundTasks):
    background_tasks.add_task(_run_ingestion_job)
    return {"message": "Ingestion started"}


@app.get("/")
def read_root():
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


@app.post("/trigger_report")
def trigger_report():
    """
    Trigger report generation from the data provided (stored in DB)
    Returns report_id for polling status
    """
    try:
        db = SessionLocal()
        
        # Generate unique report ID
        report_id = str(uuid.uuid4())
        
        # Create report job record
        report_job = ReportJob(
            report_id=report_id,
            status="Running",
            created_at=datetime.now(pytz.UTC)
        )
        db.add(report_job)
        db.commit()
        db.close()
        
        # Start report generation in background
        from threading import Thread
        thread = Thread(target=generate_report_async, args=(report_id,))
        thread.start()
        
        return {"report_id": report_id}
        
    except Exception as e:
        if 'db' in locals():
            db.close()
        raise HTTPException(status_code=500, detail=f"Error triggering report: {str(e)}")


@app.get("/get_report")
def get_report(report_id: str):
    """
    Get report status or CSV data
    Returns "Running" if not complete, or CSV file if complete
    """
    try:
        db = SessionLocal()
        
        report_job = db.query(ReportJob).filter(ReportJob.report_id == report_id).first()
        if not report_job:
            db.close()
            raise HTTPException(status_code=404, detail="Report not found")
        
        if report_job.status == "Running":
            db.close()
            return {"status": "Running"}
        elif report_job.status == "Complete":
            csv_data = report_job.csv_data
            db.close()
            return PlainTextResponse(
                content=csv_data,
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=report_{report_id}.csv"}
            )
        else:  # Failed
            error_msg = report_job.error_message
            db.close()
            raise HTTPException(status_code=500, detail=f"Report generation failed: {error_msg}")
            
    except HTTPException:
        raise
    except Exception as e:
        if 'db' in locals():
            db.close()
        raise HTTPException(status_code=500, detail=f"Error retrieving report: {str(e)}")


def generate_report_async(report_id: str):
    """
    Generate the report asynchronously
    """
    db = SessionLocal()
    try:
        # Get max timestamp to use as "current time"
        max_timestamp = db.query(func.max(StoreStatus.timestamp_utc)).scalar()
        if not max_timestamp:
            raise Exception("No status data found")
        
        current_time = max_timestamp.replace(tzinfo=pytz.UTC)
        
        # Calculate time ranges
        last_hour_start = current_time - timedelta(hours=1)
        last_day_start = current_time - timedelta(days=1)
        last_week_start = current_time - timedelta(weeks=1)
        
        # Get all stores
        all_stores = db.query(StoreTimezone.store_id).distinct().all()
        
        report_data = []
        
        for store_row in all_stores:
            store_id = str(store_row.store_id)
            
            # Calculate uptime/downtime for each period
            hour_data = calculate_store_uptime(db, store_id, last_hour_start, current_time)
            day_data = calculate_store_uptime(db, store_id, last_day_start, current_time)
            week_data = calculate_store_uptime(db, store_id, last_week_start, current_time)
            
            report_data.append({
                "store_id": store_id,
                "uptime_last_hour(in minutes)": round(hour_data["uptime_minutes"], 2),
                "uptime_last_day(in hours)": round(day_data["uptime_minutes"] / 60, 2),
                "uptime_last_week(in hours)": round(week_data["uptime_minutes"] / 60, 2),
                "downtime_last_hour(in minutes)": round(hour_data["downtime_minutes"], 2),
                "downtime_last_day(in hours)": round(day_data["downtime_minutes"] / 60, 2),
                "downtime_last_week(in hours)": round(week_data["downtime_minutes"] / 60, 2)
            })
        
        # Convert to CSV
        df = pd.DataFrame(report_data)
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_data = csv_buffer.getvalue()
        
        # Update report job as complete
        report_job = db.query(ReportJob).filter(ReportJob.report_id == report_id).first()
        report_job.status = "Complete"
        report_job.completed_at = datetime.now(pytz.UTC)
        report_job.csv_data = csv_data
        db.commit()
        
    except Exception as e:
        # Mark report as failed
        report_job = db.query(ReportJob).filter(ReportJob.report_id == report_id).first()
        if report_job:
            report_job.status = "Failed"
            report_job.error_message = str(e)
            report_job.completed_at = datetime.now(pytz.UTC)
            db.commit()
    finally:
        db.close()


def calculate_store_uptime(db, store_id: str, start_time: datetime, end_time: datetime):
    """
    Calculate uptime and downtime for a store in a given time period
    Only considers business hours and extrapolates from observations
    """
    # Get store timezone (default to America/Chicago if missing)
    timezone_record = db.query(StoreTimezone).filter(StoreTimezone.store_id == store_id).first()
    if timezone_record:
        store_tz = pytz.timezone(timezone_record.timezone_str)
    else:
        store_tz = pytz.timezone("America/Chicago")  # Default
    
    # Get business hours (default to 24/7 if missing)
    business_hours = db.query(StoreHours).filter(StoreHours.store_id == store_id).all()
    if not business_hours:
        # Default: 24/7 operation
        business_hours = []
        for day in range(7):  # 0=Monday to 6=Sunday
            business_hours.append(type('obj', (object,), {
                'dayOfWeek': day,
                'start_time_local': '00:00:00',
                'end_time_local': '23:59:59'
            }))
    
    # Get status observations for this period
    status_records = db.query(StoreStatus).filter(
        StoreStatus.store_id == store_id,
        StoreStatus.timestamp_utc >= start_time,
        StoreStatus.timestamp_utc <= end_time
    ).order_by(StoreStatus.timestamp_utc).all()
    
    total_uptime_minutes = 0
    total_downtime_minutes = 0
    
    # Process each day in the time range
    current_date = start_time.astimezone(store_tz).date()
    end_date = end_time.astimezone(store_tz).date()
    
    while current_date <= end_date:
        # Find business hours for this day (0=Monday, 6=Sunday)
        day_of_week = current_date.weekday()  # 0=Monday, 6=Sunday
        
        day_business_hours = [h for h in business_hours if h.dayOfWeek == day_of_week]
        
        for hours in day_business_hours:
            # Parse time strings
            start_hour, start_minute, start_second = map(int, hours.start_time_local.split(':'))
            end_hour, end_minute, end_second = map(int, hours.end_time_local.split(':'))
            
            # Create business period for this day
            business_start = store_tz.localize(
                datetime.combine(current_date, time(start_hour, start_minute, start_second))
            )
            business_end = store_tz.localize(
                datetime.combine(current_date, time(end_hour, end_minute, end_second))
            )
            
            # Clip to our analysis period
            period_start = max(business_start, start_time.astimezone(store_tz))
            period_end = min(business_end, end_time.astimezone(store_tz))
            
            if period_start < period_end:
                # Get relevant observations for this business period
                period_observations = [
                    obs for obs in status_records
                    if period_start <= obs.timestamp_utc.replace(tzinfo=pytz.UTC).astimezone(store_tz) <= period_end
                ]
                
                # Calculate uptime/downtime using extrapolation
                uptime_mins, downtime_mins = extrapolate_uptime(
                    period_observations, period_start, period_end, store_tz
                )
                
                total_uptime_minutes += uptime_mins
                total_downtime_minutes += downtime_mins
        
        current_date += timedelta(days=1)
    
    return {
        "uptime_minutes": total_uptime_minutes,
        "downtime_minutes": total_downtime_minutes
    }


def extrapolate_uptime(observations, start_time, end_time, store_tz):
    """
    Extrapolate uptime/downtime from sparse observations
    
    Logic:
    - If no observations, assume store was down for entire period
    - Before first observation: assume same status as first observation
    - Between observations: assume previous status continues
    - After last observation: assume same status as last observation
    """
    if not observations:
        # No data, assume downtime for entire period
        total_minutes = (end_time - start_time).total_seconds() / 60
        return 0, total_minutes
    
    # Sort observations by timestamp
    sorted_obs = sorted(observations, key=lambda x: x.timestamp_utc)
    
    uptime_minutes = 0
    downtime_minutes = 0
    
    current_time = start_time
    
    for i, obs in enumerate(sorted_obs):
        obs_time = obs.timestamp_utc.replace(tzinfo=pytz.UTC).astimezone(store_tz)
        
        if i == 0:
            # Before first observation: assume same status as first observation
            if obs_time > current_time:
                duration_minutes = (obs_time - current_time).total_seconds() / 60
                if obs.status == "active":
                    uptime_minutes += duration_minutes
                else:
                    downtime_minutes += duration_minutes
        else:
            # Between observations: use previous observation's status
            prev_obs = sorted_obs[i-1]
            duration_minutes = (obs_time - current_time).total_seconds() / 60
            if prev_obs.status == "active":
                uptime_minutes += duration_minutes
            else:
                downtime_minutes += duration_minutes
        
        current_time = obs_time
    
    # After last observation until end_time
    if current_time < end_time:
        last_obs = sorted_obs[-1]
        duration_minutes = (end_time - current_time).total_seconds() / 60
        if last_obs.status == "active":
            uptime_minutes += duration_minutes
        else:
            downtime_minutes += duration_minutes
    
    return uptime_minutes, downtime_minutes