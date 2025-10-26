"""
SES email sending with delivery tracking for Email Agent.

This module handles sending formatted newsletters via SES,
implementing sending limits compliance, bounce/complaint handling,
and delivery status tracking.
"""

import logging
import time
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from shared.models import Subscriber, WeeklySummary
from shared.aws_clients import SESClient
from email_formatter import EmailFormatter

logger = logging.getLogger(__name__)


class EmailSender:
    """Handles email sending via SES with delivery tracking."""
    
    # SES free tier limits
    SES_DAILY_LIMIT = 200  # emails per day in free tier
    SES_RATE_LIMIT = 1  # email per second in free tier
    
    def __init__(self, ses_client: SESClient, email_formatter: EmailFormatter):
        """
        Initialize email sender.
        
        Args:
            ses_client: SES client instance
            email_formatter: Email formatter instance
        """
        self.ses_client = ses_client
        self.email_formatter = email_formatter
        self.emails_sent_today = 0
        self.send_errors = []
        logger.info("EmailSender initialized")
    
    def check_sending_limits(self, batch_size: int) -> bool:
        """
        Check if sending batch would exceed daily limits.
        
        Args:
            batch_size: Number of emails to send
            
        Returns:
            bool: True if within limits, False otherwise
        """
        if self.emails_sent_today + batch_size > self.SES_DAILY_LIMIT:
            logger.warning(
                f"Sending {batch_size} emails would exceed daily limit. "
                f"Already sent: {self.emails_sent_today}/{self.SES_DAILY_LIMIT}"
            )
            return False
        return True
    
    def send_single_email(self, weekly_summary: WeeklySummary, subscriber: Subscriber) -> Dict[str, Any]:
        """
        Send newsletter email to a single subscriber.
        
        Args:
            weekly_summary: Weekly summary content
            subscriber: Subscriber to send to
            
        Returns:
            Dict with send result
        """
        result = {
            'email': str(subscriber.email),
            'success': False,
            'message_id': None,
            'error': None,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        try:
            # Format email content
            email_content = self.email_formatter.format_email(weekly_summary, subscriber)
            
            # Send via SES
            message_id = self.ses_client.send_email(
                to_email=str(subscriber.email),
                subject=email_content['subject'],
                html_body=email_content['html_body'],
                text_body=email_content['text_body']
            )
            
            result['success'] = True
            result['message_id'] = message_id
            self.emails_sent_today += 1
            
            logger.info(f"Successfully sent email to {subscriber.email}, MessageId: {message_id}")
            
        except Exception as e:
            result['error'] = str(e)
            self.send_errors.append(result)
            logger.error(f"Failed to send email to {subscriber.email}: {str(e)}")
        
        return result
    
    def send_batch(self, weekly_summary: WeeklySummary, subscribers: List[Subscriber], 
                   respect_rate_limit: bool = True) -> Dict[str, Any]:
        """
        Send newsletter emails to a batch of subscribers.
        
        Args:
            weekly_summary: Weekly summary content
            subscribers: List of subscribers to send to
            respect_rate_limit: Whether to respect SES rate limits (default: True)
            
        Returns:
            Dict with batch send results
        """
        batch_results = {
            'total': len(subscribers),
            'successful': 0,
            'failed': 0,
            'skipped': 0,
            'results': [],
            'start_time': datetime.now(timezone.utc).isoformat()
        }
        
        # Check daily limits
        if not self.check_sending_limits(len(subscribers)):
            remaining = self.SES_DAILY_LIMIT - self.emails_sent_today
            logger.warning(f"Batch size exceeds daily limit. Processing only {remaining} emails.")
            subscribers = subscribers[:remaining]
            batch_results['skipped'] = batch_results['total'] - len(subscribers)
        
        # Send emails
        for i, subscriber in enumerate(subscribers):
            # Check if we've hit daily limit
            if self.emails_sent_today >= self.SES_DAILY_LIMIT:
                logger.warning("Daily sending limit reached. Stopping batch processing.")
                batch_results['skipped'] += len(subscribers) - i
                break
            
            # Send email
            result = self.send_single_email(weekly_summary, subscriber)
            batch_results['results'].append(result)
            
            if result['success']:
                batch_results['successful'] += 1
            else:
                batch_results['failed'] += 1
            
            # Respect rate limits (1 email per second)
            if respect_rate_limit and i < len(subscribers) - 1:
                time.sleep(1.0 / self.SES_RATE_LIMIT)
        
        batch_results['end_time'] = datetime.now(timezone.utc).isoformat()
        
        logger.info(
            f"Batch send completed: {batch_results['successful']} successful, "
            f"{batch_results['failed']} failed, {batch_results['skipped']} skipped"
        )
        
        return batch_results
    
    def send_to_all_batches(self, weekly_summary: WeeklySummary, 
                           subscriber_batches: List[List[Subscriber]]) -> Dict[str, Any]:
        """
        Send newsletter to all subscriber batches.
        
        Args:
            weekly_summary: Weekly summary content
            subscriber_batches: List of subscriber batches
            
        Returns:
            Dict with overall send results
        """
        overall_results = {
            'total_batches': len(subscriber_batches),
            'total_subscribers': sum(len(batch) for batch in subscriber_batches),
            'successful': 0,
            'failed': 0,
            'skipped': 0,
            'batch_results': [],
            'start_time': datetime.now(timezone.utc).isoformat()
        }
        
        for batch_num, batch in enumerate(subscriber_batches, 1):
            logger.info(f"Processing batch {batch_num}/{len(subscriber_batches)} ({len(batch)} subscribers)")
            
            # Check if we've hit daily limit
            if self.emails_sent_today >= self.SES_DAILY_LIMIT:
                logger.warning("Daily sending limit reached. Stopping batch processing.")
                remaining_subscribers = sum(len(b) for b in subscriber_batches[batch_num-1:])
                overall_results['skipped'] += remaining_subscribers
                break
            
            # Send batch
            batch_result = self.send_batch(weekly_summary, batch)
            overall_results['batch_results'].append({
                'batch_number': batch_num,
                'result': batch_result
            })
            
            overall_results['successful'] += batch_result['successful']
            overall_results['failed'] += batch_result['failed']
            overall_results['skipped'] += batch_result['skipped']
            
            # Add delay between batches
            if batch_num < len(subscriber_batches):
                time.sleep(2)  # 2 second delay between batches
        
        overall_results['end_time'] = datetime.now(timezone.utc).isoformat()
        overall_results['emails_sent_today'] = self.emails_sent_today
        
        logger.info(
            f"All batches completed: {overall_results['successful']} successful, "
            f"{overall_results['failed']} failed, {overall_results['skipped']} skipped"
        )
        
        return overall_results
    
    def get_send_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about email sending.
        
        Returns:
            Dict with send statistics
        """
        return {
            'emails_sent_today': self.emails_sent_today,
            'daily_limit': self.SES_DAILY_LIMIT,
            'remaining_quota': self.SES_DAILY_LIMIT - self.emails_sent_today,
            'total_errors': len(self.send_errors),
            'recent_errors': self.send_errors[-10:] if self.send_errors else [],
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    def handle_bounce_notification(self, bounce_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle SES bounce notification.
        
        Args:
            bounce_data: Bounce notification data from SES
            
        Returns:
            Dict with handling result
        """
        result = {
            'handled': False,
            'bounce_type': None,
            'affected_emails': [],
            'action_taken': None
        }
        
        try:
            bounce_type = bounce_data.get('bounce', {}).get('bounceType')
            bounced_recipients = bounce_data.get('bounce', {}).get('bouncedRecipients', [])
            
            result['bounce_type'] = bounce_type
            result['affected_emails'] = [r.get('emailAddress') for r in bounced_recipients]
            
            # Handle hard bounces (permanent failures)
            if bounce_type == 'Permanent':
                logger.warning(f"Permanent bounce detected for: {result['affected_emails']}")
                result['action_taken'] = 'should_unsubscribe'
                # Note: Actual unsubscribe should be handled by calling code with DynamoDB access
            
            # Handle soft bounces (temporary failures)
            elif bounce_type == 'Transient':
                logger.info(f"Transient bounce detected for: {result['affected_emails']}")
                result['action_taken'] = 'retry_later'
            
            result['handled'] = True
            
        except Exception as e:
            logger.error(f"Failed to handle bounce notification: {str(e)}")
            result['error'] = str(e)
        
        return result
    
    def handle_complaint_notification(self, complaint_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle SES complaint notification.
        
        Args:
            complaint_data: Complaint notification data from SES
            
        Returns:
            Dict with handling result
        """
        result = {
            'handled': False,
            'complaint_type': None,
            'affected_emails': [],
            'action_taken': None
        }
        
        try:
            complaint_type = complaint_data.get('complaint', {}).get('complaintFeedbackType')
            complained_recipients = complaint_data.get('complaint', {}).get('complainedRecipients', [])
            
            result['complaint_type'] = complaint_type
            result['affected_emails'] = [r.get('emailAddress') for r in complained_recipients]
            
            # All complaints should result in unsubscribe
            logger.warning(f"Complaint received from: {result['affected_emails']}")
            result['action_taken'] = 'should_unsubscribe'
            # Note: Actual unsubscribe should be handled by calling code with DynamoDB access
            
            result['handled'] = True
            
        except Exception as e:
            logger.error(f"Failed to handle complaint notification: {str(e)}")
            result['error'] = str(e)
        
        return result
