"""
Uptime calculation service
Contains the core extrapolation algorithm
"""

from datetime import datetime
import pytz
from typing import List, Tuple, Any


def extrapolate_uptime(
    observations: List[Any], 
    start_time: datetime, 
    end_time: datetime, 
    store_tz: pytz.BaseTzInfo
) -> Tuple[float, float]:
    """
    Extrapolate uptime/downtime from sparse observations
    
    Algorithm:
    - If no observations, assume store was operating normally (uptime)
    - Before first observation: assume same status as first observation
    - Between observations: assume previous status continues
    - After last observation: assume same status as last observation
    
    Returns: (uptime_minutes, downtime_minutes)
    """
    if not observations:
        # No data, assume store was operating normally during business hours
        total_minutes = (end_time - start_time).total_seconds() / 60
        return total_minutes, 0
    
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
