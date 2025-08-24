"""
Background job service
Handles async report generation
"""

from datetime import datetime
import pytz
import uuid
from threading import Thread

from ..database import SessionLocal
from ..models import ReportJob
from .report_service import generate_report_data, update_report_job


def create_report_job() -> str:
    """
    Create a new report job and return the report_id
    """
    db = SessionLocal()
    try:
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
        
        return report_id
        
    finally:
        db.close()


def start_report_generation(report_id: str):
    """
    Start report generation in background thread
    """
    thread = Thread(target=_generate_report_async, args=(report_id,))
    thread.start()


def _generate_report_async(report_id: str):
    """
    Generate the report asynchronously
    """
    try:
        # Generate both CSV and JSON data
        csv_data, json_data = generate_report_data()
        
        # Update job as complete
        update_report_job(report_id, "Complete", csv_data=csv_data, json_data=json_data)
        
    except Exception as e:
        # Mark report as failed
        update_report_job(report_id, "Failed", error_message=str(e))


def get_report_status(report_id: str) -> dict:
    """
    Get report job status and data
    Returns dict with status info
    """
    db = SessionLocal()
    try:
        report_job = db.query(ReportJob).filter(ReportJob.report_id == report_id).first()
        
        if not report_job:
            return {"error": "Report not found", "status_code": 404}
        
        if report_job.status == "Running":
            return {"status": "Running", "status_code": 200}
        elif report_job.status == "Complete":
            return {
                "status": "Complete", 
                "csv_data": report_job.csv_data,
                "status_code": 200
            }
        else:  # Failed
            return {
                "error": f"Report generation failed: {report_job.error_message}",
                "status_code": 500
            }
            
    finally:
        db.close()
