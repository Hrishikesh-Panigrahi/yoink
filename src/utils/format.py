from __future__ import annotations


def format_size(num_bytes: float) -> str:
    if num_bytes is None or num_bytes <= 0:
        return "0 B"
    value = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024.0:
            return f"{value:.1f} {unit}"
        value /= 1024.0
    return f"{value:.1f} PB"


def format_speed(bytes_per_second: float) -> str:
    if not bytes_per_second or bytes_per_second <= 0:
        return "0 B/s"
    return f"{format_size(bytes_per_second)}/s"


def format_eta(seconds: float) -> str:
    if seconds is None or seconds <= 0:
        return "Unknown"
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    minutes, sec = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m {sec}s"
    hours, minutes = divmod(minutes, 60)
    if hours < 24:
        return f"{hours}h {minutes}m"
    days, hours = divmod(hours, 24)
    return f"{days}d {hours}h"
