"""
Shared utilities and models for Alkinson's Newsletter system.

This package contains common data models, utility functions, and AWS service
clients that are used across multiple Lambda functions.
"""

from .models import (
    Article,
    DiseaseSection,
    WeeklySummary,
    Subscriber,
    SubscriberStatus,
    EmailTemplate,
    ProcessingResult
)

from .utils import (
    get_current_week_id,
    get_week_id_for_date,
    get_week_start_end,
    get_previous_week_id,
    get_next_week_id,
    generate_secure_token,
    generate_unsubscribe_token,
    format_date_for_display,
    format_week_display,
    is_valid_email_format,
    sanitize_html_content,
    get_s3_key_for_week,
    get_current_week_s3_keys
)

from .aws_clients import (
    S3Client,
    DynamoDBClient,
    SESClient,
    RetryConfig
)

__all__ = [
    # Models
    'Article',
    'DiseaseSection', 
    'WeeklySummary',
    'Subscriber',
    'SubscriberStatus',
    'EmailTemplate',
    'ProcessingResult',
    
    # Utilities
    'get_current_week_id',
    'get_week_id_for_date',
    'get_week_start_end',
    'get_previous_week_id',
    'get_next_week_id',
    'generate_secure_token',
    'generate_unsubscribe_token',
    'format_date_for_display',
    'format_week_display',
    'is_valid_email_format',
    'sanitize_html_content',
    'get_s3_key_for_week',
    'get_current_week_s3_keys',
    
    # AWS Clients
    'S3Client',
    'DynamoDBClient',
    'SESClient',
    'RetryConfig'
]