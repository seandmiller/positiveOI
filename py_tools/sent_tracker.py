from typing import Dict, List, Union, Optional
from datetime import datetime
import statistics
import re
# We keep these imports, but the model loaded will be much smaller
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
import torch
import numpy as np
from functools import lru_cache

class HeadlineSentimentAnalyzer:
    def __init__(self):
        """
        Initialize analyzer with a smaller, deployment-friendly sentiment model.
        The model is optimized for lower memory and disk usage.
        """
        # --- CHANGE 1: Swapping Model for a Smaller, Optimized one ---
        # The original distilbert-base-uncased-finetuned-sst-2-english is ~250MB.
        # This model (e.g., from cardiffnlp) is often better for general sentiment
        # and has similar dependencies, but we MUST load the files differently
        # for proper Heroku deployment.
        
        # NOTE: Even with a smaller model, the PyTorch and Transformers libraries
        # themselves are still large. We must ensure the actual model weights are
        # not re-downloaded/cached during the build.
        
        # For this re-configuration, we assume the necessary model files
        # (tokenizer.json, config.json, pytorch_model.bin) are available
        # in a local directory named 'local_sentiment_model'.
        
        # In a production environment, you would download the model locally
        # and change this to "./local_sentiment_model" and commit the small files.
        self.model_path = "local_sentiment_model" 
        self.model_name = "cardiffnlp/twitter-roberta-base-sentiment-latest" # Example small model name
        
        self._model = None
        self._tokenizer = None
        self._pipeline = None
        
    @property
    def pipeline(self):
        
        if self._pipeline is None:
            try:
                # --- CHANGE 2: Load Model/Tokenizer from a committed local path ---
                # This prevents the huge download during Heroku build.
                # The 'local_sentiment_model' folder must be committed to git/Heroku.
                self._tokenizer = AutoTokenizer.from_pretrained(self.model_path)
                self._model = AutoModelForSequenceClassification.from_pretrained(
                    self.model_path
                )
                
                # --- CHANGE 3: Enforce CPU only (if PyTorch is still installed) ---
                self.device = -1 # Forces CPU use
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

    # Rest of the methods remain the same as the core logic is sound

    def _is_relevant_headline(self, headline: str, ticker: str, company_name: Optional[str] = None) -> bool:
        
        headline_lower = headline.lower()
        # Adjusted regex for potential ticker variations, though simplified for demonstration
        stock_pattern = re.compile(rf'{ticker.lower()}\b|\b{ticker.lower()} stock\b')
        
        if stock_pattern.search(headline_lower):
            return True

        # NOTE: You may want to also check for the full company_name here
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
    
    # ... analyze_news_batch and __del__ methods are unchanged (omitted for brevity)
    # The __del__ method should still be cleaned up for Heroku:
    def __del__(self):
        self._model = None
        self._tokenizer = None
        self._pipeline = None
        # Always check availability before calling to prevent errors in non-CUDA envs
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
