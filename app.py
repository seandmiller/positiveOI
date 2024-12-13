from flask import Flask, jsonify, render_template
from flask_cors import CORS
import yfinance as yf
import numpy as np
import math
import pandas as pd

app = Flask(__name__)
CORS(app)
def calculate_growth_rate(current, previous):
    """Calculate growth rate with proper error handling"""
    try:
        if previous is None or current is None:
            return 0
        if previous == 0:
            return 0
        return ((current / previous) - 1) * 100
    except Exception as e:
        print(f"Error calculating growth rate: {e}")
        return 0
def clean_number(value):
    """Handle NaN, inf, and -inf values"""
    if isinstance(value, (np.floating, float)):
        if math.isnan(value) or math.isinf(value):
            return 0
    return value

def get_quarterly_data(ticker_symbol):
    try:
        ticker = yf.Ticker(ticker_symbol)
        income_stmt = ticker.quarterly_income_stmt
        
        if income_stmt.empty:
            raise ValueError("No financial data available")

        latest_quarter = income_stmt.columns[0]
        previous_quarter = income_stmt.columns[1]

        # Get revenue
        try:
            current_revenue = clean_number(income_stmt.loc['Total Revenue', latest_quarter] / 1e6)
            previous_revenue = clean_number(income_stmt.loc['Total Revenue', previous_quarter] / 1e6)
        except KeyError:
            try:
                current_revenue = clean_number(income_stmt.loc['Revenue', latest_quarter] / 1e6)
                previous_revenue = clean_number(income_stmt.loc['Revenue', previous_quarter] / 1e6)
            except KeyError:
                raise ValueError("Revenue data not available")

        # Calculate operating expenses (excluding Cost of Revenue)
        operating_expense_items = [
            'Research Development',
            'Selling General Administrative',
            'Operating Expense'  # Some companies report this directly
        ]
        
        current_op_expenses = 0
        previous_op_expenses = 0
        
        print("\nOperating Expense Components:")
        for item in operating_expense_items:
            if item in income_stmt.index:
                current_value = abs(clean_number(income_stmt.loc[item, latest_quarter] / 1e6))
                previous_value = abs(clean_number(income_stmt.loc[item, previous_quarter] / 1e6))
                current_op_expenses += current_value
                previous_op_expenses += previous_value
                print(f"{item}: Current=${current_value}M, Previous=${previous_value}M")

        if current_op_expenses == 0:
            raise ValueError("Operating expense data not available")

        # Calculate gross margin
        try:
            gross_profit = income_stmt.loc['Gross Profit', latest_quarter]
            gross_margin = clean_number((gross_profit / income_stmt.loc['Total Revenue', latest_quarter]) * 100)
        except KeyError:
            try:
                cost_of_revenue = abs(income_stmt.loc['Cost Of Revenue', latest_quarter])
                gross_profit = income_stmt.loc['Total Revenue', latest_quarter] - cost_of_revenue
                gross_margin = clean_number((gross_profit / income_stmt.loc['Total Revenue', latest_quarter]) * 100)
            except:
                raise ValueError("Unable to calculate gross margin")

        # Calculate growth rates
        revenue_growth = calculate_growth_rate(current_revenue, previous_revenue)
        expense_growth = calculate_growth_rate(current_op_expenses, previous_op_expenses)

        result = {
            'quarterlyRevenue': round(float(current_revenue), 1),
            'grossMargin': round(float(gross_margin), 1),
            'operatingExpenses': round(float(current_op_expenses), 1),
            'revenueGrowthRate': round(float(revenue_growth), 1),
            'expenseGrowthRate': round(float(expense_growth), 1)
        }

        print("\nFinal Metrics:")
        for key, value in result.items():
            print(f"{key}: {value}")
            
        return result

    except ValueError as e:
        raise ValueError(str(e))
    except Exception as e:
        raise ValueError(f"Error processing data for {ticker_symbol}: {str(e)}")
def calculate_profitability(data):
    """
    Calculate quarters to profitability using the formula:
    P(t) = [R₀(1 + g)^t × m] - [E₀(1 + e)^t]
    Using actual revenue and expense growth rates
    """
    
    # Extract initial values
    R0 = data['quarterlyRevenue']
    E0 = data['operatingExpenses']
    m = data['grossMargin'] / 100
    g = math.pow(1 + data['revenueGrowthRate'] / 100, 1/4) - 1  # Quarterly revenue growth
    e = math.pow(1 + data['expenseGrowthRate'] / 100, 1/4) - 1  # Quarterly expense growth

    print(E0, R0, m)
    if E0 == 0:
        return {
            'quartersToProfitability': 'N/A',
            'yearsToProfit': 'N/A',
            'projectedRevenue': R0,
            'projectedExpenses': 0,
            'projectedProfit': 0
        }

    # Check if already profitable
    initial_profit = (R0 * m) - E0
    if initial_profit > 0:
        return {
            'quartersToProfitability': 0,
            'yearsToProfit': 0,
            'projectedRevenue': R0,
            'projectedExpenses': E0,
            'projectedProfit': initial_profit
        }

    # Find quarter where P(t) becomes positive
    # Using the formula: P(t) = [R₀(1 + g)^t × m] - [E₀(1 + e)^t]
    t = 0
    max_quarters = 40  # 10 years maximum

    while t < max_quarters:
       revenue_with_growth = R0 * math.pow(1 + g, t)  # R₀(1 + g)^t
       gross_profit = revenue_with_growth * m  # Apply margin to get actual profit from revenue
       expenses_with_growth = E0 * math.pow(1 + e, t)  # E₀(1 + e)^t
       profit = gross_profit - expenses_with_growth  
        
       if profit > 0:
            break
       t += 1
   
    # Calculate final values using the formula
    final_revenue = R0 * math.pow(1 + g, t)
    final_expenses = E0 * math.pow(1 + e, t)
    final_profit = (final_revenue * m) - final_expenses

    if t >= max_quarters:
        return {
            'quartersToProfitability': 'Not projected to be profitable within 10 years',
            'yearsToProfit': 'N/A',
            'projectedRevenue': round(final_revenue, 1),
            'projectedExpenses': round(final_expenses, 1),
            'projectedProfit': round(final_profit, 1)
        }

    return {
        'quartersToProfitability': t,
        'yearsToProfit': round(t / 4, 1),
        'projectedRevenue': round(final_revenue, 1),
        'projectedExpenses': round(final_expenses, 1),
        'projectedProfit': round(final_profit, 1)
    }
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/metrics/<ticker>')
def get_metrics(ticker):
    try:
        financial_data = get_quarterly_data(ticker.upper())
        profitability_data = calculate_profitability(financial_data)
        
        # Combine the data
        response = {
            'inputMetrics': financial_data,
            'profitability': profitability_data
        }
        
        return jsonify(response)
    except ValueError as e:
        return str(e), 400

if __name__ == '__main__':
    app.run(debug=True)