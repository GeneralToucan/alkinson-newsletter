"""
Configuration settings for Alkinson Newsletter
"""

import os
from typing import Dict, Any

class Config:
    """Configuration class for the newsletter system"""
    
    # AWS Configuration
    AWS_REGION = os.getenv('AWS_REGION', 'ap-southeast-2')
    
    # S3 Configuration
    CONTENT_BUCKET = os.getenv('CONTENT_BUCKET', 'alkinson-newsletter-content')
    
    # DynamoDB Configuration
    SUBSCRIBERS_TABLE = os.getenv('SUBSCRIBERS_TABLE', 'alkinson-newsletter-subscribers')
    
    # SES Configuration
    SES_SENDER_EMAIL = os.getenv('SES_SENDER_EMAIL', 'newsletter@example.com')
    SES_DAILY_LIMIT = int(os.getenv('SES_DAILY_LIMIT', '200'))
    
    # NewsAPI Configuration
    NEWSAPI_KEY = os.getenv('NEWSAPI_KEY', '')
    NEWSAPI_BASE_URL = 'https://newsapi.org/v2'
    
    # Bedrock Configuration
    BEDROCK_MODEL_ID = os.getenv('BEDROCK_MODEL_ID', 'anthropic.claude-3-haiku-20240307-v1:0')
    BEDROCK_REGION = os.getenv('BEDROCK_REGION', 'ap-southeast-2')
    
    # Content Sources
    RSS_FEEDS = [
        'https://www.alzheimers.org.uk/news/rss.xml',
        'https://www.parkinson.org/news/rss',
        'https://feeds.feedburner.com/alzheimers-research-uk',
        'https://www.michaeljfox.org/news/rss'
    ]
    
    # Content Keywords for filtering
    ALZHEIMERS_KEYWORDS = [
        'alzheimer', 'alzheimers', 'dementia', 'cognitive decline',
        'memory loss', 'beta amyloid', 'tau protein', 'neurodegeneration'
    ]
    
    PARKINSONS_KEYWORDS = [
        'parkinson', 'parkinsons', 'dopamine', 'motor symptoms',
        'tremor', 'bradykinesia', 'rigidity', 'lewy body'
    ]
    
    # Website Configuration
    WEBSITE_URL = os.getenv('WEBSITE_URL', 'https://alkinson-newsletter-content.s3-website-ap-southeast-2.amazonaws.com')
    
    # Email Template Configuration
    EMAIL_TEMPLATE_PATH = 'templates/email-template.html'
    UNSUBSCRIBE_URL_TEMPLATE = f"{WEBSITE_URL}/unsubscribe?email={{email}}&token={{token}}"
    
    @classmethod
    def get_env_vars(cls) -> Dict[str, Any]:
        """Get all configuration as environment variables dictionary"""
        return {
            'AWS_REGION': cls.AWS_REGION,
            'CONTENT_BUCKET': cls.CONTENT_BUCKET,
            'SUBSCRIBERS_TABLE': cls.SUBSCRIBERS_TABLE,
            'SES_SENDER_EMAIL': cls.SES_SENDER_EMAIL,
            'SES_DAILY_LIMIT': str(cls.SES_DAILY_LIMIT),
            'NEWSAPI_KEY': cls.NEWSAPI_KEY,
            'BEDROCK_MODEL_ID': cls.BEDROCK_MODEL_ID,
            'BEDROCK_REGION': cls.BEDROCK_REGION,
            'WEBSITE_URL': cls.WEBSITE_URL
        }
    
    @classmethod
    def validate_config(cls) -> bool:
        """Validate that required configuration is present"""
        required_vars = [
            'NEWSAPI_KEY',
            'SES_SENDER_EMAIL'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not getattr(cls, var):
                missing_vars.append(var)
        
        if missing_vars:
            print(f"Missing required configuration: {', '.join(missing_vars)}")
            return False
        
        return True