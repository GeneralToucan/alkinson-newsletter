"""
Content Gatherer Module
Handles RSS feed parsing and NewsAPI content gathering with filtering
"""

import feedparser
import requests
import time
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@dataclass
class Article:
    """Represents a gathered article"""
    title: str
    url: str
    source: str
    published_date: str
    description: str
    content: Optional[str] = None
    category: Optional[str] = None  # 'alzheimers' or 'parkinsons'


class ContentGatherer:
    """Gathers content from RSS feeds and NewsAPI"""
    
    def __init__(
        self,
        newsapi_key: str,
        rss_feeds: List[str],
        alzheimers_keywords: List[str],
        parkinsons_keywords: List[str]
    ):
        """
        Initialize the content gatherer
        
        Args:
            newsapi_key: API key for NewsAPI
            rss_feeds: List of RSS feed URLs
            alzheimers_keywords: Keywords for Alzheimer's content filtering
            parkinsons_keywords: Keywords for Parkinson's content filtering
        """
        self.newsapi_key = newsapi_key
        self.rss_feeds = rss_feeds
        self.alzheimers_keywords = [kw.lower() for kw in alzheimers_keywords]
        self.parkinsons_keywords = [kw.lower() for kw in parkinsons_keywords]
        self.newsapi_base_url = 'https://newsapi.org/v2'
        
        # Rate limiting configuration
        self.newsapi_requests_per_minute = 5
        self.newsapi_last_request_time = 0
        self.newsapi_request_interval = 60.0 / self.newsapi_requests_per_minute
    
    def gather_all_content(self, days_back: int = 7) -> List[Article]:
        """
        Gather content from all sources
        
        Args:
            days_back: Number of days to look back for content
            
        Returns:
            List of Article objects
        """
        articles = []
        
        logger.info("Starting content gathering from RSS feeds")
        rss_articles = self._gather_from_rss()
        articles.extend(rss_articles)
        logger.info(f"Gathered {len(rss_articles)} articles from RSS feeds")
        
        logger.info("Starting content gathering from NewsAPI")
        newsapi_articles = self._gather_from_newsapi(days_back)
        articles.extend(newsapi_articles)
        logger.info(f"Gathered {len(newsapi_articles)} articles from NewsAPI")
        
        # Categorize and filter articles
        categorized_articles = self._categorize_articles(articles)
        logger.info(f"Total categorized articles: {len(categorized_articles)}")
        
        return categorized_articles
    
    def _gather_from_rss(self) -> List[Article]:
        """
        Gather content from RSS feeds
        
        Returns:
            List of Article objects from RSS feeds
        """
        articles = []
        
        for feed_url in self.rss_feeds:
            try:
                logger.info(f"Parsing RSS feed: {feed_url}")
                feed = feedparser.parse(feed_url)
                
                if feed.bozo:
                    logger.warning(f"RSS feed parsing warning for {feed_url}: {feed.bozo_exception}")
                
                for entry in feed.entries:
                    try:
                        article = self._parse_rss_entry(entry, feed_url)
                        if article:
                            articles.append(article)
                    except Exception as e:
                        logger.error(f"Error parsing RSS entry from {feed_url}: {str(e)}")
                        continue
                
                # Small delay between feeds to be respectful
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error fetching RSS feed {feed_url}: {str(e)}")
                continue
        
        return articles
    
    def _parse_rss_entry(self, entry: Any, feed_url: str) -> Optional[Article]:
        """
        Parse a single RSS entry into an Article
        
        Args:
            entry: RSS feed entry
            feed_url: URL of the RSS feed
            
        Returns:
            Article object or None if parsing fails
        """
        try:
            # Extract title
            title = entry.get('title', '').strip()
            if not title:
                return None
            
            # Extract URL
            url = entry.get('link', '').strip()
            if not url:
                return None
            
            # Extract source
            source = entry.get('source', {}).get('title', '') or feed_url
            
            # Extract published date
            published_date = None
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                published_date = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc).isoformat()
            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                published_date = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc).isoformat()
            else:
                published_date = datetime.now(timezone.utc).isoformat()
            
            # Extract description/summary
            description = entry.get('summary', '') or entry.get('description', '')
            
            # Extract content
            content = None
            if hasattr(entry, 'content') and entry.content:
                content = entry.content[0].get('value', '')
            
            return Article(
                title=title,
                url=url,
                source=source,
                published_date=published_date,
                description=description,
                content=content
            )
            
        except Exception as e:
            logger.error(f"Error parsing RSS entry: {str(e)}")
            return None
    
    def _gather_from_newsapi(self, days_back: int = 7) -> List[Article]:
        """
        Gather content from NewsAPI
        
        Args:
            days_back: Number of days to look back
            
        Returns:
            List of Article objects from NewsAPI
        """
        if not self.newsapi_key:
            logger.warning("NewsAPI key not configured, skipping NewsAPI gathering")
            return []
        
        articles = []
        
        # Calculate date range
        to_date = datetime.now(timezone.utc)
        from_date = to_date - timedelta(days=days_back)
        
        # Search for Alzheimer's content
        alzheimers_query = ' OR '.join([f'"{kw}"' for kw in ['alzheimer', 'alzheimers', 'dementia']])
        alzheimers_articles = self._query_newsapi(alzheimers_query, from_date, to_date)
        articles.extend(alzheimers_articles)
        
        # Search for Parkinson's content - use full disease name to avoid false positives
        parkinsons_query = '"Parkinson\'s disease" OR "Parkinsons disease"'
        parkinsons_articles = self._query_newsapi(parkinsons_query, from_date, to_date)
        articles.extend(parkinsons_articles)
        
        return articles
    
    def _query_newsapi(
        self,
        query: str,
        from_date: datetime,
        to_date: datetime
    ) -> List[Article]:
        """
        Query NewsAPI with rate limiting
        
        Args:
            query: Search query
            from_date: Start date for search
            to_date: End date for search
            
        Returns:
            List of Article objects
        """
        # Rate limiting
        self._wait_for_rate_limit()
        
        try:
            url = f"{self.newsapi_base_url}/everything"
            params = {
                'q': query,
                'from': from_date.strftime('%Y-%m-%d'),
                'to': to_date.strftime('%Y-%m-%d'),
                'language': 'en',
                'sortBy': 'relevancy',
                'pageSize': 20,  # Limit to stay within free tier
                'apiKey': self.newsapi_key
            }
            
            logger.info(f"Querying NewsAPI with query: {query}")
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('status') != 'ok':
                logger.error(f"NewsAPI error: {data.get('message', 'Unknown error')}")
                return []
            
            articles = []
            for item in data.get('articles', []):
                article = self._parse_newsapi_article(item)
                if article:
                    articles.append(article)
            
            logger.info(f"Retrieved {len(articles)} articles from NewsAPI for query: {query}")
            return articles
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error querying NewsAPI: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error in NewsAPI query: {str(e)}")
            return []
    
    def _parse_newsapi_article(self, item: Dict[str, Any]) -> Optional[Article]:
        """
        Parse a NewsAPI article into an Article object
        
        Args:
            item: NewsAPI article data
            
        Returns:
            Article object or None
        """
        try:
            title = item.get('title', '').strip()
            url = item.get('url', '').strip()
            
            if not title or not url:
                return None
            
            source = item.get('source', {}).get('name', 'Unknown')
            
            # Parse published date
            published_at = item.get('publishedAt', '')
            if published_at:
                try:
                    published_date = datetime.fromisoformat(published_at.replace('Z', '+00:00')).isoformat()
                except:
                    published_date = datetime.now(timezone.utc).isoformat()
            else:
                published_date = datetime.now(timezone.utc).isoformat()
            
            description = item.get('description', '') or ''
            content = item.get('content', '') or ''
            
            return Article(
                title=title,
                url=url,
                source=source,
                published_date=published_date,
                description=description,
                content=content
            )
            
        except Exception as e:
            logger.error(f"Error parsing NewsAPI article: {str(e)}")
            return None
    
    def _wait_for_rate_limit(self):
        """Implement rate limiting for NewsAPI requests"""
        current_time = time.time()
        time_since_last_request = current_time - self.newsapi_last_request_time
        
        if time_since_last_request < self.newsapi_request_interval:
            sleep_time = self.newsapi_request_interval - time_since_last_request
            logger.info(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        
        self.newsapi_last_request_time = time.time()
    
    def _categorize_articles(self, articles: List[Article]) -> List[Article]:
        """
        Categorize articles as Alzheimer's or Parkinson's based on keywords
        
        Args:
            articles: List of Article objects
            
        Returns:
            List of categorized Article objects (only those matching keywords)
        """
        categorized = []
        
        for article in articles:
            # Combine title, description, and content for keyword matching
            text = f"{article.title} {article.description} {article.content or ''}".lower()
            
            # Check for Alzheimer's keywords
            alzheimers_match = any(keyword in text for keyword in self.alzheimers_keywords)
            
            # Check for Parkinson's keywords
            parkinsons_match = any(keyword in text for keyword in self.parkinsons_keywords)
            
            # Categorize (prefer Alzheimer's if both match)
            if alzheimers_match:
                article.category = 'alzheimers'
                categorized.append(article)
            elif parkinsons_match:
                article.category = 'parkinsons'
                categorized.append(article)
            # If neither matches, skip the article
        
        return categorized
    
    def deduplicate_articles(self, articles: List[Article]) -> List[Article]:
        """
        Remove duplicate articles based on URL
        
        Args:
            articles: List of Article objects
            
        Returns:
            Deduplicated list of Article objects
        """
        seen_urls = set()
        deduplicated = []
        
        for article in articles:
            if article.url not in seen_urls:
                seen_urls.add(article.url)
                deduplicated.append(article)
        
        logger.info(f"Deduplicated {len(articles)} articles to {len(deduplicated)}")
        return deduplicated
