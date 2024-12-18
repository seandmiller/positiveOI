from typing import Dict, List, Union, Optional
from datetime import datetime
import statistics
import re
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
import torch
import numpy as np
from functools import lru_cache

class HeadlineSentimentAnalyzer:
    def __init__(self):
        """Initialize analyzer with DistilBERT model."""
        self.model_name = "distilbert-base-uncased-finetuned-sst-2-english"
        self._model = None
        self._tokenizer = None
        self._pipeline = None
        
    @property
    def pipeline(self):
        
        if self._pipeline is None:
            try:
                # Load tokenizer and model
                self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                self._model = AutoModelForSequenceClassification.from_pretrained(
                    self.model_name
                )
                
            
                self.device = -1
                print(f"Device set to use cpu")
                
                # Create pipeline
                self._pipeline = pipeline(
                    "sentiment-analysis",
                    model=self._model,
                    tokenizer=self._tokenizer,
                    device=self.device
                )
            except Exception as e:
                print(f"Error initializing model: {e}")
                raise
        return self._pipeline

    def _is_relevant_headline(self, headline: str, ticker: str, company_name: Optional[str] = None) -> bool:
    
        headline_lower = headline.lower()
        stock_pattern = re.compile(rf'{ticker.lower()} stock\b')
        
        if stock_pattern.search(headline_lower):
            return True

        return False

    @lru_cache(maxsize=1000)
    def _get_sentiment_score(self, headline: str) -> float:
   
        try:
         
            results = self.pipeline(headline)
            result = results[0]  # Get first result
            
            
            if result['label'] == 'POSITIVE':
                return result['score']
            else:
                return -result['score']
            
        except Exception as e:
            print(f"Error in sentiment analysis: {e}")
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
        
        for item in news_items:
            try:
                if ticker and company_name and not self._is_relevant_headline(item['title'], ticker, company_name):
                    continue
                
                relevant_news += 1
                if len(processed_news) < 10:
                    date = datetime.fromtimestamp(item['providerPublishTime'])
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

    def __del__(self):
      
        self._model = None
        self._tokenizer = None
        self._pipeline = None
        if torch.cuda.is_available():
            torch.cuda.empty_cache()