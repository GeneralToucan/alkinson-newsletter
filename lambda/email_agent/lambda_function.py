"""
Email Agent Lambda Function

This Lambda function handles newsletter email distribution:
- Retrieves active subscribers from DynamoDB
- Loads weekly content from S3
- Formats and sends newsletter emails via SES
- Tracks delivery status and handles bounces/complaints
"""

import json
import os
import logging
from datetime import datetime, timezone
from typing import Dict, Any

from shared.models import WeeklySummary
from shared.aws_clients import S3Client, DynamoDBClient, SESClient
from subscriber_manager import SubscriberManager
from email_formatter import EmailFormatter
from email_sender import EmailSender

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context) -> Dict[str, Any]:
    """
    Email Agent Lambda Function handler.
    
    Args:
        event: Lambda event data (can contain week_id or use current week)
        context: Lambda context
        
    Returns:
        Dict with execution results
    """
    logger.info("Email Agent started")
    logger.info(f"Event: {json.dumps(event)}")
    
    # Environment variables
    content_bucket = os.environ.get('CONTENT_BUCKET', 'alkinson-newsletter-content')
    subscribers_table = os.environ.get('SUBSCRIBERS_TABLE', 'alkinson-subscribers')
    sender_email = os.environ.get('SENDER_EMAIL', 'newsletter@example.com')
    base_url = os.environ.get('BASE_URL', 'https://your-domain.com')
    region = os.environ.get('AWS_REGION', 'ap-southeast-2')
    
    try:
        # Initialize AWS clients
        s3_client = S3Client(bucket_name=content_bucket, region_name=region)
        dynamodb_client = DynamoDBClient(table_name=subscribers_table, region_name=region)
        ses_client = SESClient(sender_email=sender_email, region_name=region)
        
        # Initialize managers
        subscriber_manager = SubscriberManager(dynamodb_client)
        email_formatter = EmailFormatter(base_url=base_url)
        email_sender = EmailSender(ses_client, email_formatter)
        
        # Get weekly content from S3
        logger.info("Loading weekly content from S3")
        week_id = event.get('week_id')  # Optional: specify week, otherwise use current
        
        if week_id:
            content_key = f"data/archive/{week_id}.json"
        else:
            content_key = "data/current-week.json"
        
        content_data = s3_client.download_json(content_key)
        
        if not content_data:
            logger.error(f"No content found at {content_key}")
            return {
                'statusCode': 404,
                'body': json.dumps({
                    'error': 'Weekly content not found',
                    'content_key': content_key,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
            }
        
        # Parse weekly summary
        weekly_summary = WeeklySummary(**content_data)
        logger.info(f"Loaded weekly summary: {weekly_summary.week_id}")
        
        # Get subscribers organized in batches
        logger.info("Retrieving active subscribers")
        subscriber_batches = subscriber_manager.get_subscribers_for_sending(batch_size=50)
        
        if not subscriber_batches:
            logger.warning("No active subscribers found")
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'No active subscribers to send to',
                    'week_id': weekly_summary.week_id,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
            }
        
        total_subscribers = sum(len(batch) for batch in subscriber_batches)
        logger.info(f"Found {total_subscribers} subscribers in {len(subscriber_batches)} batches")
        
        # Send emails to all batches
        logger.info("Starting email distribution")
        send_results = email_sender.send_to_all_batches(weekly_summary, subscriber_batches)
        
        # Get final statistics
        send_stats = email_sender.get_send_statistics()
        
        # Prepare response
        response = {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Email Agent completed successfully',
                'week_id': weekly_summary.week_id,
                'send_results': {
                    'total_subscribers': send_results['total_subscribers'],
                    'successful': send_results['successful'],
                    'failed': send_results['failed'],
                    'skipped': send_results['skipped']
                },
                'statistics': send_stats,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }, default=str)
        }
        
        logger.info(f"Email Agent completed: {send_results['successful']} emails sent successfully")
        return response
        
    except Exception as e:
        logger.error(f"Error in Email Agent: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'error_type': type(e).__name__,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
        }


def handle_sns_notification(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Handle SNS notifications for bounces and complaints.
    
    This function can be configured as a separate Lambda or as part of the main handler.
    
    Args:
        event: SNS event data
        context: Lambda context
        
    Returns:
        Dict with handling results
    """
    logger.info("Processing SNS notification")
    
    try:
        # Parse SNS message
        for record in event.get('Records', []):
            sns_message = json.loads(record['Sns']['Message'])
            notification_type = sns_message.get('notificationType')
            
            logger.info(f"Notification type: {notification_type}")
            
            # Initialize email sender for notification handling
            ses_client = SESClient(
                sender_email=os.environ.get('SENDER_EMAIL', 'newsletter@example.com')
            )
            email_formatter = EmailFormatter()
            email_sender = EmailSender(ses_client, email_formatter)
            
            if notification_type == 'Bounce':
                result = email_sender.handle_bounce_notification(sns_message)
                logger.info(f"Bounce handled: {result}")
                
                # If permanent bounce, should unsubscribe (requires DynamoDB access)
                if result.get('action_taken') == 'should_unsubscribe':
                    dynamodb_client = DynamoDBClient(
                        table_name=os.environ.get('SUBSCRIBERS_TABLE', 'alkinson-subscribers')
                    )
                    for email in result['affected_emails']:
                        from shared.models import SubscriberStatus
                        dynamodb_client.update_subscriber_status(email, SubscriberStatus.UNSUBSCRIBED)
                        logger.info(f"Unsubscribed {email} due to permanent bounce")
            
            elif notification_type == 'Complaint':
                result = email_sender.handle_complaint_notification(sns_message)
                logger.info(f"Complaint handled: {result}")
                
                # Unsubscribe complainers
                if result.get('action_taken') == 'should_unsubscribe':
                    dynamodb_client = DynamoDBClient(
                        table_name=os.environ.get('SUBSCRIBERS_TABLE', 'alkinson-subscribers')
                    )
                    for email in result['affected_emails']:
                        from shared.models import SubscriberStatus
                        dynamodb_client.update_subscriber_status(email, SubscriberStatus.UNSUBSCRIBED)
                        logger.info(f"Unsubscribed {email} due to complaint")
        
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'SNS notification processed'})
        }
        
    except Exception as e:
        logger.error(f"Error processing SNS notification: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }