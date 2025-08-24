"""
Search service for restaurant data
Handles searching through generated reports
"""

import json
from typing import Dict, List, Optional, Any

from ..database import SessionLocal
from ..models import ReportJob


def search_report(report_id: str, store_id: Optional[str] = None, min_uptime: Optional[float] = None) -> Dict[str, Any]:
    """
    Search for restaurant data in a specific report
    
    Args:
        report_id: The report to search in
        store_id: Filter by specific store ID (optional)
        min_uptime: Filter by minimum uptime percentage (optional)
    
    Returns:
        Dictionary with search results
    """
    db = SessionLocal()
    try:
        # Get the report
        report_job = db.query(ReportJob).filter(ReportJob.report_id == report_id).first()
        
        if not report_job:
            return {"error": "Report not found", "status_code": 404}
        
        if report_job.status != "Complete":
            return {"error": f"Report is {report_job.status.lower()}", "status_code": 400}
        
        if not report_job.json_data:
            return {"error": "No JSON data available for this report", "status_code": 400}
        
        # Parse JSON data
        try:
            report_data = json.loads(report_job.json_data)
        except json.JSONDecodeError:
            return {"error": "Invalid JSON data in report", "status_code": 500}
        
        # Get stores data
        all_stores = report_data.get("stores", [])
        filtered_stores = []
        
        # Apply filters
        for store in all_stores:
            # Filter by store_id if provided
            if store_id and store["store_id"] != store_id:
                continue
            
            # Filter by minimum uptime if provided
            if min_uptime is not None:
                avg_uptime = (
                    store["uptime_percentage"]["last_hour"] +
                    store["uptime_percentage"]["last_day"] +
                    store["uptime_percentage"]["last_week"]
                ) / 3
                if avg_uptime < min_uptime:
                    continue
            
            filtered_stores.append(store)
        
        # Prepare response
        result = {
            "report_id": report_id,
            "report_metadata": report_data.get("report_metadata", {}),
            "filters_applied": {
                "store_id": store_id,
                "min_uptime": min_uptime
            },
            "results": {
                "total_stores_found": len(filtered_stores),
                "stores": filtered_stores
            },
            "status_code": 200
        }
        
        return result
        
    finally:
        db.close()


def get_store_details(report_id: str, store_id: str) -> Dict[str, Any]:
    """
    Get detailed information for a specific store
    
    Args:
        report_id: The report to search in
        store_id: The specific store ID
    
    Returns:
        Detailed store information
    """
    search_result = search_report(report_id, store_id=store_id)
    
    if search_result.get("status_code") != 200:
        return search_result
    
    stores = search_result["results"]["stores"]
    if not stores:
        return {"error": f"Store {store_id} not found in report", "status_code": 404}
    
    store_data = stores[0]  # Should be only one since we filtered by store_id
    
    # Add enhanced details for frontend
    enhanced_data = {
        "report_id": report_id,
        "store_id": store_id,
        "uptime_data": {
            "last_hour": {
                "uptime_minutes": store_data["uptime_last_hour_minutes"],
                "downtime_minutes": store_data["downtime_last_hour_minutes"],
                "total_minutes": store_data["total_business_time"]["last_hour_minutes"],
                "uptime_percentage": store_data["uptime_percentage"]["last_hour"]
            },
            "last_day": {
                "uptime_hours": store_data["uptime_last_day_hours"],
                "downtime_hours": store_data["downtime_last_day_hours"],
                "total_hours": store_data["total_business_time"]["last_day_hours"],
                "uptime_percentage": store_data["uptime_percentage"]["last_day"]
            },
            "last_week": {
                "uptime_hours": store_data["uptime_last_week_hours"],
                "downtime_hours": store_data["downtime_last_week_hours"],
                "total_hours": store_data["total_business_time"]["last_week_hours"],
                "uptime_percentage": store_data["uptime_percentage"]["last_week"]
            }
        },
        "summary": {
            "average_uptime_percentage": round(
                (store_data["uptime_percentage"]["last_hour"] +
                 store_data["uptime_percentage"]["last_day"] +
                 store_data["uptime_percentage"]["last_week"]) / 3, 1
            ),
            "performance_status": _get_performance_status(store_data),
            "total_business_hours_week": store_data["total_business_time"]["last_week_hours"]
        },
        "raw_data": store_data,  # Include original data for reference
        "status_code": 200
    }
    
    return enhanced_data


def _get_performance_status(store_data: Dict[str, Any]) -> str:
    """
    Get performance status based on uptime percentages
    """
    avg_uptime = (
        store_data["uptime_percentage"]["last_hour"] +
        store_data["uptime_percentage"]["last_day"] +
        store_data["uptime_percentage"]["last_week"]
    ) / 3
    
    if avg_uptime >= 95:
        return "Excellent"
    elif avg_uptime >= 90:
        return "Good"
    elif avg_uptime >= 80:
        return "Fair"
    elif avg_uptime >= 70:
        return "Poor"
    else:
        return "Critical"


def get_report_summary(report_id: str) -> Dict[str, Any]:
    """
    Get summary statistics for the entire report
    """
    db = SessionLocal()
    try:
        report_job = db.query(ReportJob).filter(ReportJob.report_id == report_id).first()
        
        if not report_job or report_job.status != "Complete" or not report_job.json_data:
            return {"error": "Report not available", "status_code": 400}
        
        report_data = json.loads(report_job.json_data)
        stores = report_data.get("stores", [])
        
        if not stores:
            return {"error": "No store data in report", "status_code": 400}
        
        # Calculate summary statistics
        total_stores = len(stores)
        uptime_percentages = []
        
        excellent_stores = 0
        good_stores = 0
        fair_stores = 0
        poor_stores = 0
        critical_stores = 0
        
        for store in stores:
            avg_uptime = (
                store["uptime_percentage"]["last_hour"] +
                store["uptime_percentage"]["last_day"] +
                store["uptime_percentage"]["last_week"]
            ) / 3
            uptime_percentages.append(avg_uptime)
            
            if avg_uptime >= 95:
                excellent_stores += 1
            elif avg_uptime >= 90:
                good_stores += 1
            elif avg_uptime >= 80:
                fair_stores += 1
            elif avg_uptime >= 70:
                poor_stores += 1
            else:
                critical_stores += 1
        
        summary = {
            "report_id": report_id,
            "report_metadata": report_data.get("report_metadata", {}),
            "summary_statistics": {
                "total_stores": total_stores,
                "average_uptime_percentage": round(sum(uptime_percentages) / len(uptime_percentages), 1),
                "min_uptime_percentage": round(min(uptime_percentages), 1),
                "max_uptime_percentage": round(max(uptime_percentages), 1),
                "performance_distribution": {
                    "excellent": {"count": excellent_stores, "percentage": round(excellent_stores/total_stores*100, 1)},
                    "good": {"count": good_stores, "percentage": round(good_stores/total_stores*100, 1)},
                    "fair": {"count": fair_stores, "percentage": round(fair_stores/total_stores*100, 1)},
                    "poor": {"count": poor_stores, "percentage": round(poor_stores/total_stores*100, 1)},
                    "critical": {"count": critical_stores, "percentage": round(critical_stores/total_stores*100, 1)}
                }
            },
            "status_code": 200
        }
        
        return summary
        
    finally:
        db.close()
