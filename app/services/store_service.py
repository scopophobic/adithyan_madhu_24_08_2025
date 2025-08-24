"""
Store data service
Handles store-related data retrieval
"""

import pytz
from typing import List, Any

from ..models import StoreTimezone, StoreHours


def get_store_timezone(db, store_id: str) -> pytz.BaseTzInfo:
    """
    Get store timezone, default to America/Chicago if missing
    """
    timezone_record = db.query(StoreTimezone).filter(StoreTimezone.store_id == store_id).first()
    if timezone_record:
        return pytz.timezone(timezone_record.timezone_str)
    else:
        return pytz.timezone("America/Chicago")  # Default as per requirements


def get_store_business_hours(db, store_id: str) -> List[Any]:
    """
    Get store business hours, default to 24/7 if missing
    """
    business_hours = db.query(StoreHours).filter(StoreHours.store_id == store_id).all()
    
    if not business_hours:
        # Default: 24/7 operation as per requirements
        business_hours = []
        for day in range(7):  # 0=Monday to 6=Sunday
            business_hours.append(type('obj', (object,), {
                'dayOfWeek': day,
                'start_time_local': '00:00:00',
                'end_time_local': '23:59:59'
            }))
    
    return business_hours
