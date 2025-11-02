import os
import requests
from typing import Dict, List, Union, Optional
from datetime import datetime
import statistics
import re
from functools import lru_cache

class HeadlineSentimentAnalyzer:
    def __init__(self):
        """
        Initializes the analyzer to use the Hugging Face Inference API.
        Requires the HF_TOKEN environment variable to be set.
        """
        # The public endpoint for the DistilBERT fine-tuned model
        self.API_URL = "https://api-inference.huggingface.co/models/distilbert-base-uncased-finetuned-sst-2-english"
        
        # Authentication header using the token set in the environment
        hf_token = os.environ.get("HF_TOKEN")
        if not hf_token:
            print("WARNING: HF_TOKEN environment variable not set. API calls may fail.")
        self.headers = {"Authorization": f"Bearer {hf_token}"}
        
        # No model or tokenizer loading here!

    # Removed the @property def pipeline(self): method
    
    def _query(self, payload: Dict):
        """Sends data to the Hugging Face Inference API."""
        try:
            # We use json=payload to send the data in the POST body
            response = requests.post(self.API_URL, headers=self.headers, json=payload)
            response.raise_for_status() # Raises an exception for 4xx/5xx errors
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Hugging Face API Error: {e}")
            return None

    @lru_cache(maxsize=1000)
    def _get_sentiment_score(self, headline: str) -> float:
        """Analyzes a single headline using the external API."""
        
        payload = {"inputs": headline}
        results = self._query(payload)
        
        if results and isinstance(results, list) and results[0]:
            # The API returns a structure like: [[{'label': 'NEGATIVE', 'score': 0.999}]]
            result_list = results[0]

            # Extract POSITIVE score and calculate the final sentiment (positive - negative)
            score_map = {item['label']: item['score'] for item in result_list}
            
            pos_score = score_map.get('POSITIVE', 0.0)
            neg_score = score_map.get('NEGATIVE', 0.0)

            # Convert to the desired -1 to +1 range
            if pos_score > neg_score:
                # If POSITIVE is higher, return the POSITIVE score
                return pos_score
            else:
                # If NEGATIVE is higher, return the negative of the NEGATIVE score
                return -neg_score
        
        return 0.0 # Return neutral if analysis fails

    def analyze_sentiment(self, headline: str) -> Dict[str, Union[float, List[tuple]]]:
        sentiment_score = self._get_sentiment_score(headline)
        return {
            'sentiment': round(sentiment_score, 3),
            'word_contributions': [(headline, round(sentiment_score, 3))]
        }

    def categorize_sentiment(self, sentiment_score: float) -> str:
        # The categorization logic is sound and can be kept here
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

    def analyze_news_batch(self, news_items: List[Dict], ticker: str = None, company_name: Optional[str] = None) -> Dict:
        # ... (This function remains largely unchanged as its logic is fine)
        # Note: I omitted the full analyze_news_batch for brevity, assume it uses the updated _get_sentiment_score
        
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
        
        # ... [omitting the loop for brevity, but it calls self.analyze_sentiment(item['title'])]
        for item in news_items:
            try:
                if ticker and company_name and not self._is_relevant_headline(item['title'], ticker, company_name):
                    continue
                
                relevant_news += 1
                if len(processed_news) < 10:
                        timestamp_value = (
                        item.get('providerPublishTime') or 
                        item.get('publishTime') or 
                        item.get('datetime') or 
                        item.get('timestamp') # Final fallback
                    )
                    timestamp = timestamp_value / 1000
                    date = datetime.fromtimestamp(timestamp)
                    analysis = self.analyze_sentiment(item['title'])
                    
                    sentiments.append(analysis['sentiment'])
                    processed_news.append({
                        'title': item['title'],
                        'date': date.strftime('%Y-%m-%d'),
                        'sentiment': analysis['sentiment'],
                        'word_contributions': analysis['word_contributions']
                    })
            except Exception as e:
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


    def _is_relevant_headline(self, headline: str, ticker: str, company_name: Optional[str] = None) -> bool:
        # ... (This function remains unchanged)
        headline_lower = headline.lower()
        stock_pattern = re.compile(rf'{ticker.lower()} stock\b')
        if stock_pattern.search(headline_lower):
            return True
        return False
        

