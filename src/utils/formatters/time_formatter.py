"""Utility for formatting time durations."""

from typing import Union

def format_time(seconds: Union[int, float]) -> str:
    """Format time in seconds to human-readable string.
    
    Args:
        seconds: Time duration in seconds
        
    Returns:
        Human-readable time string (e.g., "2h 15m")
    """
    if seconds is None or seconds < 0 or seconds == float('inf'):
        return "Unknown"
    
    # Convert to integer seconds
    total_seconds = int(seconds)
    
    # Calculate days, hours, minutes, seconds
    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60
    remaining_seconds = total_seconds % 60
    
    # Format based on duration
    if days > 0:
        return f"{days}d {hours}h" if hours > 0 else f"{days}d"
    elif hours > 0:
        return f"{hours}h {minutes}m" if minutes > 0 else f"{hours}h"
    elif minutes > 0:
        return f"{minutes}m" if remaining_seconds < 10 else f"{minutes}m {remaining_seconds}s"
    else:
        return f"{remaining_seconds}s" 