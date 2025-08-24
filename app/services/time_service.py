"""
Time and business hours calculation service
Handles timezone conversions and business period calculations
"""

from datetime import datetime, timedelta, time
import pytz
from typing import List, Tuple, Any


def get_business_periods_in_range(
    business_hours: List[Any], 
    start_time: datetime, 
    end_time: datetime, 
    store_tz: pytz.BaseTzInfo
) -> List[Tuple[datetime, datetime]]:
    """
    Get all business periods that overlap with the given time range
    Returns list of (period_start, period_end) tuples in store timezone
    """
    # Convert UTC times to store local time
    start_local = start_time.replace(tzinfo=pytz.UTC).astimezone(store_tz)
    end_local = end_time.replace(tzinfo=pytz.UTC).astimezone(store_tz)
    
    business_periods = []
    
    # Process each day in the range
    current_date = start_local.date()
    end_date = end_local.date()
    
    while current_date <= end_date:
        # Find business hours for this day (0=Monday, 6=Sunday)
        day_of_week = current_date.weekday()  # 0=Monday, 6=Sunday (matches CSV format)
        
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
            period_start = max(business_start, start_local)
            period_end = min(business_end, end_local)
            
            if period_start < period_end:
                business_periods.append((period_start, period_end))
        
        current_date += timedelta(days=1)
    
    return business_periods
