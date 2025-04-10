"""Utility for formatting file sizes."""

from typing import Union

def format_size(size_bytes: Union[int, float]) -> str:
    """Format size in bytes to human-readable string.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Human-readable size string (e.g., "15.2 MB")
    """
    if size_bytes < 0:
        return "0 B"
        
    if size_bytes < 1024:
        return f"{size_bytes:.0f} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes/1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes/(1024*1024):.1f} MB"
    elif size_bytes < 1024 * 1024 * 1024 * 1024:
        return f"{size_bytes/(1024*1024*1024):.2f} GB"
    else:
        return f"{size_bytes/(1024*1024*1024*1024):.2f} TB" 