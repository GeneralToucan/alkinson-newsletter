"""
Email template system and formatting for Email Agent.

This module handles email template rendering, content formatting,
and unsubscribe link generation for newsletter emails.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from jinja2 import Template, Environment, BaseLoader

from shared.models import WeeklySummary, Subscriber, Article
from shared.utils import format_date_for_display, format_week_display

logger = logging.getLogger(__name__)


class EmailFormatter:
    """Handles email template rendering and formatting."""
    
    # Responsive HTML email template
    EMAIL_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Alkinson's Newsletter - {{ week_display }}</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background-color: #ffffff;
            border-radius: 8px;
            padding: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .header {
            text-align: center;
            border-bottom: 3px solid #4A90E2;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }
        .header h1 {
            color: #2C3E50;
            margin: 0 0 10px 0;
            font-size: 28px;
        }
        .header .week-info {
            color: #7F8C8D;
            font-size: 14px;
        }
        .section {
            margin-bottom: 40px;
        }
        .section-title {
            color: #2C3E50;
            font-size: 22px;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #ECF0F1;
        }
        .section-summary {
            background-color: #F8F9FA;
            padding: 15px;
            border-left: 4px solid #4A90E2;
            margin-bottom: 20px;
            font-style: italic;
            color: #555;
        }
        .article {
            margin-bottom: 25px;
            padding-bottom: 20px;
            border-bottom: 1px solid #ECF0F1;
        }
        .article:last-child {
            border-bottom: none;
        }
        .article-title {
            font-size: 18px;
            font-weight: 600;
            color: #2C3E50;
            margin-bottom: 8px;
        }
        .article-title a {
            color: #4A90E2;
            text-decoration: none;
        }
        .article-title a:hover {
            text-decoration: underline;
        }
        .article-meta {
            font-size: 13px;
            color: #7F8C8D;
            margin-bottom: 10px;
        }
        .article-summary {
            color: #555;
            font-size: 15px;
            line-height: 1.6;
        }
        .footer {
            margin-top: 40px;
            padding-top: 20px;
            border-top: 2px solid #ECF0F1;
            text-align: center;
            font-size: 13px;
            color: #7F8C8D;
        }
        .footer a {
            color: #4A90E2;
            text-decoration: none;
        }
        .footer a:hover {
            text-decoration: underline;
        }
        .unsubscribe {
            margin-top: 15px;
            font-size: 12px;
        }
        @media only screen and (max-width: 600px) {
            body {
                padding: 10px;
            }
            .container {
                padding: 20px;
            }
            .header h1 {
                font-size: 24px;
            }
            .section-title {
                font-size: 20px;
            }
            .article-title {
                font-size: 16px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧠 Alkinson's Newsletter</h1>
            <div class="week-info">{{ week_display }}</div>
            <div class="week-info">{{ generated_date }}</div>
        </div>
        
        {% if alzheimers_articles %}
        <div class="section">
            <h2 class="section-title">🔬 Alzheimer's Disease Updates</h2>
            {% if alzheimers_summary %}
            <div class="section-summary">
                {{ alzheimers_summary }}
            </div>
            {% endif %}
            {% for article in alzheimers_articles %}
            <div class="article">
                <div class="article-title">
                    <a href="{{ article.url }}" target="_blank">{{ article.title }}</a>
                </div>
                <div class="article-meta">
                    📰 {{ article.source }} • 📅 {{ article.published_date }}
                </div>
                <div class="article-summary">
                    {{ article.summary }}
                </div>
            </div>
            {% endfor %}
        </div>
        {% endif %}
        
        {% if parkinsons_articles %}
        <div class="section">
            <h2 class="section-title">🧬 Parkinson's Disease Updates</h2>
            {% if parkinsons_summary %}
            <div class="section-summary">
                {{ parkinsons_summary }}
            </div>
            {% endif %}
            {% for article in parkinsons_articles %}
            <div class="article">
                <div class="article-title">
                    <a href="{{ article.url }}" target="_blank">{{ article.title }}</a>
                </div>
                <div class="article-meta">
                    📰 {{ article.source }} • 📅 {{ article.published_date }}
                </div>
                <div class="article-summary">
                    {{ article.summary }}
                </div>
            </div>
            {% endfor %}
        </div>
        {% endif %}
        
        <div class="footer">
            <p>Thank you for reading Alkinson's Newsletter!</p>
            <p>Stay informed about the latest developments in Alzheimer's and Parkinson's disease research.</p>
            <div class="unsubscribe">
                <a href="{{ unsubscribe_url }}">Unsubscribe from this newsletter</a>
            </div>
        </div>
    </div>
</body>
</html>
"""
    
    # Plain text template for email clients that don't support HTML
    TEXT_TEMPLATE = """
ALKINSON'S NEWSLETTER
{{ week_display }}
{{ generated_date }}

================================================================================

{% if alzheimers_articles %}
ALZHEIMER'S DISEASE UPDATES
{% if alzheimers_summary %}
{{ alzheimers_summary }}
{% endif %}

{% for article in alzheimers_articles %}
{{ loop.index }}. {{ article.title }}
   Source: {{ article.source }} | Date: {{ article.published_date }}
   {{ article.url }}
   
   {{ article.summary }}

{% endfor %}
{% endif %}

{% if parkinsons_articles %}
PARKINSON'S DISEASE UPDATES
{% if parkinsons_summary %}
{{ parkinsons_summary }}
{% endif %}

{% for article in parkinsons_articles %}
{{ loop.index }}. {{ article.title }}
   Source: {{ article.source }} | Date: {{ article.published_date }}
   {{ article.url }}
   
   {{ article.summary }}

{% endfor %}
{% endif %}

================================================================================

Thank you for reading Alkinson's Newsletter!
Stay informed about the latest developments in Alzheimer's and Parkinson's disease research.

To unsubscribe: {{ unsubscribe_url }}
"""
    
    def __init__(self, base_url: str = "https://your-domain.com"):
        """
        Initialize email formatter.
        
        Args:
            base_url: Base URL for unsubscribe links
        """
        self.base_url = base_url.rstrip('/')
        self.jinja_env = Environment(loader=BaseLoader())
        logger.info(f"EmailFormatter initialized with base_url: {base_url}")
    
    def generate_unsubscribe_url(self, subscriber: Subscriber) -> str:
        """
        Generate secure unsubscribe URL for a subscriber.
        
        Args:
            subscriber: Subscriber model with unsubscribe token
            
        Returns:
            str: Complete unsubscribe URL
        """
        if not subscriber.unsubscribe_token:
            logger.error(f"Subscriber {subscriber.email} missing unsubscribe token")
            raise ValueError("Subscriber missing unsubscribe token")
        
        url = f"{self.base_url}/unsubscribe?token={subscriber.unsubscribe_token}&email={subscriber.email}"
        return url
    
    def format_article_for_template(self, article: Article) -> Dict[str, str]:
        """
        Format article data for template rendering.
        
        Args:
            article: Article model
            
        Returns:
            Dict with formatted article data
        """
        return {
            'title': article.title,
            'source': article.source,
            'url': article.url,
            'summary': article.summary,
            'published_date': format_date_for_display(article.published_date)
        }
    
    def prepare_template_context(self, weekly_summary: WeeklySummary, subscriber: Subscriber) -> Dict[str, Any]:
        """
        Prepare context data for template rendering.
        
        Args:
            weekly_summary: Weekly summary content
            subscriber: Subscriber receiving the email
            
        Returns:
            Dict with template context data
        """
        # Format articles
        alzheimers_articles = [
            self.format_article_for_template(article)
            for article in weekly_summary.alzheimers.articles
        ]
        
        parkinsons_articles = [
            self.format_article_for_template(article)
            for article in weekly_summary.parkinsons.articles
        ]
        
        # Generate unsubscribe URL
        unsubscribe_url = self.generate_unsubscribe_url(subscriber)
        
        context = {
            'week_display': format_week_display(weekly_summary.week_id),
            'generated_date': format_date_for_display(weekly_summary.generated_date),
            'alzheimers_summary': weekly_summary.alzheimers.summary,
            'alzheimers_articles': alzheimers_articles,
            'parkinsons_summary': weekly_summary.parkinsons.summary,
            'parkinsons_articles': parkinsons_articles,
            'unsubscribe_url': unsubscribe_url,
            'total_articles': weekly_summary.total_articles_processed
        }
        
        return context
    
    def render_html_email(self, weekly_summary: WeeklySummary, subscriber: Subscriber) -> str:
        """
        Render HTML email content.
        
        Args:
            weekly_summary: Weekly summary content
            subscriber: Subscriber receiving the email
            
        Returns:
            str: Rendered HTML email content
        """
        try:
            context = self.prepare_template_context(weekly_summary, subscriber)
            template = self.jinja_env.from_string(self.EMAIL_TEMPLATE)
            html_content = template.render(**context)
            
            logger.info(f"Rendered HTML email for {subscriber.email}")
            return html_content
            
        except Exception as e:
            logger.error(f"Failed to render HTML email: {str(e)}")
            raise
    
    def render_text_email(self, weekly_summary: WeeklySummary, subscriber: Subscriber) -> str:
        """
        Render plain text email content.
        
        Args:
            weekly_summary: Weekly summary content
            subscriber: Subscriber receiving the email
            
        Returns:
            str: Rendered plain text email content
        """
        try:
            context = self.prepare_template_context(weekly_summary, subscriber)
            template = self.jinja_env.from_string(self.TEXT_TEMPLATE)
            text_content = template.render(**context)
            
            logger.info(f"Rendered text email for {subscriber.email}")
            return text_content
            
        except Exception as e:
            logger.error(f"Failed to render text email: {str(e)}")
            raise
    
    def generate_email_subject(self, weekly_summary: WeeklySummary) -> str:
        """
        Generate email subject line.
        
        Args:
            weekly_summary: Weekly summary content
            
        Returns:
            str: Email subject line
        """
        week_display = format_week_display(weekly_summary.week_id)
        subject = f"🧠 Alkinson's Newsletter - {week_display}"
        return subject
    
    def format_email(self, weekly_summary: WeeklySummary, subscriber: Subscriber) -> Dict[str, str]:
        """
        Format complete email with subject, HTML, and text content.
        
        Args:
            weekly_summary: Weekly summary content
            subscriber: Subscriber receiving the email
            
        Returns:
            Dict with 'subject', 'html_body', and 'text_body'
        """
        try:
            subject = self.generate_email_subject(weekly_summary)
            html_body = self.render_html_email(weekly_summary, subscriber)
            text_body = self.render_text_email(weekly_summary, subscriber)
            
            return {
                'subject': subject,
                'html_body': html_body,
                'text_body': text_body
            }
            
        except Exception as e:
            logger.error(f"Failed to format email for {subscriber.email}: {str(e)}")
            raise
