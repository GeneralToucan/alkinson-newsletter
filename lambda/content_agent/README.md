# Content Agent - RSS Feed and NewsAPI Content Gathering

This module implements the content gathering functionality for the Alkinson Newsletter system.

## Features

### RSS Feed Parser
- Parses multiple RSS feeds using the `feedparser` library
- Handles malformed feeds gracefully with error logging
- Extracts title, URL, source, published date, description, and content
- Implements respectful delays between feed requests

### NewsAPI Client
- Queries NewsAPI for Alzheimer's and Parkinson's disease content
- Implements rate limiting (5 requests per minute) to stay within free tier
- Supports date range filtering (default: last 7 days)
- Handles API errors and timeouts gracefully
- Limits results to 20 articles per query to optimize costs

### Content Filtering
- Filters content based on configurable keyword lists
- Alzheimer's keywords: alzheimer, alzheimers, dementia, cognitive decline, memory loss, beta amyloid, tau protein, neurodegeneration
- Parkinson's keywords: parkinson's disease, parkinsons', dopamine, motor symptoms, tremor, bradykinesia, rigidity, lewy body
- Categorizes articles as 'alzheimers' or 'parkinsons'
- Removes articles that don't match any keywords

### Deduplication
- Removes duplicate articles based on URL
- Ensures unique content in the final output

## Usage

```python
from content_gatherer import ContentGatherer

# Initialize the gatherer
gatherer = ContentGatherer(
    newsapi_key='your-api-key',
    rss_feeds=[
        'https://www.alzheimers.org.uk/news/rss.xml',
        'https://www.parkinson.org/news/rss',
    ],
    alzheimers_keywords=['alzheimer', 'dementia', ...],
    parkinsons_keywords=["parkinson's disease", 'dopamine', ...]
)

# Gather content from all sources
articles = gatherer.gather_all_content(days_back=7)

# Deduplicate
articles = gatherer.deduplicate_articles(articles)

# Separate by category
alzheimers_articles = [a for a in articles if a.category == 'alzheimers']
parkinsons_articles = [a for a in articles if a.category == 'parkinsons']
```

## Article Data Structure

```python
@dataclass
class Article:
    title: str              # Article title
    url: str                # Article URL
    source: str             # Source name
    published_date: str     # ISO format datetime
    description: str        # Article summary/description
    content: Optional[str]  # Full article content (if available)
    category: Optional[str] # 'alzheimers' or 'parkinsons'
```

## Error Handling

- RSS feed parsing errors are logged but don't stop execution
- NewsAPI errors are caught and logged
- Rate limiting prevents API throttling
- Missing or invalid data is handled gracefully

## Testing

Run unit tests:
```bash
python test_unit.py
```

Run integration test (requires internet connection):
```bash
python test_content_gatherer.py
```

## Requirements

See `requirements.txt`:
- feedparser>=6.0.10
- requests>=2.31.0
- boto3>=1.28.0

## Environment Variables

- `NEWSAPI_KEY`: API key for NewsAPI (optional, but recommended)

## Implementation Notes

- Implements Requirements 5.2 and 5.3 from the requirements document
- Designed to work within AWS Lambda constraints
- Optimized for AWS free tier usage
- Logging configured for CloudWatch integration
