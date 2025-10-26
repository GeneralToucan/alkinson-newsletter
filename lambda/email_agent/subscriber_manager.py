"""
Subscriber list management for Email Agent.

This module handles querying DynamoDB for active subscribers,
filtering, validation, and batch processing for large subscriber lists.
"""

import logging
from typing import List, Dict, Any
from datetime import datetime, timezone

from shared.models import Subscriber, SubscriberStatus
from shared.aws_clients import DynamoDBClient

logger = logging.getLogger(__name__)


class SubscriberManager:
    """Manages subscriber list retrieval and processing."""
    
    def __init__(self, dynamodb_client: DynamoDBClient):
        """
        Initialize subscriber manager.
        
        Args:
            dynamodb_client: DynamoDB client instance
        """
        self.dynamodb_client = dynamodb_client
        logger.info("SubscriberManager initialized")
    
    def get_active_subscribers(self) -> List[Subscriber]:
        """
        Retrieve all active subscribers from DynamoDB.
        
        Returns:
            List of active Subscriber models
        """
        try:
            subscribers = self.dynamodb_client.get_active_subscribers()
            logger.info(f"Retrieved {len(subscribers)} active subscribers")
            return subscribers
        except Exception as e:
            logger.error(f"Failed to retrieve active subscribers: {str(e)}")
            raise
    
    def filter_valid_subscribers(self, subscribers: List[Subscriber]) -> List[Subscriber]:
        """
        Filter subscribers to ensure they are valid for email sending.
        
        Args:
            subscribers: List of subscribers to filter
            
        Returns:
            List of valid subscribers
        """
        valid_subscribers = []
        
        for subscriber in subscribers:
            # Validate subscriber status
            if subscriber.status != SubscriberStatus.ACTIVE:
                logger.warning(f"Skipping non-active subscriber: {subscriber.email}")
                continue
            
            # Validate email format
            if not subscriber.email or '@' not in str(subscriber.email):
                logger.warning(f"Skipping invalid email format: {subscriber.email}")
                continue
            
            # Validate unsubscribe token exists
            if not subscriber.unsubscribe_token:
                logger.warning(f"Skipping subscriber without unsubscribe token: {subscriber.email}")
                continue
            
            valid_subscribers.append(subscriber)
        
        logger.info(f"Filtered to {len(valid_subscribers)} valid subscribers from {len(subscribers)} total")
        return valid_subscribers
    
    def batch_subscribers(self, subscribers: List[Subscriber], batch_size: int = 50) -> List[List[Subscriber]]:
        """
        Split subscribers into batches for processing.
        
        Args:
            subscribers: List of subscribers to batch
            batch_size: Number of subscribers per batch (default: 50)
            
        Returns:
            List of subscriber batches
        """
        batches = []
        
        for i in range(0, len(subscribers), batch_size):
            batch = subscribers[i:i + batch_size]
            batches.append(batch)
        
        logger.info(f"Created {len(batches)} batches from {len(subscribers)} subscribers (batch_size={batch_size})")
        return batches
    
    def get_subscribers_for_sending(self, batch_size: int = 50) -> List[List[Subscriber]]:
        """
        Get active, valid subscribers organized into batches for email sending.
        
        Args:
            batch_size: Number of subscribers per batch
            
        Returns:
            List of subscriber batches ready for email sending
        """
        try:
            # Get all active subscribers
            subscribers = self.get_active_subscribers()
            
            if not subscribers:
                logger.warning("No active subscribers found")
                return []
            
            # Filter for valid subscribers
            valid_subscribers = self.filter_valid_subscribers(subscribers)
            
            if not valid_subscribers:
                logger.warning("No valid subscribers after filtering")
                return []
            
            # Batch subscribers for processing
            batches = self.batch_subscribers(valid_subscribers, batch_size)
            
            return batches
            
        except Exception as e:
            logger.error(f"Failed to get subscribers for sending: {str(e)}")
            raise
    
    def get_subscriber_stats(self) -> Dict[str, Any]:
        """
        Get statistics about subscribers.
        
        Returns:
            Dict with subscriber statistics
        """
        try:
            subscribers = self.get_active_subscribers()
            valid_subscribers = self.filter_valid_subscribers(subscribers)
            
            return {
                'total_active': len(subscribers),
                'valid_for_sending': len(valid_subscribers),
                'invalid_count': len(subscribers) - len(valid_subscribers),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to get subscriber stats: {str(e)}")
            return {
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
