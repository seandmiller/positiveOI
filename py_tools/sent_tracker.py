from typing import Dict, List, Union, Optional
from datetime import datetime
import statistics
import re
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
import torch


class HeadlineSentimentAnalyzer:
    def __init__(self):
     
        self.model_name = "ProsusAI/finbert"
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
            self.device = 0 if torch.cuda.is_available() else -1
            self.sentiment_pipeline = pipeline(
                "sentiment-analysis",
                model=self.model,
                tokenizer=self.tokenizer,
                device=self.device
            )
        except Exception as e:
            print(f"Error initializing FinBERT model: {e}")
            raise

    def _is_relevant_headline(self, headline: str, ticker: str, company_name: Optional[str] = None) -> bool:
      
        headline_lower = headline.lower()
        
        stock_pattern = re.compile(rf'{ticker.lower()} stock\b')
        
     
        if stock_pattern.search(headline_lower):
            return True
            

                
        # Check for company name if provided
        if company_name:
            company_lower = company_name.lower()
            company_names = [
                company_lower,
                company_lower.replace(" inc", ""),
                company_lower.replace(" corporation", ""),
                company_lower.replace(" corp", ""),
                company_lower.replace(" ltd", ""),
                company_lower.replace(" llc", "")
            ]
            
            for name in company_names:
                name_pattern = re.compile(rf'\b{re.escape(name)}\b')
                if name_pattern.search(headline_lower):

                    return True
        
        return False

    def analyze_sentiment(self, headline: str) -> Dict[str, Union[float, List[tuple]]]:
        """Analyze sentiment using FinBERT model."""
        try:
            # Get sentiment prediction
            result = self.sentiment_pipeline(headline)[0]
            
            # Convert label to score (-1 to 1 range)
            label_scores = {
                'positive': 1.0,
                'negative': -1.0,
                'neutral': 0.0
            }
            
            sentiment_score = label_scores[result['label']] * result['score']
            
            # Create word contributions based on attention weights
            # Note: This is a simplified version since we can't easily get word-level contributions
            # from the neural network without additional processing
            word_contributions = [
                (headline, round(sentiment_score, 3))
            ]
            
            return {
                'sentiment': round(sentiment_score, 3),
                'word_contributions': word_contributions
            }
        except Exception as e:
            print(f"Error in sentiment analysis: {e}")
            return {
                'sentiment': 0.0,
                'word_contributions': []
            }

    def categorize_sentiment(self, sentiment_score: float) -> str:
        """Categorize sentiment score into labels."""
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
        """Analyze a batch of news items."""
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
                # Skip if ticker/company provided and headline not relevant
                if ticker and company_name and not self._is_relevant_headline(item['title'], ticker, company_name):
                    continue
                
                relevant_news += 1
                if len(processed_news) < 10:  # Only process first 10 relevant news items
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