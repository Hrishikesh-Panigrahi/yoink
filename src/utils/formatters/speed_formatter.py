"""Utility for formatting data transfer speeds."""

from typing import Union

def format_speed(speed_bytes_per_sec: Union[int, float]) -> str:
    """Format speed in bytes/sec to human-readable string.
    
    Args:
        speed_bytes_per_sec: Speed in bytes per second
        
    Returns:
        Human-readable speed string (e.g., "1.5 MB/s")
    """
    if speed_bytes_per_sec < 0:
        return "0 B/s"
        
    if speed_bytes_per_sec < 1024:
        return f"{speed_bytes_per_sec:.0f} B/s"
    elif speed_bytes_per_sec < 1024 * 1024:
        return f"{speed_bytes_per_sec/1024:.1f} KB/s"
    elif speed_bytes_per_sec < 1024 * 1024 * 1024:
        return f"{speed_bytes_per_sec/(1024*1024):.1f} MB/s"
    else:
        return f"{speed_bytes_per_sec/(1024*1024*1024):.1f} GB/s" 