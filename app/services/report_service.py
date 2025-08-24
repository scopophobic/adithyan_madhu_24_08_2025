"""
Report generation service
Handles all report calculation logic
"""

from datetime import datetime, timedelta, time
import pytz
import pandas as pd
import io
from sqlalchemy import func
from typing import Dict, List, Any

from ..database import SessionLocal
from ..models import StoreStatus, StoreHours, StoreTimezone, ReportJob


def generate_report_data() -> tuple[str, str]:
    """
    Generate the complete report data in both CSV and JSON formats
    Returns (csv_string, json_string)
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
            
            # Store data for JSON (more detailed)
            store_report = {
                "store_id": store_id,
                "uptime_last_hour_minutes": round(hour_data["uptime_minutes"], 2),
                "uptime_last_day_hours": round(day_data["uptime_minutes"] / 60, 2),
                "uptime_last_week_hours": round(week_data["uptime_minutes"] / 60, 2),
                "downtime_last_hour_minutes": round(hour_data["downtime_minutes"], 2),
                "downtime_last_day_hours": round(day_data["downtime_minutes"] / 60, 2),
                "downtime_last_week_hours": round(week_data["downtime_minutes"] / 60, 2),
                # Add calculated percentages for frontend
                "uptime_percentage": {
                    "last_hour": round((hour_data["uptime_minutes"] / max(1, hour_data["uptime_minutes"] + hour_data["downtime_minutes"])) * 100, 1),
                    "last_day": round((day_data["uptime_minutes"] / max(60, day_data["uptime_minutes"] + day_data["downtime_minutes"])) * 100, 1),
                    "last_week": round((week_data["uptime_minutes"] / max(60, week_data["uptime_minutes"] + week_data["downtime_minutes"])) * 100, 1)
                },
                "total_business_time": {
                    "last_hour_minutes": round(hour_data["uptime_minutes"] + hour_data["downtime_minutes"], 2),
                    "last_day_hours": round((day_data["uptime_minutes"] + day_data["downtime_minutes"]) / 60, 2),
                    "last_week_hours": round((week_data["uptime_minutes"] + week_data["downtime_minutes"]) / 60, 2)
                }
            }
            
            report_data.append(store_report)
        
        # Generate JSON
        import json
        json_data = {
            "report_metadata": {
                "generated_at": current_time.isoformat(),
                "total_stores": len(report_data),
                "time_periods": {
                    "last_hour": (last_hour_start.isoformat(), current_time.isoformat()),
                    "last_day": (last_day_start.isoformat(), current_time.isoformat()),
                    "last_week": (last_week_start.isoformat(), current_time.isoformat())
                }
            },
            "stores": report_data
        }
        json_string = json.dumps(json_data, indent=2)
        
        # Generate CSV (convert JSON data to CSV format)
        csv_data = []
        for store in report_data:
            csv_data.append({
                "store_id": store["store_id"],
                "uptime_last_hour(in minutes)": store["uptime_last_hour_minutes"],
                "uptime_last_day(in hours)": store["uptime_last_day_hours"],
                "uptime_last_week(in hours)": store["uptime_last_week_hours"],
                "downtime_last_hour(in minutes)": store["downtime_last_hour_minutes"],
                "downtime_last_day(in hours)": store["downtime_last_day_hours"],
                "downtime_last_week(in hours)": store["downtime_last_week_hours"]
            })
        
        df = pd.DataFrame(csv_data)
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_string = csv_buffer.getvalue()
        
        return csv_string, json_string
        
    finally:
        db.close()


def calculate_store_uptime(db, store_id: str, start_time: datetime, end_time: datetime) -> Dict[str, float]:
    """
    Calculate uptime and downtime for a store in a given time period
    Only considers business hours and extrapolates from observations
    """
    from .store_service import get_store_timezone, get_store_business_hours
    from .time_service import get_business_periods_in_range
    from .calculation_service import extrapolate_uptime
    
    # Get store data
    store_tz = get_store_timezone(db, store_id)
    business_hours = get_store_business_hours(db, store_id)
    
    # Get status observations for this period
    status_records = db.query(StoreStatus).filter(
        StoreStatus.store_id == store_id,
        StoreStatus.timestamp_utc >= start_time,
        StoreStatus.timestamp_utc <= end_time
    ).order_by(StoreStatus.timestamp_utc).all()
    
    # Get business periods within the time range
    business_periods = get_business_periods_in_range(
        business_hours, start_time, end_time, store_tz
    )
    
    total_uptime_minutes = 0
    total_downtime_minutes = 0
    
    # Calculate for each business period
    for period_start, period_end in business_periods:
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
    
    return {
        "uptime_minutes": total_uptime_minutes,
        "downtime_minutes": total_downtime_minutes
    }


def update_report_job(report_id: str, status: str, csv_data: str = None, json_data: str = None, error_message: str = None):
    """
    Update report job status in database
    """
    db = SessionLocal()
    try:
        report_job = db.query(ReportJob).filter(ReportJob.report_id == report_id).first()
        if report_job:
            report_job.status = status
            report_job.completed_at = datetime.now(pytz.UTC)
            if csv_data:
                report_job.csv_data = csv_data
            if json_data:
                report_job.json_data = json_data
            if error_message:
                report_job.error_message = error_message
            db.commit()
    finally:
        db.close()
