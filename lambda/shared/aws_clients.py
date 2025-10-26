"""
AWS service clients and utilities for Alkinson's Newsletter system.

This module provides wrapper classes for AWS services with error handling,
retry logic, and newsletter-specific functionality.
"""

import boto3
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from botocore.exceptions import ClientError, BotoCoreError
from botocore.config import Config
import time
import random
from datetime import datetime, timezone

from .models import Subscriber, WeeklySummary, SubscriberStatus
from .utils import generate_unsubscribe_token

# Configure logging
logger = logging.getLogger(__name__)


class RetryConfig:
    """Configuration for retry logic."""
    MAX_RETRIES = 3
    BASE_DELAY = 1.0
    MAX_DELAY = 60.0
    BACKOFF_MULTIPLIER = 2.0


def exponential_backoff_retry(func):
    """Decorator for exponential backoff retry logic."""
    def wrapper(*args, **kwargs):
        last_exception = None
        
        for attempt in range(RetryConfig.MAX_RETRIES):
            try:
                return func(*args, **kwargs)
            except (ClientError, BotoCoreError) as e:
                last_exception = e
                if attempt == RetryConfig.MAX_RETRIES - 1:
                    break
                
                # Calculate delay with jitter
                delay = min(
                    RetryConfig.BASE_DELAY * (RetryConfig.BACKOFF_MULTIPLIER ** attempt),
                    RetryConfig.MAX_DELAY
                )
                jitter = random.uniform(0, delay * 0.1)
                time.sleep(delay + jitter)
                
                logger.warning(f"Retry attempt {attempt + 1} after error: {str(e)}")
        
        raise last_exception
    
    return wrapper


