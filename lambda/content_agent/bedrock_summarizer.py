"""
Bedrock Summarizer Module
Handles content summarization using AWS Bedrock Claude models
"""

import json
import boto3
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from content_gatherer import Article

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@dataclass
class SummarizedContent:
    """Represents summarized content for a category"""
    category: str  # 'alzheimers' or 'parkinsons'
    overall_summary: str
    article_summaries: List[Dict[str, Any]]
    total_articles: int


class BedrockSummarizer:
    """Summarizes medical research content using AWS Bedrock"""
    
    # Cost safeguards
    MAX_ARTICLES_PER_CATEGORY = 25  # Maximum articles to process per category
    MAX_CONTENT_LENGTH = 1000  # Maximum characters from article content
    MAX_TOKENS_ARTICLE = 200  # Maximum tokens for article summary
    MAX_TOKENS_OVERALL = 300  # Maximum tokens for overall summary
    
    def __init__(
        self,
        model_id: str = "anthropic.claude-3-haiku-20240307-v1:0",
        region: str = "us-east-1"
    ):
        """
        Initialize the Bedrock summarizer
        
        Args:
            model_id: Bedrock model ID (default: Claude 3 Haiku for cost optimization)
            region: AWS region for Bedrock
        """
        self.model_id = model_id
        self.region = region
        
        try:
            self.bedrock_runtime = boto3.client(
                service_name='bedrock-runtime',
                region_name=region
            )
            logger.info(f"Initialized Bedrock client with model: {model_id}")
        except Exception as e:
            logger.error(f"Failed to initialize Bedrock client: {str(e)}")
            raise
    
    def summarize_articles(
        self,
        articles: List[Article],
        category: str
    ) -> SummarizedContent:
        """
        Summarize a list of articles for a specific category
        
        Args:
            articles: List of Article objects
            category: 'alzheimers' or 'parkinsons'
            
        Returns:
            SummarizedContent object with summaries
        """
        if not articles:
            logger.warning(f"No articles to summarize for category: {category}")
            return SummarizedContent(
                category=category,
                overall_summary="No new developments this week.",
                article_summaries=[],
                total_articles=0
            )
        
        # COST SAFEGUARD: Limit number of articles to process
        if len(articles) > self.MAX_ARTICLES_PER_CATEGORY:
            logger.warning(
                f"Limiting articles from {len(articles)} to {self.MAX_ARTICLES_PER_CATEGORY} "
                f"for cost optimization"
            )
            articles = articles[:self.MAX_ARTICLES_PER_CATEGORY]
        
        logger.info(f"Summarizing {len(articles)} articles for {category}")
        
        # Summarize individual articles
        article_summaries = []
        for article in articles:
            try:
                summary = self._summarize_single_article(article, category)
                if summary:
                    article_summaries.append(summary)
            except Exception as e:
                logger.error(f"Failed to summarize article '{article.title}': {str(e)}")
                # Continue with other articles
                continue
        
        # Generate overall summary
        overall_summary = self._generate_overall_summary(article_summaries, category)
        
        return SummarizedContent(
            category=category,
            overall_summary=overall_summary,
            article_summaries=article_summaries,
            total_articles=len(article_summaries)
        )
    
    def _summarize_single_article(
        self,
        article: Article,
        category: str
    ) -> Optional[Dict[str, Any]]:
        """
        Summarize a single article using Bedrock
        
        Args:
            article: Article object
            category: Category for context
            
        Returns:
            Dictionary with article summary
        """
        # Prepare content for summarization
        # COST SAFEGUARD: Limit content length to reduce token usage
        content = f"{article.title}\n\n{article.description}"
        if article.content:
            content += f"\n\n{article.content[:self.MAX_CONTENT_LENGTH]}"
        
        # Create prompt for medical research summarization
        disease_name = "Alzheimer's disease" if category == "alzheimers" else "Parkinson's disease"
        
        prompt = f"""Write a 2-3 sentence summary of this {disease_name} article. Focus on key findings, clinical significance, and practical implications for patients and caregivers.

Article:
{content}

Write only the summary, without any preamble or introduction:"""
        
        try:
            summary_text = self._invoke_bedrock(prompt, max_tokens=self.MAX_TOKENS_ARTICLE)
            
            return {
                'title': article.title,
                'source': article.source,
                'url': article.url,
                'published_date': article.published_date,
                'summary': summary_text,
                'original_description': article.description
            }
            
        except Exception as e:
            logger.error(f"Bedrock invocation failed for article: {str(e)}")
            return None
    
    def _generate_overall_summary(
        self,
        article_summaries: List[Dict[str, Any]],
        category: str
    ) -> str:
        """
        Generate an overall summary from individual article summaries
        
        Args:
            article_summaries: List of summarized articles
            category: Category name
            
        Returns:
            Overall summary text
        """
        if not article_summaries:
            return "No new developments this week."
        
        # Combine article summaries for context
        # COST SAFEGUARD: Limit to top 10 articles for overall summary
        combined_summaries = "\n\n".join([
            f"- {item['title']}: {item['summary']}"
            for item in article_summaries[:10]
        ])
        
        disease_name = "Alzheimer's disease" if category == "alzheimers" else "Parkinson's disease"
        
        prompt = f"""Write a 3-4 sentence overview of this week's {disease_name} developments based on these article summaries. Highlight the most significant findings and common themes.

Article Summaries:
{combined_summaries}

Write only the overview, without any preamble:"""
        
        try:
            overall_summary = self._invoke_bedrock(prompt, max_tokens=self.MAX_TOKENS_OVERALL)
            return overall_summary
        except Exception as e:
            logger.error(f"Failed to generate overall summary: {str(e)}")
            return f"This week's {disease_name} updates include {len(article_summaries)} new articles covering recent research and developments."
    
    def _invoke_bedrock(
        self,
        prompt: str,
        max_tokens: int = 500,
        temperature: float = 0.7
    ) -> str:
        """
        Invoke Bedrock model with the given prompt
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            
        Returns:
            Generated text response
        """
        # Prepare request body for Claude 3
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
        
        try:
            # Invoke Bedrock
            response = self.bedrock_runtime.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body)
            )
            
            # Parse response
            response_body = json.loads(response['body'].read())
            
            # Extract text from Claude 3 response format
            if 'content' in response_body and len(response_body['content']) > 0:
                text = response_body['content'][0]['text'].strip()
                
                # Clean up any prompt artifacts that might appear in response
                cleanup_phrases = [
                    "Here is a 2-3 sentence summary of the key points from the article:",
                    "Here is a 3-sentence summary of the key points from the article:",
                    "Here is a 2-3 sentence summary of the article for patients and caregivers:",
                    "Here is a 3-sentence summary of the article for patients and caregivers:",
                    "Here is a 2-3 sentence summary of the key points from the article related to",
                    "Here is a 2-3 sentence summary:",
                    "Here is a 3-sentence summary:",
                    "Here is a summary:",
                    "Here's a 2-3 sentence summary:",
                    "Here's a 3-sentence summary:",
                    "Here's a summary:"
                ]
                
                for phrase in cleanup_phrases:
                    # Check if text starts with the phrase (case-insensitive)
                    if text.lower().startswith(phrase.lower()):
                        text = text[len(phrase):].strip()
                        # Remove any leading newlines or colons
                        text = text.lstrip('\n:').strip()
                        break
                
                return text
            else:
                logger.error(f"Unexpected response format: {response_body}")
                return ""
                
        except Exception as e:
            logger.error(f"Bedrock invocation error: {str(e)}")
            raise
    
    def estimate_cost(
        self,
        num_articles: int,
        avg_article_length: int = 500
    ) -> Dict[str, float]:
        """
        Estimate the cost of processing articles
        
        Args:
            num_articles: Number of articles to process
            avg_article_length: Average article length in characters
            
        Returns:
            Dictionary with cost estimates
        """
        # Claude 3 Haiku pricing (as of 2024)
        # Input: $0.25 per 1M tokens
        # Output: $1.25 per 1M tokens
        
        # Rough estimation: 1 token ≈ 4 characters
        input_tokens_per_article = avg_article_length / 4 + 100  # Article + prompt
        output_tokens_per_article = 200  # Summary length
        
        total_input_tokens = input_tokens_per_article * num_articles
        total_output_tokens = output_tokens_per_article * num_articles
        
        # Add overall summary tokens
        total_input_tokens += 2000  # Combined summaries
        total_output_tokens += 300  # Overall summary
        
        input_cost = (total_input_tokens / 1_000_000) * 0.25
        output_cost = (total_output_tokens / 1_000_000) * 1.25
        total_cost = input_cost + output_cost
        
        return {
            'input_tokens': int(total_input_tokens),
            'output_tokens': int(total_output_tokens),
            'input_cost_usd': round(input_cost, 4),
            'output_cost_usd': round(output_cost, 4),
            'total_cost_usd': round(total_cost, 4)
        }
