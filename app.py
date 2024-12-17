from flask import Flask, jsonify, render_template
import yfinance as yf
import numpy as np
import math

app = Flask(__name__)

def calculate_growth_rate(current, previous):
  
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
    if isinstance(value, (np.floating, float)):
        if math.isnan(value) or math.isinf(value):
            return 0
    return round(float(value), 2)

def get_quarterly_data(ticker_symbol):
    try:
        ticker = yf.Ticker(ticker_symbol)
        income_stmt = ticker.quarterly_income_stmt
        
        if income_stmt.empty:
            raise ValueError("No financial data available")

        quarters = income_stmt.columns[:4]
        if len(quarters) < 4:
            raise ValueError("Insufficient quarterly data available")

        quarterly_metrics = []
        
        for i in range(3):
            current_quarter = quarters[i]
            previous_quarter = quarters[i + 1]
            
            # Get revenue
            try:
                current_revenue = clean_number(income_stmt.loc['Total Revenue', current_quarter] / 1e6)
                previous_revenue = clean_number(income_stmt.loc['Total Revenue', previous_quarter] / 1e6)
            except KeyError:
                try:
                    current_revenue = clean_number(income_stmt.loc['Revenue', current_quarter] / 1e6)
                    previous_revenue = clean_number(income_stmt.loc['Revenue', previous_quarter] / 1e6)
                except KeyError:
                    raise ValueError("Revenue data not available")

            # Calculate operating expenses - Fixed to avoid double counting
            current_op_expenses = 0
            previous_op_expenses = 0
            
            # First try to get the total Operating Expense
            if 'Operating Expense' in income_stmt.index:
                current_op_expenses = abs(clean_number(income_stmt.loc['Operating Expense', current_quarter] / 1e6))
                previous_op_expenses = abs(clean_number(income_stmt.loc['Operating Expense', previous_quarter] / 1e6))
            else:
                # If no total Operating Expense, sum R&D and SG&A
                expense_components = [
                    'Research Development',
                    'Selling General Administrative'
                ]
                
                for item in expense_components:
                    if item in income_stmt.index:
                        current_op_expenses += abs(clean_number(income_stmt.loc[item, current_quarter] / 1e6))
                        previous_op_expenses += abs(clean_number(income_stmt.loc[item, previous_quarter] / 1e6))

            if current_op_expenses == 0:
                raise ValueError("Operating expense data not available")

            
            try:
                gross_profit = income_stmt.loc['Gross Profit', current_quarter]
                gross_margin = clean_number((gross_profit / income_stmt.loc['Total Revenue', current_quarter]) * 100)
            except KeyError:
                try:
                    cost_of_revenue = abs(income_stmt.loc['Cost Of Revenue', current_quarter])
                    gross_profit = income_stmt.loc['Total Revenue', current_quarter] - cost_of_revenue
                    gross_margin = clean_number((gross_profit / income_stmt.loc['Total Revenue', current_quarter]) * 100)
                except:
                    raise ValueError("Unable to calculate gross margin")

            revenue_growth = calculate_growth_rate(current_revenue, previous_revenue)
            expense_growth = calculate_growth_rate(current_op_expenses, previous_op_expenses)

            quarterly_metrics.append({
                'quarterlyRevenue': round(float(current_revenue), 1),
                'grossMargin': round(float(gross_margin), 1),
                'operatingExpenses': round(float(current_op_expenses), 1),
                'revenueGrowthRate': round(float(revenue_growth), 1),
                'expenseGrowthRate': round(float(expense_growth), 1)
            })

      
        result = {
            'quarterlyRevenue': round(sum(q['quarterlyRevenue'] for q in quarterly_metrics) / len(quarterly_metrics), 1),
            'grossMargin': round(sum(q['grossMargin'] for q in quarterly_metrics) / len(quarterly_metrics), 1),
            'operatingExpenses': round(sum(q['operatingExpenses'] for q in quarterly_metrics) / len(quarterly_metrics), 1),
            'revenueGrowthRate': round(sum(q['revenueGrowthRate'] for q in quarterly_metrics) / len(quarterly_metrics), 1),
            'expenseGrowthRate': round(sum(q['expenseGrowthRate'] for q in quarterly_metrics) / len(quarterly_metrics), 1)
        }

        return result

    except ValueError as e:
        raise ValueError(str(e))
    except Exception as e:
        raise ValueError(f"Error processing data for {ticker_symbol}: {str(e)}")

def calculate_profitability(data):
    # Extract initial values using averaged data
    R0 = data['quarterlyRevenue']
    E0 = data['operatingExpenses']
    m = data['grossMargin'] / 100
    g = math.pow(1 + data['revenueGrowthRate'] / 100, 1/4) - 1  
    e = math.pow(1 + data['expenseGrowthRate'] / 100, 1/4) - 1  

    print(E0, R0, m)
    if E0 == 0:
        return {
            'quartersToProfitability': 'N/A',
            'yearsToProfit': 'N/A',
            'projectedRevenue': R0,
            'projectedGrossProfit': 0,
            'projectedExpenses': 0,
            'projectedProfit': 0
        }

    # Check if already profitable
    initial_profit = (R0 * m) - E0
    if initial_profit > 0:
      return {
       'quartersToProfitability': 0,
       'yearsToProfit': 0,
       'projectedRevenue': clean_number(R0),
       'projectedGrossProfit': clean_number(R0 * m),
       'projectedExpenses': clean_number(E0),
       'projectedProfit': clean_number(initial_profit)
   }

    # Find quarter where P(t) becomes positive
    t = 0
    max_quarters = 40  # 10 years maximum

    while t < max_quarters:
        revenue_with_growth = R0 * math.pow(1 + g, t)
        gross_profit = revenue_with_growth * m
        expenses_with_growth = E0 * math.pow(1 + e, t)
        profit = gross_profit - expenses_with_growth
        
        if profit > 0:
            break
        t += 1
   
    final_revenue = R0 * math.pow(1 + g, t)
    final_gross_profit = final_revenue * m
    final_expenses = E0 * math.pow(1 + e, t)
    final_profit = final_gross_profit - final_expenses

    if t >= max_quarters:
      return {
        'quartersToProfitability': 'Not projected to be profitable within 10 years',
        'yearsToProfit': 'N/A',
        'projectedRevenue': clean_number(final_revenue),
        'projectedGrossProfit': clean_number(final_gross_profit),
        'projectedExpenses': clean_number(final_expenses),
        'projectedProfit': clean_number(final_profit)
    }

    return {
   'quartersToProfitability': t,
   'yearsToProfit': clean_number(t / 4),
   'projectedRevenue': clean_number(final_revenue),
   'projectedGrossProfit': clean_number(final_gross_profit),
   'projectedExpenses': clean_number(final_expenses),
   'projectedProfit': clean_number(final_profit)
}

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/metrics/<ticker>')
def get_metrics(ticker):
    try:
        financial_data = get_quarterly_data(ticker.upper())
        profitability_data = calculate_profitability(financial_data)
        
        response = {
            'inputMetrics': financial_data,
            'profitability': profitability_data
        }
        print(response)
        return jsonify(response)
    except ValueError as e:
        return str(e), 400

if __name__ == '__main__':
    app.run(debug=True)