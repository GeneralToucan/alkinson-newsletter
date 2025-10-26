"""
Data models for Alkinson's Newsletter system.

This module defines Pydantic models for newsletter content, subscribers,
and related data structures used across the Lambda functions.
"""

from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, EmailStr, Field, validator
import json
from enum import Enum


class SubscriberStatus(str, Enum):
    """Enumeration for subscriber status values."""
    ACTIVE = "active"
    UNSUBSCRIBED = "unsubscribed"
    PENDING_CONFIRMATION = "pending_confirmation"


class Article(BaseModel):
    """Model for individual article data."""
    title: str = Field(..., description="Article title")
    source: str = Field(..., description="Source publication name")
    url: str = Field(..., description="Article URL")
    summary: str = Field(..., description="AI-generated summary")
    published_date: datetime = Field(..., description="Article publication date")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class DiseaseSection(BaseModel):
    """Model for disease-specific content section."""
    summary: str = Field(..., description="Overall summary for the disease section")
    articles: List[Article] = Field(default_factory=list, description="List of articles for this disease")
    
    @validator('articles')
    def validate_articles(cls, v):
        """Ensure articles list is not None."""
        return v or []


class WeeklySummary(BaseModel):
    """Model for complete weekly newsletter summary."""
    week_id: str = Field(..., description="Week identifier (e.g., '2024-week-01')")
    generated_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    alzheimers: DiseaseSection = Field(default_factory=DiseaseSection)
    parkinsons: DiseaseSection = Field(default_factory=DiseaseSection)
    total_articles_processed: int = Field(default=0, description="Total number of articles processed")
    processing_time_seconds: Optional[float] = Field(None, description="Time taken to process content")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    def to_json(self) -> str:
        """Convert model to JSON string."""
        return self.json(indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'WeeklySummary':
        """Create model instance from JSON string."""
        return cls.parse_raw(json_str)


class Subscriber(BaseModel):
    """Model for newsletter subscriber data."""
    email: EmailStr = Field(..., description="Subscriber email address")
    subscribed_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: SubscriberStatus = Field(default=SubscriberStatus.PENDING_CONFIRMATION)
    confirmation_token: Optional[str] = Field(None, description="Email confirmation token")
    unsubscribe_token: Optional[str] = Field(None, description="Unsubscribe token")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    def to_dynamodb_item(self) -> Dict[str, Any]:
        """Convert model to DynamoDB item format."""
        return {
            'email': str(self.email),
            'subscribed_date': self.subscribed_date.isoformat(),
            'status': self.status.value,
            'confirmation_token': self.confirmation_token,
            'unsubscribe_token': self.unsubscribe_token
        }
    
    @classmethod
    def from_dynamodb_item(cls, item: Dict[str, Any]) -> 'Subscriber':
        """Create model instance from DynamoDB item."""
        return cls(
            email=item['email'],
            subscribed_date=datetime.fromisoformat(item['subscribed_date']),
            status=SubscriberStatus(item['status']),
            confirmation_token=item.get('confirmation_token'),
            unsubscribe_token=item.get('unsubscribe_token')
        )


class EmailTemplate(BaseModel):
    """Model for email template data."""
    subject: str = Field(..., description="Email subject line")
    html_content: str = Field(..., description="HTML email content")
    text_content: Optional[str] = Field(None, description="Plain text email content")
    unsubscribe_url: str = Field(..., description="Unsubscribe URL for this email")


class ProcessingResult(BaseModel):
    """Model for content processing results."""
    success: bool = Field(..., description="Whether processing was successful")
    weekly_summary: Optional[WeeklySummary] = Field(None, description="Generated weekly summary")
    error_message: Optional[str] = Field(None, description="Error message if processing failed")
    articles_found: int = Field(default=0, description="Number of articles found")
    articles_processed: int = Field(default=0, description="Number of articles successfully processed")
    processing_time_seconds: float = Field(default=0.0, description="Total processing time")