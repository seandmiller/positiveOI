from typing import Dict, List, Union, Optional
from datetime import datetime
import statistics
import re

class HeadlineSentimentAnalyzer:
    def __init__(self):
        # Updated domain-specific terms with stock-specific context
        self.domain_specific_terms = {
            # Strong positive indicators
            "record high": 1.0,
            "all-time high": 1.0,
            "breakout": 0.8,
            "surge": 0.7,
            "rally": 0.7,
            "soar": 0.7,
            "bullish": 0.6,
            "upgrade": 0.6,
            "outperform": 0.6,
            "boost": 0.5,           
            "strike": -0.6,
            "strike authorization": -0.5,
            "labor dispute": -0.4,
            "walkout": -0.5,
            "unionize": -0.3,
            "union": -0.2,  
            "protest": -0.4,
            "picket": -0.4,
            "authorize strike": -0.5,
            "authorize": 0,  
            "labor action": -0.4,
            "work stoppage": -0.5,
            "labor tension": -0.4,
            "contract dispute": -0.4,
            "teamsters": -0.1,  
            
            # Positive resolution terms
            "agreement reached": 0.5,
            "deal reached": 0.5,
            "settlement": 0.4,
            "resolution": 0.4,
            "contract approved": 0.5,
            
           
            "plunge": -0.8,
            "crash": -0.8,
            "tumble": -0.7,
            "slump": -0.7,
            "bearish": -0.6,
            "downgrade": -0.6,
            "underperform": -0.6,
            "lower": -0.4,
            "drops": -0.4,
            "falls": -0.4,
            
            # Price movement contexts
            "reverses": -0.3,  # Usually indicates a negative turn
            "pulls back": -0.3,
            "rebounds": 0.4,   # Usually indicates recovery
            "recovers": 0.4,
            
            # Stock rating contexts
            "buy": 0.5,
            "strong buy": 0.7,
            "sell": -0.5,
            "strong sell": -0.7,
            "hold": 0,
            
            # Neutral/contextual terms
            "target": 0,
            "price target": 0,
            "moves": 0,
            "trading": 0,
            "partners": 0.2,
            "deploys": 0.2
        }
        
        # Price-related modifiers
        self.price_modifiers = {
            "higher": 0.3,
            "raised": 0.3,
            "increased": 0.3,
            "lifted": 0.3,
            "lower": -0.3,
            "cut": -0.3,
            "reduced": -0.3,
            "slashed": -0.4
        }
        
        self.intensifiers = {
            "very": 1.5,
            "strongly": 1.5,
            "sharply": 1.3,
            "significantly": 1.3,
            "substantially": 1.3,
            "massively": 1.4,
            "slightly": 0.7,
            "marginally": 0.7
        }
        
        self.negations = {
            "not", "no", "never", "none", "neither", "nor", "nobody", 
            "nowhere", "without", "fails", "fail", "failed"
        }

    def _is_relevant_headline(self, headline: str, ticker: str, company_name: Optional[str] = None) -> bool:

       headline_lower = headline.lower()
    
    # Create patterns for exact matching of ticker
       ticker_pattern = re.compile(rf'\b{ticker.lower()}\b')
       ticker_with_parens = re.compile(rf'\({ticker.upper()}\)')
       stock_pattern = re.compile(rf'{ticker.lower()} stock\b')
    
    # Check for explicit stock mentions
       if stock_pattern.search(headline_lower):
          return True
        
    # Check for ticker symbols with careful context
       if ticker_pattern.search(headline_lower) or ticker_with_parens.search(headline):
        # Skip if another company's stock is the main subject
           other_companies = ['rivian', 'nvidia', 'apple', 'amazon', 'meta', 'microsoft', 'alphabet', 'google']
           for company in other_companies:
              if f"{company} stock" in headline_lower:
                  return False
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
              
                  other_companies = ['rivian', 'nvidia', 'apple', 'amazon', 'meta', 'microsoft', 'alphabet', 'google']
                  for company in other_companies:
                      if f"{company} stock" in headline_lower:
                          return False
                  return True
    
       return False

    def _extract_percentage(self, text: str) -> Optional[float]:
        """Extract percentage values from text."""
        percentage_match = re.search(r'(\d+(?:\.\d+)?)%', text)
        if percentage_match:
            return float(percentage_match.group(1))
        return None

    def analyze_sentiment(self, headline: str) -> Dict[str, Union[float, List[tuple]]]:
        """Enhanced sentiment analysis for stock headlines."""
        headline_lower = headline.lower()
        words = headline_lower.split()
        sentiment_value = 0
        word_contributions = []
        
        # Check for percentage movements
        percentage = self._extract_percentage(headline)
        if percentage:
            if any(term in headline_lower for term in ["gain", "up", "rise", "higher", "rally"]):
                sentiment_value += min(percentage / 20, 1.0)  # Cap at 1.0
            elif any(term in headline_lower for term in ["drop", "down", "fall", "lower", "decline"]):
                sentiment_value -= min(percentage / 20, 1.0)  # Cap at -1.0

        # Analyze phrases and words
        for i, word in enumerate(words):
            # Check for price target context
            if "target" in word and i > 0:
                prev_word = words[i-1]
                if prev_word in self.price_modifiers:
                    sentiment_value += self.price_modifiers[prev_word]
                    word_contributions.append((f"{prev_word} target", self.price_modifiers[prev_word]))
            
            # Check domain specific terms
            if word in self.domain_specific_terms:
                word_sentiment = self.domain_specific_terms[word]
                multiplier = self._get_intensifier_multiplier(words, i)
                
                if self._check_negation(words, i):
                    word_sentiment *= -1
                
                final_sentiment = word_sentiment * multiplier
                sentiment_value += final_sentiment
                
                if final_sentiment != 0:
                    word_contributions.append((word, final_sentiment))
        
        # Normalize sentiment to [-1, 1] range using tanh
        from math import tanh
        normalized_sentiment = tanh(sentiment_value)
        
        return {
            'sentiment': round(normalized_sentiment, 3),
            'word_contributions': word_contributions
        }

    def _check_negation(self, words: List[str], index: int) -> bool:
        """Check for negations in context."""
        start = max(0, index - 3)
        previous_words = words[start:index]
        return any(word in self.negations for word in previous_words)

    def _get_intensifier_multiplier(self, words: List[str], index: int) -> float:
        """Get intensity multiplier from context."""
        multiplier = 1.0
        start = max(0, index - 2)
        previous_words = words[start:index]
        
        for word in previous_words:
            if word in self.intensifiers:
                multiplier *= self.intensifiers[word]
        return multiplier

    def analyze_news_batch(self, news_items: List[Dict], ticker: str, company_name: Optional[str] = None) -> Dict:
        """Analyze a batch of news items with improved filtering and sentiment analysis."""
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
                if not self._is_relevant_headline(item['title'], ticker, company_name):
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

    def categorize_sentiment(self, sentiment_score: float) -> str:
        """Categorize sentiment with refined thresholds."""
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

    def analyze_news_batch(self, news_items: List[Dict]) -> Dict:
        
        if not news_items:
            return {
                'averageSentiment': 0,
                'sentimentCategory': 'Neutral',
                'newsCount': 0,
                'recentNews': []
            }
        
        processed_news = []
        sentiments = []
        
        for item in news_items[:10]:  
            try:
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
            'newsCount': len(processed_news),
            'recentNews': processed_news
        }