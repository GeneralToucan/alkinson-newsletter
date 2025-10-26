"""
Utility functions for Alkinson's Newsletter system.

This module provides common utility functions for date handling,
week ID generation, and other shared functionality.
"""

from datetime import datetime, timezone, timedelta
from typing import Tuple, Optional
import secrets
import string
import hashlib


def get_current_week_id() -> str:
    """
    Generate week ID for the current week.
    
    Returns:
        str: Week ID in format 'YYYY-week-NN' (e.g., '2024-week-01')
    """
    now = datetime.now(timezone.utc)
    return get_week_id_for_date(now)


def get_week_id_for_date(date: datetime) -> str:
    """
    Generate week ID for a specific date.
    
    Args:
        date: The date to generate week ID for
        
    Returns:
        str: Week ID in format 'YYYY-week-NN'
    """
    # Get the ISO week number (1-53)
    year, week_num, _ = date.isocalendar()
    return f"{year}-week-{week_num:02d}"


def get_week_start_end(week_id: str) -> Tuple[datetime, datetime]:
    """
    Get start and end dates for a given week ID.
    
    Args:
        week_id: Week ID in format 'YYYY-week-NN'
        
    Returns:
        Tuple of (start_date, end_date) for the week
        
    Raises:
        ValueError: If week_id format is invalid
    """
    try:
        parts = week_id.split('-')
        if len(parts) != 3 or parts[1] != 'week':
            raise ValueError(f"Invalid week ID format: {week_id}")
        
        year = int(parts[0])
        week_num = int(parts[2])
        
        # Get the first day of the year
        jan_1 = datetime(year, 1, 1, tzinfo=timezone.utc)
        
        # Find the first Monday of the year (ISO week starts on Monday)
        days_to_monday = (7 - jan_1.weekday()) % 7
        if jan_1.weekday() > 3:  # If Jan 1 is Thu-Sun, first week is next week
            days_to_monday += 7
        
        first_monday = jan_1 + timedelta(days=days_to_monday)
        
        # Calculate the start of the requested week
        week_start = first_monday + timedelta(weeks=week_num - 1)
        week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)
        
        return week_start, week_end
        
    except (ValueError, IndexError) as e:
        raise ValueError(f"Invalid week ID format: {week_id}") from e


def get_previous_week_id(week_id: Optional[str] = None) -> str:
    """
    Get the week ID for the previous week.
    
    Args:
        week_id: Current week ID. If None, uses current week.
        
    Returns:
        str: Previous week ID
    """
    if week_id is None:
        week_id = get_current_week_id()
    
    start_date, _ = get_week_start_end(week_id)
    previous_week_date = start_date - timedelta(days=7)
    return get_week_id_for_date(previous_week_date)


def get_next_week_id(week_id: Optional[str] = None) -> str:
    """
    Get the week ID for the next week.
    
    Args:
        week_id: Current week ID. If None, uses current week.
        
    Returns:
        str: Next week ID
    """
    if week_id is None:
        week_id = get_current_week_id()
    
    start_date, _ = get_week_start_end(week_id)
    next_week_date = start_date + timedelta(days=7)
    return get_week_id_for_date(next_week_date)


def generate_secure_token(length: int = 32) -> str:
    """
    Generate a cryptographically secure random token.
    
    Args:
        length: Length of the token to generate
        
    Returns:
        str: Secure random token
    """
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def generate_unsubscribe_token(email: str, timestamp: Optional[datetime] = None) -> str:
    """
    Generate a secure unsubscribe token for an email address.
    
    Args:
        email: Email address to generate token for
        timestamp: Optional timestamp to include in token generation
        
    Returns:
        str: Secure unsubscribe token
    """
    if timestamp is None:
        timestamp = datetime.now(timezone.utc)
    
    # Create a hash of email + timestamp + secret
    secret_key = generate_secure_token(16)  # In production, use environment variable
    data = f"{email}:{timestamp.isoformat()}:{secret_key}"
    token_hash = hashlib.sha256(data.encode()).hexdigest()
    
    return token_hash[:32]  # Return first 32 characters


def format_date_for_display(date: datetime) -> str:
    """
    Format a datetime for user-friendly display.
    
    Args:
        date: Datetime to format
        
    Returns:
        str: Formatted date string
    """
    return date.strftime("%B %d, %Y")


def format_week_display(week_id: str) -> str:
    """
    Format a week ID for user-friendly display.
    
    Args:
        week_id: Week ID in format 'YYYY-week-NN'
        
    Returns:
        str: Formatted week string (e.g., "Week of January 1, 2024")
    """
    try:
        start_date, _ = get_week_start_end(week_id)
        return f"Week of {format_date_for_display(start_date)}"
    except ValueError:
        return week_id  # Return original if parsing fails


def is_valid_email_format(email: str) -> bool:
    """
    Basic email format validation.
    
    Args:
        email: Email address to validate
        
    Returns:
        bool: True if email format appears valid
    """
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def sanitize_html_content(content: str) -> str:
    """
    Basic HTML sanitization for user content.
    
    Args:
        content: HTML content to sanitize
        
    Returns:
        str: Sanitized HTML content
    """
    import html
    # Basic HTML escaping - in production, use a proper HTML sanitizer
    return html.escape(content)


def get_s3_key_for_week(week_id: str, file_type: str = "json") -> str:
    """
    Generate S3 key for storing weekly content.
    
    Args:
        week_id: Week ID
        file_type: File type (json, html)
        
    Returns:
        str: S3 key path
    """
    if file_type == "json":
        return f"data/archive/{week_id}.json"
    elif file_type == "html":
        return f"website/archive/{week_id}.html"
    else:
        raise ValueError(f"Unsupported file type: {file_type}")


def get_current_week_s3_keys() -> Tuple[str, str]:
    """
    Get S3 keys for current week's JSON and HTML files.
    
    Returns:
        Tuple of (json_key, html_key)
    """
    week_id = get_current_week_id()
    json_key = "data/current-week.json"
    html_key = "website/index.html"
    return json_key, html_key