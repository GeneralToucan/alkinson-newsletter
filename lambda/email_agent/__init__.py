"""
Email Agent Lambda Function Package

This package contains the Email Agent Lambda function for Alkinson's Newsletter.
It handles newsletter email distribution to subscribers.
"""

from .lambda_function import lambda_handler, handle_sns_notification
from .subscriber_manager import SubscriberManager
from .email_formatter import EmailFormatter
from .email_sender import EmailSender

__all__ = [
    'lambda_handler',
    'handle_sns_notification',
    'SubscriberManager',
    'EmailFormatter',
    'EmailSender'
]