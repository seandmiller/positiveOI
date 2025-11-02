import os
import requests
from typing import Dict, List, Union, Optional
from datetime import datetime
import statistics
import re
from functools import lru_cache

class HeadlineSentimentAnalyzer:
    def __init__(self):
        """Initializes the analyzer to use the Hugging Face Inference API."""
        
        self.API_URL = "https://api-inference.huggingface.co/models/cardiffnlp/twitter-roberta-base-sentiment-latest"
        
        hf_token = os.environ.get("HF_TOKEN")
  
        if not hf_token:
            print("WARNING: HF_TOKEN environment variable not set. API calls will fail.")
        self.headers = {"Authorization": f"Bearer {hf_token}"}
        
    def _query(self, payload: Dict):
        """Sends data to the Hugging Face Inference API."""
        try:
            response = requests.post(self.API_URL, headers=self.headers, json=payload)
            response.raise_for_status() 
           
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Hugging Face API Error: {e}")
            return None

    @lru_cache(maxsize=1000)
    def _get_sentiment_score(self, headline: str) -> float:
        """Analyzes a single headline using the external API."""
        
        payload = {"inputs": headline}
        results = self._query(payload)
        print(results)
        if results and isinstance(results, list) and results[0]:
            result_list = results[0]
            score_map = {item['label']: item['score'] for item in result_list}
            
            pos_score = score_map.get('POSITIVE', 0.0)
            neg_score = score_map.get('NEGATIVE', 0.0)
            
            if pos_score > neg_score:
                return pos_score
            else:
                return -neg_score
        
        return 0.0

    def analyze_sentiment(self, headline: str) -> Dict[str, Union[float, List[tuple]]]:
        sentiment_score = self._get_sentiment_score(headline)
        return {
            'sentiment': round(sentiment_score, 3),
            'word_contributions': [(headline, round(sentiment_score, 3))]
        }

    def categorize_sentiment(self, sentiment_score: float) -> str:
        
        if sentiment_score >= 0.5:
            return 'Very Positive'
        elif sentiment_score >= 0.1:
            return 'Positive'
        elif sentiment_score <= -0.5:
            return 'Very Negative'
        elif sentiment_score <= -0.1:
            return 'Negative'
        else:
            return 'Neutral'

    def _is_relevant_headline(self, headline: str, ticker: str, company_name: Optional[str] = None) -> bool:
        headline_lower = headline.lower()
        # Simplified to match just the ticker to keep this function self-contained
        stock_pattern = re.compile(rf'{ticker.lower()} stock\b|\b{ticker.lower()}\b') 
        if stock_pattern.search(headline_lower):
            return True
        return False
        
    def analyze_news_batch(self, news_items: List[Dict], ticker: str = None, company_name: Optional[str] = None) -> Dict:
        
        if not news_items:
             return {
                'averageSentiment': 0,
                'sentimentCategory': 'Neutral',
                'newsCount': 0,
                'recentNews': [],
                'relevantNewsCount': 0
             }
        
        processed_news = []
        sentiments = []
        total_news = len(news_items)
        relevant_news = 0
        
        # Define the expected date format for the nested structure (ISO 8601 string)
        # Note: '%Y-%m-%dT%H:%M:%SZ' matches '2025-11-01T17:01:53Z' exactly.
        DATE_FORMAT = '%Y-%m-%dT%H:%M:%SZ'
        
        for item in news_items:
            try:
                # Use the nested title for relevance check
                headline_to_check = item.get('content', {}).get('title', item.get('title', ''))
                
                if ticker and company_name and not self._is_relevant_headline(headline_to_check, ticker, company_name):
                    continue
                
                relevant_news += 1
                if len(processed_news) < 10:
                    
                    # 1. Access the date string from the new nested structure
                    # Use .get() chains for safe access
                    date_string = item.get('content', {}).get('pubDate')
                    
                    if not date_string:
                        # Skip if the date key is missing
                        print("Skipping news item: Missing 'content' or 'pubDate' key.")
                        continue
                        
                    # 2. Parse the ISO 8601 string into a datetime object
                    date = datetime.strptime(date_string, DATE_FORMAT)
                    
                    # Use the nested title for sentiment analysis and final result
                    final_title = item.get('content', {}).get('title', headline_to_check)
                    
                    analysis = self.analyze_sentiment(final_title) 
                    
                    sentiments.append(analysis['sentiment'])
                    processed_news.append({
                        'title': final_title, 
                        'date': date.strftime('%Y-%m-%d'),
                        'sentiment': analysis['sentiment'],
                        'word_contributions': analysis['word_contributions']
                    })
            except Exception as e:
                # Catching general exception during processing of a single news item
                print(f"Error processing news item: {e}")
                continue
        
        avg_sentiment = statistics.mean(sentiments) if sentiments else 0
        
        return {
            'averageSentiment': round(avg_sentiment, 3),
            'sentimentCategory': self.categorize_sentiment(avg_sentiment),
            'newsCount': total_news,
            'relevantNewsCount': relevant_news,
            'recentNews': processed_news
        }
