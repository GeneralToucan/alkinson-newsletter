import json
import os
import boto3
import time
from datetime import datetime, timezone
import logging
from content_gatherer import ContentGatherer
from bedrock_summarizer import BedrockSummarizer
from content_processor import ContentProcessor

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """
    Content Agent Lambda Function
    Gathers content from RSS feeds and NewsAPI, processes with Bedrock,
    and stores weekly summaries in S3.
    """
    
    logger.info("Content Agent started")
    
    # Environment variables
    content_bucket = os.environ.get('CONTENT_BUCKET')
    subscribers_table = os.environ.get('SUBSCRIBERS_TABLE')
    newsapi_key = os.environ.get('NEWSAPI_KEY', '')
    
    # RSS feeds configuration
    rss_feeds = [
        'https://www.alzheimers.org.uk/news/rss.xml',
        'https://www.parkinson.org/news/rss',
        'https://feeds.feedburner.com/alzheimers-research-uk',
        'https://www.michaeljfox.org/news/rss'
    ]
    
    # Keywords for filtering
    alzheimers_keywords = [
        'alzheimer', 'alzheimers', 'dementia', 'cognitive decline',
        'memory loss', 'beta amyloid', 'tau protein', 'neurodegeneration'
    ]
    
    parkinsons_keywords = [
        "parkinson's disease", "parkinson's", 'parkinsons disease',
        'dopamine', 'motor symptoms', 'tremor', 'bradykinesia', 
        'rigidity', 'lewy body', 'substantia nigra'
    ]
    
    try:
        # Initialize content gatherer
        gatherer = ContentGatherer(
            newsapi_key=newsapi_key,
            rss_feeds=rss_feeds,
            alzheimers_keywords=alzheimers_keywords,
            parkinsons_keywords=parkinsons_keywords
        )
        
        # Gather content from all sources
        logger.info("Starting content gathering")
        articles = gatherer.gather_all_content(days_back=7)
        
        # Deduplicate articles
        articles = gatherer.deduplicate_articles(articles)
        
        logger.info(f"Total articles gathered: {len(articles)}")
        
        # Separate by category
        alzheimers_articles = [a for a in articles if a.category == 'alzheimers']
        parkinsons_articles = [a for a in articles if a.category == 'parkinsons']
        
        logger.info(f"Alzheimer's articles: {len(alzheimers_articles)}")
        logger.info(f"Parkinson's articles: {len(parkinsons_articles)}")
        
        # Initialize Bedrock summarizer
        bedrock_model_id = os.environ.get('BEDROCK_MODEL_ID', 'anthropic.claude-3-haiku-20240307-v1:0')
        bedrock_region = os.environ.get('BEDROCK_REGION', 'us-east-1')
        
        logger.info(f"Initializing Bedrock summarizer with model: {bedrock_model_id}")
        summarizer = BedrockSummarizer(
            model_id=bedrock_model_id,
            region=bedrock_region
        )
        
        # Estimate cost before processing
        total_articles = len(alzheimers_articles) + len(parkinsons_articles)
        cost_estimate = summarizer.estimate_cost(total_articles)
        logger.info(f"Estimated Bedrock cost: ${cost_estimate['total_cost_usd']:.4f}")
        logger.info(f"Estimated tokens - Input: {cost_estimate['input_tokens']}, Output: {cost_estimate['output_tokens']}")
        
        # COST SAFEGUARD: Warn if estimated cost is unusually high
        if cost_estimate['total_cost_usd'] > 0.10:
            logger.warning(
                f"⚠️  HIGH COST ALERT: Estimated cost ${cost_estimate['total_cost_usd']:.4f} "
                f"exceeds normal threshold of $0.10. Processing {total_articles} articles."
            )
        
        # COST SAFEGUARD: Hard limit to prevent runaway costs
        MAX_COST_THRESHOLD = 0.50  # $0.50 per execution
        if cost_estimate['total_cost_usd'] > MAX_COST_THRESHOLD:
            error_msg = (
                f"COST LIMIT EXCEEDED: Estimated cost ${cost_estimate['total_cost_usd']:.4f} "
                f"exceeds maximum threshold of ${MAX_COST_THRESHOLD}. "
                f"Aborting to prevent unexpected charges. "
                f"Articles: {total_articles}"
            )
            logger.error(error_msg)
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Cost limit exceeded',
                    'message': error_msg,
                    'estimated_cost_usd': cost_estimate['total_cost_usd'],
                    'max_threshold_usd': MAX_COST_THRESHOLD,
                    'articles_count': total_articles
                })
            }
        
        # Track processing time
        processing_start_time = time.time()
        
        # Summarize Alzheimer's articles
        logger.info("Summarizing Alzheimer's articles with Bedrock...")
        alzheimers_summary = summarizer.summarize_articles(alzheimers_articles, 'alzheimers')
        logger.info(f"Alzheimer's summary generated: {alzheimers_summary.total_articles} articles processed")
        
        # Summarize Parkinson's articles
        logger.info("Summarizing Parkinson's articles with Bedrock...")
        parkinsons_summary = summarizer.summarize_articles(parkinsons_articles, 'parkinsons')
        logger.info(f"Parkinson's summary generated: {parkinsons_summary.total_articles} articles processed")
        
        processing_time = time.time() - processing_start_time
        
        # Initialize content processor
        logger.info("Initializing content processor")
        processor = ContentProcessor(
            content_bucket=content_bucket,
            region=bedrock_region
        )
        
        # Process and store content in S3
        logger.info("Processing and storing content in S3")
        storage_result = processor.process_and_store(
            alzheimers_summary=alzheimers_summary,
            parkinsons_summary=parkinsons_summary,
            processing_time_seconds=processing_time
        )
        
        logger.info(f"Content stored successfully: {storage_result['week_id']}")
        logger.info(f"S3 keys: {storage_result['s3_keys']}")
        
        # TODO: Trigger email agent (Task 7.2)
        
        response = {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Content gathering, summarization, and storage completed successfully',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'week_id': storage_result['week_id'],
                'articles_gathered': len(articles),
                'alzheimers_articles': len(alzheimers_articles),
                'parkinsons_articles': len(parkinsons_articles),
                'alzheimers_summaries': alzheimers_summary.total_articles,
                'parkinsons_summaries': parkinsons_summary.total_articles,
                'total_articles_processed': storage_result['total_articles'],
                'estimated_cost_usd': cost_estimate['total_cost_usd'],
                'processing_time_seconds': processing_time,
                's3_keys': storage_result['s3_keys']
            })
        }
        
        logger.info("Content Agent completed successfully")
        return response
        
    except Exception as e:
        logger.error(f"Error in Content Agent: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
        }