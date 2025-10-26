"""
Content Processor Module
Handles weekly summary generation, HTML generation, and S3 storage
"""

import json
import boto3
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from bedrock_summarizer import SummarizedContent

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class ContentProcessor:
    """Processes summarized content and stores in S3"""
    
    def __init__(self, content_bucket: str, region: str = "us-east-1"):
        """
        Initialize the content processor
        
        Args:
            content_bucket: S3 bucket name for content storage
            region: AWS region
        """
        self.content_bucket = content_bucket
        self.region = region
        
        try:
            self.s3_client = boto3.client('s3', region_name=region)
            logger.info(f"Initialized S3 client for bucket: {content_bucket}")
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {str(e)}")
            raise
    
    def generate_week_id(self, date: Optional[datetime] = None) -> str:
        """
        Generate week ID in format YYYY-week-WW
        
        Args:
            date: Date to generate week ID for (defaults to current date)
            
        Returns:
            Week ID string
        """
        if date is None:
            date = datetime.now(timezone.utc)
        
        # Get ISO week number
        year, week_num, _ = date.isocalendar()
        return f"{year}-week-{week_num:02d}"
    
    def generate_weekly_summary(
        self,
        alzheimers_summary: SummarizedContent,
        parkinsons_summary: SummarizedContent,
        processing_time_seconds: float,
        week_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate weekly summary JSON structure
        
        Args:
            alzheimers_summary: Summarized Alzheimer's content
            parkinsons_summary: Summarized Parkinson's content
            processing_time_seconds: Time taken to process content
            week_id: Optional week ID (generated if not provided)
            
        Returns:
            Weekly summary dictionary
        """
        if week_id is None:
            week_id = self.generate_week_id()
        
        generated_date = datetime.now(timezone.utc).isoformat()
        
        weekly_summary = {
            "week_id": week_id,
            "generated_date": generated_date,
            "alzheimers": {
                "summary": alzheimers_summary.overall_summary,
                "articles": alzheimers_summary.article_summaries
            },
            "parkinsons": {
                "summary": parkinsons_summary.overall_summary,
                "articles": parkinsons_summary.article_summaries
            },
            "total_articles_processed": (
                alzheimers_summary.total_articles + 
                parkinsons_summary.total_articles
            ),
            "processing_time_seconds": round(processing_time_seconds, 2)
        }
        
        logger.info(f"Generated weekly summary for {week_id}")
        logger.info(f"Total articles: {weekly_summary['total_articles_processed']}")
        
        return weekly_summary

    def generate_html_content(
        self,
        weekly_summary: Dict[str, Any],
        template_type: str = "website"
    ) -> str:
        """
        Generate HTML content from weekly summary
        
        Args:
            weekly_summary: Weekly summary dictionary
            template_type: Type of template ('website' or 'email')
            
        Returns:
            HTML content string
        """
        week_id = weekly_summary['week_id']
        generated_date = datetime.fromisoformat(weekly_summary['generated_date'])
        week_date = generated_date.strftime('%B %d, %Y')
        
        # Generate Alzheimer's articles HTML
        alzheimers_articles_html = self._generate_articles_html(
            weekly_summary['alzheimers']['articles']
        )
        
        # Generate Parkinson's articles HTML
        parkinsons_articles_html = self._generate_articles_html(
            weekly_summary['parkinsons']['articles']
        )
        
        # Create HTML based on template type
        if template_type == "website":
            html = self._generate_website_html(
                week_id=week_id,
                week_date=week_date,
                alzheimers_summary=weekly_summary['alzheimers']['summary'],
                alzheimers_articles=alzheimers_articles_html,
                parkinsons_summary=weekly_summary['parkinsons']['summary'],
                parkinsons_articles=parkinsons_articles_html
            )
        else:
            # Email template will be handled by Email Agent
            html = self._generate_simple_html(
                week_id=week_id,
                week_date=week_date,
                alzheimers_summary=weekly_summary['alzheimers']['summary'],
                alzheimers_articles=alzheimers_articles_html,
                parkinsons_summary=weekly_summary['parkinsons']['summary'],
                parkinsons_articles=parkinsons_articles_html
            )
        
        logger.info(f"Generated {template_type} HTML for {week_id}")
        return html
    
    def _generate_articles_html(self, articles: list) -> str:
        """
        Generate HTML for a list of articles
        
        Args:
            articles: List of article dictionaries
            
        Returns:
            HTML string for articles
        """
        if not articles:
            return '<p class="no-articles">No new articles this week.</p>'
        
        articles_html = []
        for article in articles:
            article_html = f'''
            <div class="article">
                <h4><a href="{article['url']}" target="_blank">{article['title']}</a></h4>
                <p class="source">{article['source']} - {self._format_date(article['published_date'])}</p>
                <p class="summary">{article['summary']}</p>
            </div>
            '''
            articles_html.append(article_html)
        
        return '\n'.join(articles_html)
    
    def _format_date(self, date_str: str) -> str:
        """
        Format ISO date string to readable format
        
        Args:
            date_str: ISO format date string
            
        Returns:
            Formatted date string
        """
        try:
            date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return date.strftime('%B %d, %Y')
        except:
            return date_str
    
    def _generate_website_html(
        self,
        week_id: str,
        week_date: str,
        alzheimers_summary: str,
        alzheimers_articles: str,
        parkinsons_summary: str,
        parkinsons_articles: str
    ) -> str:
        """Generate complete website HTML"""
        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Alkinson's Newsletter - {week_id}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f7fa;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-align: center;
            padding: 40px 20px;
            border-radius: 12px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        .header p {{
            font-size: 1.2em;
            opacity: 0.9;
        }}
        .content {{
            background: white;
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }}
        .disease-section {{
            margin-bottom: 40px;
        }}
        .disease-section:last-child {{
            margin-bottom: 0;
        }}
        .disease-section h2 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
            margin-bottom: 20px;
            font-size: 1.8em;
        }}
        .overall-summary {{
            background: #e8f4f8;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 25px;
            border-left: 4px solid #3498db;
        }}
        .overall-summary p {{
            font-size: 1.1em;
            line-height: 1.7;
        }}
        .article {{
            margin-bottom: 25px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
            border-left: 4px solid #95a5a6;
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        .article:hover {{
            transform: translateX(5px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }}
        .article h4 {{
            margin-bottom: 8px;
            font-size: 1.3em;
        }}
        .article h4 a {{
            color: #2c3e50;
            text-decoration: none;
        }}
        .article h4 a:hover {{
            color: #3498db;
        }}
        .article .source {{
            font-size: 0.9em;
            color: #7f8c8d;
            margin-bottom: 12px;
        }}
        .article .summary {{
            color: #555;
            line-height: 1.7;
        }}
        .no-articles {{
            color: #7f8c8d;
            font-style: italic;
            padding: 20px;
            text-align: center;
        }}
        .footer {{
            background: white;
            padding: 30px;
            text-align: center;
            border-radius: 12px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .footer p {{
            color: #7f8c8d;
            margin-bottom: 10px;
        }}
        .footer a {{
            color: #3498db;
            text-decoration: none;
            margin: 0 10px;
        }}
        .footer a:hover {{
            text-decoration: underline;
        }}
        @media (max-width: 768px) {{
            .container {{
                padding: 10px;
            }}
            .header h1 {{
                font-size: 2em;
            }}
            .content {{
                padding: 20px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Alkinson's Newsletter</h1>
            <p>Week of {week_date}</p>
        </div>
        
        <div class="content">
            <div class="disease-section">
                <h2>Alzheimer's Disease Updates</h2>
                <div class="overall-summary">
                    <p>{alzheimers_summary}</p>
                </div>
                {alzheimers_articles}
            </div>
            
            <div class="disease-section">
                <h2>Parkinson's Disease Updates</h2>
                <div class="overall-summary">
                    <p>{parkinsons_summary}</p>
                </div>
                {parkinsons_articles}
            </div>
        </div>
        
        <div class="footer">
            <p>Alkinson's Newsletter - AI-powered weekly summaries of Alzheimer's and Parkinson's disease research</p>
            <p>
                <a href="/">Home</a> |
                <a href="/archive.html">Archive</a> |
                <a href="#subscribe">Subscribe</a>
            </p>
        </div>
    </div>
</body>
</html>'''
    
    def _generate_simple_html(
        self,
        week_id: str,
        week_date: str,
        alzheimers_summary: str,
        alzheimers_articles: str,
        parkinsons_summary: str,
        parkinsons_articles: str
    ) -> str:
        """Generate simple HTML for email or basic display"""
        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Alkinson's Newsletter - {week_id}</title>
</head>
<body>
    <h1>Alkinson's Newsletter</h1>
    <p>Week of {week_date}</p>
    
    <h2>Alzheimer's Disease Updates</h2>
    <p>{alzheimers_summary}</p>
    {alzheimers_articles}
    
    <h2>Parkinson's Disease Updates</h2>
    <p>{parkinsons_summary}</p>
    {parkinsons_articles}
</body>
</html>'''

    def store_in_s3(
        self,
        weekly_summary: Dict[str, Any],
        html_content: str
    ) -> Dict[str, str]:
        """
        Store weekly summary JSON and HTML in S3
        
        Args:
            weekly_summary: Weekly summary dictionary
            html_content: Generated HTML content
            
        Returns:
            Dictionary with S3 keys for stored objects
        """
        week_id = weekly_summary['week_id']
        
        # Define S3 keys with proper naming conventions
        json_key = f"data/archive/{week_id}.json"
        html_key = f"website/archive/{week_id}.html"
        current_json_key = "data/current-week.json"
        current_html_key = "website/index.html"
        
        stored_keys = {}
        
        try:
            # Store JSON archive
            logger.info(f"Storing JSON to s3://{self.content_bucket}/{json_key}")
            self.s3_client.put_object(
                Bucket=self.content_bucket,
                Key=json_key,
                Body=json.dumps(weekly_summary, indent=2),
                ContentType='application/json',
                CacheControl='public, max-age=3600'
            )
            stored_keys['json_archive'] = json_key
            
            # Store HTML archive
            logger.info(f"Storing HTML to s3://{self.content_bucket}/{html_key}")
            self.s3_client.put_object(
                Bucket=self.content_bucket,
                Key=html_key,
                Body=html_content,
                ContentType='text/html',
                CacheControl='public, max-age=3600'
            )
            stored_keys['html_archive'] = html_key
            
            # Update current week JSON
            logger.info(f"Updating current week JSON: s3://{self.content_bucket}/{current_json_key}")
            self.s3_client.put_object(
                Bucket=self.content_bucket,
                Key=current_json_key,
                Body=json.dumps(weekly_summary, indent=2),
                ContentType='application/json',
                CacheControl='public, max-age=300'  # 5 minutes cache
            )
            stored_keys['current_json'] = current_json_key
            
            # Update current website homepage
            logger.info(f"Updating website homepage: s3://{self.content_bucket}/{current_html_key}")
            self.s3_client.put_object(
                Bucket=self.content_bucket,
                Key=current_html_key,
                Body=html_content,
                ContentType='text/html',
                CacheControl='public, max-age=300'  # 5 minutes cache
            )
            stored_keys['current_html'] = current_html_key
            
            logger.info(f"Successfully stored all content for {week_id}")
            return stored_keys
            
        except Exception as e:
            logger.error(f"Error storing content in S3: {str(e)}")
            raise
    
    def process_and_store(
        self,
        alzheimers_summary: SummarizedContent,
        parkinsons_summary: SummarizedContent,
        processing_time_seconds: float
    ) -> Dict[str, Any]:
        """
        Complete pipeline: generate summary, create HTML, and store in S3
        
        Args:
            alzheimers_summary: Summarized Alzheimer's content
            parkinsons_summary: Summarized Parkinson's content
            processing_time_seconds: Time taken to process content
            
        Returns:
            Dictionary with processing results and S3 keys
        """
        logger.info("Starting content processing and storage pipeline")
        
        # Generate weekly summary JSON
        weekly_summary = self.generate_weekly_summary(
            alzheimers_summary=alzheimers_summary,
            parkinsons_summary=parkinsons_summary,
            processing_time_seconds=processing_time_seconds
        )
        
        # Generate HTML content
        html_content = self.generate_html_content(
            weekly_summary=weekly_summary,
            template_type="website"
        )
        
        # Store in S3
        stored_keys = self.store_in_s3(
            weekly_summary=weekly_summary,
            html_content=html_content
        )
        
        result = {
            'week_id': weekly_summary['week_id'],
            'generated_date': weekly_summary['generated_date'],
            'total_articles': weekly_summary['total_articles_processed'],
            's3_keys': stored_keys,
            'success': True
        }
        
        logger.info("Content processing and storage pipeline completed successfully")
        return result
