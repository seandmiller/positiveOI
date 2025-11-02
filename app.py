from flask import Flask, jsonify, render_template
import yfinance as yf
from py_tools.sent_tracker import HeadlineSentimentAnalyzer
from py_tools.calc_tools import FinancialCalculator


app = Flask(__name__)
def get_news_sentiment(ticker_symbol):
    try:
        stock = yf.Ticker(ticker_symbol)
        news = stock.news
        analyzer = HeadlineSentimentAnalyzer()
 
        return analyzer.analyze_news_batch(news)
        
    except Exception as e:
        raise ValueError(f"Error analyzing news sentiment: {str(e)}")


@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/metrics/<ticker>')
def get_metrics(ticker):
    try:
        calculator = FinancialCalculator()
        financial_data = calculator.get_quarterly_data(ticker.upper())
        profitability_data = calculator.calculate_profitability(financial_data)
        sentiment_data = get_news_sentiment(ticker.upper())
        
        response = {
            'inputMetrics': financial_data,
            'profitability': profitability_data,
            'sentiment': sentiment_data
        }
        
        return jsonify(response)
    except ValueError as e:
        return str(e), 400
if __name__ == '__main__':
    app.run(debug=True)