class S3Client:
    """S3 client wrapper with error handling and retry logic."""
    
    def __init__(self, bucket_name: str, region_name: str = 'ap-southeast-2'):
        """
        Initialize S3 client.
        
        Args:
            bucket_name: S3 bucket name for newsletter content
            region_name: AWS region name
        """
        self.bucket_name = bucket_name
        self.region_name = region_name
        
        # Configure client with retry settings
        config = Config(
            region_name=region_name,
            retries={'max_attempts': 3, 'mode': 'adaptive'},
            max_pool_connections=50
        )
        
        self.client = boto3.client('s3', config=config)
        logger.info(f"S3 client initialized for bucket: {bucket_name}")
    
    @exponential_backoff_retry
    def upload_json(self, key: str, data: Dict[str, Any]) -> bool:
        """
        Upload JSON data to S3.
        
        Args:
            key: S3 object key
            data: Dictionary to upload as JSON
            
        Returns:
            bool: True if successful
        """
        try:
            json_content = json.dumps(data, indent=2, default=str)
            
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=json_content,
                ContentType='application/json',
                CacheControl='max-age=300'  # 5 minutes cache
            )
            
            logger.info(f"Successfully uploaded JSON to s3://{self.bucket_name}/{key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upload JSON to S3: {str(e)}")
            raise
    
    @exponential_backoff_retry
    def upload_html(self, key: str, html_content: str) -> bool:
        """
        Upload HTML content to S3.
        
        Args:
            key: S3 object key
            html_content: HTML content string
            
        Returns:
            bool: True if successful
        """
        try:
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=html_content,
                ContentType='text/html',
                CacheControl='max-age=3600'  # 1 hour cache
            )
            
            logger.info(f"Successfully uploaded HTML to s3://{self.bucket_name}/{key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upload HTML to S3: {str(e)}")
            raise
    
    @exponential_backoff_retry
    def download_json(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Download and parse JSON from S3.
        
        Args:
            key: S3 object key
            
        Returns:
            Dict or None if not found
        """
        try:
            response = self.client.get_object(Bucket=self.bucket_name, Key=key)
            content = response['Body'].read().decode('utf-8')
            return json.loads(content)
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.info(f"Object not found: s3://{self.bucket_name}/{key}")
                return None
            raise
        except Exception as e:
            logger.error(f"Failed to download JSON from S3: {str(e)}")
            raise
    
    @exponential_backoff_retry
    def download_text(self, key: str) -> Optional[str]:
        """
        Download text content from S3.
        
        Args:
            key: S3 object key
            
        Returns:
            str or None if not found
        """
        try:
            response = self.client.get_object(Bucket=self.bucket_name, Key=key)
            return response['Body'].read().decode('utf-8')
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.info(f"Object not found: s3://{self.bucket_name}/{key}")
                return None
            raise
        except Exception as e:
            logger.error(f"Failed to download text from S3: {str(e)}")
            raise
    
    def upload_weekly_summary(self, weekly_summary: WeeklySummary) -> Tuple[str, str]:
        """
        Upload weekly summary to both current and archive locations.
        
        Args:
            weekly_summary: WeeklySummary model instance
            
        Returns:
            Tuple of (current_key, archive_key)
        """
        # Convert to dict for JSON serialization
        summary_dict = weekly_summary.dict()
        
        # Upload to current week location
        current_key = "data/current-week.json"
        self.upload_json(current_key, summary_dict)
        
        # Upload to archive location
        archive_key = f"data/archive/{weekly_summary.week_id}.json"
        self.upload_json(archive_key, summary_dict)
        
        return current_key, archive_key


class DynamoDBClient:
    """DynamoDB client wrapper for subscriber management."""
    
    def __init__(self, table_name: str, region_name: str = 'ap-southeast-2'):
        """
        Initialize DynamoDB client.
        
        Args:
            table_name: DynamoDB table name for subscribers
            region_name: AWS region name
        """
        self.table_name = table_name
        self.region_name = region_name
        
        # Configure client with retry settings
        config = Config(
            region_name=region_name,
            retries={'max_attempts': 3, 'mode': 'adaptive'}
        )
        
        self.client = boto3.client('dynamodb', config=config)
        self.resource = boto3.resource('dynamodb', config=config)
        self.table = self.resource.Table(table_name)
        
        logger.info(f"DynamoDB client initialized for table: {table_name}")
    
    @exponential_backoff_retry
    def add_subscriber(self, email: str, confirmation_token: str) -> Subscriber:
        """
        Add a new subscriber to the database.
        
        Args:
            email: Subscriber email address
            confirmation_token: Email confirmation token
            
        Returns:
            Subscriber: Created subscriber model
        """
        try:
            subscriber = Subscriber(
                email=email,
                status=SubscriberStatus.PENDING_CONFIRMATION,
                confirmation_token=confirmation_token,
                unsubscribe_token=generate_unsubscribe_token(email)
            )
            
            # Use put_item with condition to prevent overwrites
            self.table.put_item(
                Item=subscriber.to_dynamodb_item(),
                ConditionExpression='attribute_not_exists(email)'
            )
            
            logger.info(f"Added new subscriber: {email}")
            return subscriber
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                logger.warning(f"Subscriber already exists: {email}")
                # Return existing subscriber
                return self.get_subscriber(email)
            raise
        except Exception as e:
            logger.error(f"Failed to add subscriber: {str(e)}")
            raise
    
    @exponential_backoff_retry
    def get_subscriber(self, email: str) -> Optional[Subscriber]:
        """
        Get subscriber by email address.
        
        Args:
            email: Subscriber email address
            
        Returns:
            Subscriber or None if not found
        """
        try:
            response = self.table.get_item(Key={'email': email})
            
            if 'Item' in response:
                return Subscriber.from_dynamodb_item(response['Item'])
            return None
            
        except Exception as e:
            logger.error(f"Failed to get subscriber: {str(e)}")
            raise
    
    @exponential_backoff_retry
    def update_subscriber_status(self, email: str, status: SubscriberStatus) -> bool:
        """
        Update subscriber status.
        
        Args:
            email: Subscriber email address
            status: New status
            
        Returns:
            bool: True if successful
        """
        try:
            self.table.update_item(
                Key={'email': email},
                UpdateExpression='SET #status = :status',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={':status': status.value},
                ConditionExpression='attribute_exists(email)'
            )
            
            logger.info(f"Updated subscriber status: {email} -> {status.value}")
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                logger.warning(f"Subscriber not found for status update: {email}")
                return False
            raise
        except Exception as e:
            logger.error(f"Failed to update subscriber status: {str(e)}")
            raise
    
    @exponential_backoff_retry
    def get_active_subscribers(self) -> List[Subscriber]:
        """
        Get all active subscribers.
        
        Returns:
            List of active Subscriber models
        """
        try:
            response = self.table.scan(
                FilterExpression='#status = :status',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={':status': SubscriberStatus.ACTIVE.value}
            )
            
            subscribers = []
            for item in response.get('Items', []):
                subscribers.append(Subscriber.from_dynamodb_item(item))
            
            logger.info(f"Retrieved {len(subscribers)} active subscribers")
            return subscribers
            
        except Exception as e:
            logger.error(f"Failed to get active subscribers: {str(e)}")
            raise
    
    @exponential_backoff_retry
    def confirm_subscriber(self, email: str, confirmation_token: str) -> bool:
        """
        Confirm subscriber email with token validation.
        
        Args:
            email: Subscriber email address
            confirmation_token: Confirmation token to validate
            
        Returns:
            bool: True if confirmation successful
        """
        try:
            # Get current subscriber
            subscriber = self.get_subscriber(email)
            if not subscriber:
                logger.warning(f"Subscriber not found for confirmation: {email}")
                return False
            
            # Validate token
            if subscriber.confirmation_token != confirmation_token:
                logger.warning(f"Invalid confirmation token for: {email}")
                return False
            
            # Update status to active
            return self.update_subscriber_status(email, SubscriberStatus.ACTIVE)
            
        except Exception as e:
            logger.error(f"Failed to confirm subscriber: {str(e)}")
            raise


class SESClient:
    """SES client wrapper for email operations with bounce handling."""
    
    def __init__(self, sender_email: str, region_name: str = 'ap-southeast-2'):
        """
        Initialize SES client.
        
        Args:
            sender_email: Verified sender email address
            region_name: AWS region name
        """
        self.sender_email = sender_email
        self.region_name = region_name
        
        # Configure client with retry settings
        config = Config(
            region_name=region_name,
            retries={'max_attempts': 3, 'mode': 'adaptive'}
        )
        
        self.client = boto3.client('ses', config=config)
        logger.info(f"SES client initialized with sender: {sender_email}")
    
    @exponential_backoff_retry
    def send_email(self, to_email: str, subject: str, html_body: str, 
                   text_body: Optional[str] = None) -> str:
        """
        Send email via SES.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_body: HTML email body
            text_body: Optional plain text body
            
        Returns:
            str: SES message ID
        """
        try:
            # Prepare email body
            body = {'Html': {'Data': html_body, 'Charset': 'UTF-8'}}
            if text_body:
                body['Text'] = {'Data': text_body, 'Charset': 'UTF-8'}
            
            response = self.client.send_email(
                Source=self.sender_email,
                Destination={'ToAddresses': [to_email]},
                Message={
                    'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                    'Body': body
                }
            )
            
            message_id = response['MessageId']
            logger.info(f"Email sent successfully to {to_email}, MessageId: {message_id}")
            return message_id
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            raise
    
    @exponential_backoff_retry
    def send_bulk_email(self, subscribers: List[Subscriber], subject: str, 
                       html_body: str, text_body: Optional[str] = None) -> Dict[str, Any]:
        """
        Send bulk email to multiple subscribers.
        
        Args:
            subscribers: List of Subscriber models
            subject: Email subject
            html_body: HTML email body
            text_body: Optional plain text body
            
        Returns:
            Dict with send results
        """
        results = {
            'successful': 0,
            'failed': 0,
            'errors': []
        }
        
        # SES free tier limit: 200 emails per day
        # Process in batches to respect limits
        batch_size = 50  # Conservative batch size
        
        for i in range(0, len(subscribers), batch_size):
            batch = subscribers[i:i + batch_size]
            
            for subscriber in batch:
                try:
                    # Personalize unsubscribe link for each subscriber
                    personalized_html = html_body.replace(
                        '{{unsubscribe_url}}',
                        f"https://your-domain.com/unsubscribe?token={subscriber.unsubscribe_token}"
                    )
                    
                    message_id = self.send_email(
                        to_email=str(subscriber.email),
                        subject=subject,
                        html_body=personalized_html,
                        text_body=text_body
                    )
                    
                    results['successful'] += 1
                    
                except Exception as e:
                    results['failed'] += 1
                    results['errors'].append({
                        'email': str(subscriber.email),
                        'error': str(e)
                    })
                    logger.error(f"Failed to send email to {subscriber.email}: {str(e)}")
            
            # Add delay between batches to respect rate limits
            if i + batch_size < len(subscribers):
                time.sleep(1)  # 1 second delay between batches
        
        logger.info(f"Bulk email completed: {results['successful']} successful, {results['failed']} failed")
        return results
    
    def send_confirmation_email(self, email: str, confirmation_token: str) -> str:
        """
        Send subscription confirmation email.
        
        Args:
            email: Subscriber email address
            confirmation_token: Confirmation token
            
        Returns:
            str: SES message ID
        """
        subject = "Confirm your Alkinson's Newsletter subscription"
        
        html_body = f"""
        <html>
        <body>
            <h2>Welcome to Alkinson's Newsletter!</h2>
            <p>Thank you for subscribing to our weekly newsletter about Alzheimer's and Parkinson's disease research.</p>
            <p>Please click the link below to confirm your subscription:</p>
            <p><a href="https://your-domain.com/confirm?token={confirmation_token}&email={email}">Confirm Subscription</a></p>
            <p>If you didn't subscribe to this newsletter, you can safely ignore this email.</p>
        </body>
        </html>
        """
        
        text_body = f"""
        Welcome to Alkinson's Newsletter!
        
        Thank you for subscribing to our weekly newsletter about Alzheimer's and Parkinson's disease research.
        
        Please visit the following link to confirm your subscription:
        https://your-domain.com/confirm?token={confirmation_token}&email={email}
        
        If you didn't subscribe to this newsletter, you can safely ignore this email.
        """
        
        return self.send_email(email, subject, html_body, text_body)