import requests
from flask import Flask, render_template, request, redirect, url_for, Blueprint, flash
from datetime import datetime
import pygal
from pygal.style import LightColorizedStyle
import os
import csv

app = Flask(__name__)

def fetch_stock_data(symbol, function):
    API_KEY = "710QOQG2JW67UPY0"
    BASE_URL = "https://www.alphavantage.co/query"
    params = {
        "function": function,
        "symbol": symbol,
        "apikey": API_KEY,
        "datatype": "json"
    }
    if function == "TIME_SERIES_INTRADAY":
        params["interval"] = "60min"
    response = requests.get(BASE_URL, params=params)
    return response.json() if response.status_code == 200 else None

@app.route('/', methods=['GET'])
def index():
    symbols = []
    with open("stocks.csv", newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            symbol = row['Symbol']
            name = row['Name']
            symbols.append((symbol, name))

    return render_template('index.html', symbols=symbols)

@app.route('/results', methods=['POST'])
def show_results():
    symbol = request.form['symbol'].upper()
    chart_type = request.form['chart_type']
    time_series = request.form['time_series']
    start_date = datetime.strptime(request.form['start_date'], "%Y-%m-%d")
    end_date = datetime.strptime(request.form['end_date'], "%Y-%m-%d")

    if start_date > end_date:
        return "<h1>Start date cannot be after end date.</h1>"

    stock_data = fetch_stock_data(symbol, time_series)
    if not stock_data:
        return "<h1>Error loading stock data.</h1>"

    if "Error Message" in stock_data:
        return f"<h1>API Error: {stock_data['Error Message']}</h1>"

    if "Note" in stock_data:
        return f"<h1>API Limit Reached: {stock_data['Note']}</h1>"

    time_series_key = next((k for k in stock_data if "Time Series" in k), None)
    if not time_series_key:
        return "<h1>Unexpected data format.</h1>"

    dates = []
    open_prices = []
    high_prices = []
    low_prices = []
    close_prices = []

    for date_str, values in sorted(stock_data[time_series_key].items()):
        try:
            date = datetime.strptime(date_str.split()[0], "%Y-%m-%d")
            if start_date <= date <= end_date:
                dates.append(date.strftime("%Y-%m-%d"))
                open_prices.append(float(values["1. open"]))
                high_prices.append(float(values["2. high"]))
                low_prices.append(float(values["3. low"]))
                close_prices.append(float(values["4. close"]))
        except:
            continue

    if not close_prices:
        return "<h1>No data in selected date range.</h1>"

    if chart_type == "Bar":
        chart = pygal.Bar(style=LightColorizedStyle, x_label_rotation=45, show_minor_x_labels=True)
    else:
        chart = pygal.Line(style=LightColorizedStyle, x_label_rotation=45, show_minor_x_labels=True)

    chart.title = f"{symbol} Stock Data"
    step = max(1, len(dates) // 10)
    chart.x_labels = dates[::step]
    chart.x_labels_major = dates[::step]

    chart.add("Open", open_prices)
    chart.add("High", high_prices)
    chart.add("Low", low_prices)
    chart.add("Close", close_prices)

    if not os.path.exists("static"):
        os.makedirs("static")

    chart.render_to_file("static/chart.svg")

    return f"""
    <h1>Stock Visualizer</h1>
    <div style="margin: 20px;">
        <p><strong>Symbol:</strong> {symbol}</p>
        <p><strong>Date Range:</strong> {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}</p>
        <object type="image/svg+xml" data="/static/chart.svg" width="90%" height="500"></object>
        <br><a href="/">Visualize Another Stock</a>
    </div>
    """

if __name__ == '__main__':
    app.run(debug=True, port=5051)
