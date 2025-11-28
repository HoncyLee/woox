# Interactive Dashboard

The WOOX Trading Bot includes a powerful web-based dashboard built with Dash and Plotly for real-time monitoring and control.

## Overview

The dashboard provides a professional interface to:

* Monitor real-time market data and bot performance
* Start and stop the trading bot with one click
* View live charts of price, volume, and orderbook depth
* Track profit/loss and performance metrics
* Emergency close positions
* Generate printable trading reports

## Quick Start

Launch the dashboard:

```bash
python dashboard.py
```

Then open your browser to `http://127.0.0.1:8050`

## Dashboard Features

### Control Panel

The control panel provides buttons for:

* **Start Bot**: Launch the trading bot in the background
* **Stop Bot**: Stop the trading bot gracefully
* **Close Position**: Emergency position close (if position is open)
* **Print Report**: Generate a printable report with all trading records

### Real-time Metrics

Five metric cards display live information:

1. **Current Price**: Latest BTC price with 24h change percentage
2. **Position**: Current position (LONG/SHORT/NONE) and quantity
3. **Unrealized P&L**: Profit/loss for open position in USD and percentage
4. **Total Trades**: Number of completed trades and win rate
5. **Data Points**: Historical data coverage (out of 1440 minutes)

### Interactive Charts

The dashboard includes eleven interactive charts for comprehensive analysis:

1. **Price Chart**: 
   * Main chart showing BTC price over time
   * Subplot showing orderbook depth (bid vs ask)
   * Auto-scaling and zoom capabilities

2. **Orderbook Chart**: 
   * Cumulative orderbook visualization
   * Bid/ask levels with quantities
   * Current spread indicator

3. **Volume Chart**: 
   * Trading volume over time
   * Bar chart format

4. **P&L Chart**: 
   * Profit/loss tracking
   * Cumulative and per-trade view
   * Color-coded positive/negative

5. **RSI Chart**:
   * Relative Strength Index (14-period)
   * Overbought (70) and Oversold (30) threshold lines
   * Momentum tracking

6. **Moving Averages Chart**:
   * SMA 20 (Fast) and SMA 50 (Slow) lines
   * Trend identification and crossover signals

7. **Spread Chart**:
   * Bid-Ask spread percentage over time
   * Liquidity monitoring

8. **Trade Distribution**:
   * Pie chart visualization
   * Win vs. Loss ratio breakdown

9. **Cumulative Return**:
   * Area chart showing total portfolio growth
   * Long-term performance tracking

### Performance Metrics

Performance table shows:

* Total trades (winning/losing breakdown)
* Win rate percentage
* Total P&L in USD
* Sharpe ratio
* Other statistical metrics

### Activity Log

Real-time log viewer displays:

* Recent bot activities
* Color-coded by log level (INFO/WARNING/ERROR)
* Auto-scrolling with latest entries
* Monospace font for easy reading

## Print Reports

### Generate Professional Reports

Click the **🖨️ Print Report** button to generate a printable report:

1. Click the Print Report button in the control panel
2. Use browser's print function (Ctrl+P or Cmd+P)
3. The report will automatically format with:
   * White background for printing
   * Black text for readability
   * Professional table layouts
   * All trading records
   * Performance metrics
   * Current position details
   * Recent price history

### Report Contents

The printed report includes:

* **Header**: Report title and generation timestamp
* **Trading Records**: Table with all trades (timestamp, side, price, quantity, status)
* **Performance Summary**: Total trades, win rate, P&L, Sharpe ratio
* **Current Position**: If open, shows entry price, current price, unrealized P&L
* **Price History**: Recent price data for reference
* **Account Summary**: Bot status and configuration

### Print Optimization

The print layout is optimized with:

* Page-break-inside avoidance for tables
* Proper borders and spacing
* Black text on white background
* Header on each page (browser dependent)
* Charts hidden (data tables shown instead)

## Dark Theme

The dashboard uses a professional dark theme:

* **Background**: Dark grey (#0e1117)
* **Cards**: Slightly lighter dark (#1e2130)
* **Text**: Light colors (#e0e0e0 to #ffffff)
* **Accent**: Purple gradient for headers
* **Charts**: Dark theme with light gridlines

All text is carefully colored for optimal readability on dark backgrounds.

## Customization

### Color Scheme

Edit the CSS in `dashboard.py` to customize colors:

```python
# Find the <style> section in app.index_string
body {
    background-color: #0e1117;  # Main background
    color: #e0e0e0;              # Default text
}

.metric-card {
    background-color: #1e2130;   # Card background
    border-left: 4px solid #667eea;  # Accent border
}
```

### Chart Themes

Charts use Plotly's dark template. To change:

```python
fig.update_layout(
    template='plotly_dark',  # Change to 'plotly', 'plotly_white', etc.
    paper_bgcolor='#1e2130',
    plot_bgcolor='#1e2130',
)
```

### Update Frequency

Default update interval is 1 second. To change:

```python
dcc.Interval(
    id='interval-component',
    interval=1000,  # Change to desired milliseconds
    n_intervals=0
)
```

## Performance Considerations

### Memory Usage

The dashboard stores recent data in memory using `deque` collections:

* **Chart data**: Limited to 500 points (configurable via `maxlen`)
* **Price history**: Limited to 1440 points (24 hours)

To adjust:

```python
chart_data = {
    'timestamps': deque(maxlen=500),  # Change 500 to desired size
    'prices': deque(maxlen=500),
    # ...
}
```

### CPU Usage

The dashboard runs the bot in a separate daemon thread to avoid blocking the UI. The update frequency (1 second) balances:

* Responsiveness: Real-time data updates
* Performance: Low CPU usage
* Network: Reasonable API call rate

For lower-end systems, increase the interval to 2000ms (2 seconds).

## Deployment

### Development Server

The included Flask server is suitable for:

* Local monitoring
* Development and testing
* Single-user access

### Production Deployment

For production use, deploy with Gunicorn:

```bash
pip install gunicorn
gunicorn dashboard:server -w 4 -b 0.0.0.0:8050
```

Key considerations:

* Use nginx as reverse proxy
* Enable HTTPS with SSL certificate
* Add authentication (basic auth or OAuth)
* Set up monitoring and logging
* Use systemd or supervisor for auto-restart

### Network Access

By default, the dashboard listens on all interfaces (`0.0.0.0:8050`), making it accessible:

* Locally: `http://127.0.0.1:8050`
* On network: `http://<your-ip>:8050`

To restrict to localhost only:

```python
app.run(debug=False, port=8050, host='127.0.0.1')
```

## Troubleshooting

### Port Already in Use

If port 8050 is already occupied:

```bash
# Find process using the port
lsof -ti:8050

# Kill the process
kill -9 <pid>

# Or use a different port
app.run(debug=False, port=8051, host='0.0.0.0')
```

### Dashboard Not Loading

Check:

1. Flask server is running (see terminal output)
2. Browser is pointing to correct URL
3. Firewall allows connections on port 8050
4. No JavaScript errors in browser console (F12)

### Charts Not Updating

Verify:

1. Bot is started (click Start Bot button)
2. API credentials are valid (check logs)
3. Internet connection is stable
4. No errors in Activity Log section

### Print Report Empty

Ensure:

1. Bot has been running for some time (data collected)

## 🚀 Quick Start

### Method 1: Use Start Script (Recommended)

```bash
./start_dashboard.sh
```

### Method 2: Direct Python

```bash
python dashboard.py
```

### Method 3: Background Mode

```bash
nohup python dashboard.py > dashboard.log 2>&1 &
```

Then open your browser to: **http://127.0.0.1:8050**

## 📦 Installation

The dashboard requires additional packages:

```bash
pip install dash plotly pandas
```

Or install all requirements:

```bash
pip install -r requirements.txt
```

## 🎯 Usage Guide

### Starting the Bot

1. Open the dashboard in your browser
2. Click **"▶ Start Bot"** button
3. Bot will start in **PAPER mode** by default
4. Watch metrics update in real-time

### Monitoring Performance

- **Price Chart**: Shows BTC/USDT price history with bid/ask depth
- **Order Book**: Visualizes cumulative buy/sell pressure
- **Volume Chart**: Displays trading volume over time
- **P&L Chart**: Tracks your profit/loss in real-time

### Controlling the Bot

- **Stop Bot**: Safely stops the trading bot
- **Close Position**: Immediately closes any open position
- **Status Indicator**: Green (running) / Red (stopped)

### Reading Metrics

| Metric | Description |
|--------|-------------|
| **Current Price** | Latest BTC/USDT price with % change |
| **Position** | Current position (LONG/SHORT/NONE) |
| **Unrealized P&L** | Current profit/loss on open position |
| **Total Trades** | Number of trades executed |
| **Data Points** | Amount of historical data collected |

## 🔧 Configuration

### Change Update Frequency

In `dashboard.py`, modify the interval:

```python
dcc.Interval(id='interval-component', interval=1000, n_intervals=0)  # 1000ms = 1 second
```

### Change Port

```python
app.run_server(debug=True, port=8050, host='0.0.0.0')
```

### Enable Production Mode

```python
app.run_server(debug=False, port=8050, host='0.0.0.0')
```

### Access from Other Devices

1. Find your local IP: `ifconfig | grep "inet "`
2. Dashboard will be available at: `http://YOUR_IP:8050`

## 📊 Dashboard Sections

### 1. Header Section
- **Dashboard Title** with status indicator
- Shows if bot is running (animated green dot) or stopped (red dot)

### 2. Control Panel
- Start/Stop/Close buttons with color coding
- Feedback messages showing operation results

### 3. Metrics Row (5 Cards)
```
┌─────────────┬─────────────┬─────────────┬─────────────┬─────────────┐
│ Price       │ Position    │ P&L         │ Trades      │ Data Points │
│ $50,234.56  │ LONG        │ +$125.00    │ 15          │ 180/1440    │
│ +2.5%       │ 0.001 BTC   │ +2.5%       │ Win: 60%    │ 12.5%       │
└─────────────┴─────────────┴─────────────┴─────────────┴─────────────┘
```

### 4. Main Charts Row
- **Price Chart** (left, 66%): Historical price with bid/ask depth subplot
- **Order Book** (right, 33%): Cumulative depth visualization

### 5. Secondary Charts Row
- **Volume Chart** (left, 50%): Trading volume bars
- **P&L Chart** (right, 50%): Real-time profit/loss tracking

### 6. Bottom Row
- **Performance Table** (left, 50%): Detailed metrics
- **Activity Log** (right, 50%): Live scrolling log

## 🎨 Customization

### Change Colors

Edit the color scheme in the CSS section:

```python
# Primary gradient
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);

# Positive values
color: #00c853;  # Green

# Negative values
color: #ff1744;  # Red

# Neutral values
color: #ffd600;  # Yellow
```

### Add New Charts

Add a new graph component:

```python
html.Div([
    dcc.Graph(id='my-new-chart', config={'displayModeBar': False}),
], style={'width': '100%'}),
```

Create a callback to update it:

```python
@app.callback(
    Output('my-new-chart', 'figure'),
    Input('interval-component', 'n_intervals')
)
def update_my_chart(n):
    # Your chart logic
    return fig
```

## 🔍 Troubleshooting

### Dashboard Won't Start

```bash
# Check if port is already in use
lsof -i :8050

# Kill existing process
kill -9 <PID>
```

### Import Errors

```bash
# Reinstall dependencies
pip install --upgrade dash plotly pandas
```

### No Data Showing

1. Make sure trading bot is started using the "Start Bot" button
2. Wait for data collection (needs a few updates)
3. Check logs for errors

### Charts Not Updating

1. Check browser console for JavaScript errors
2. Verify `interval-component` is set correctly
3. Ensure trader object is initialized

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Dashboard (Dash/Plotly)                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Controls   │  │    Charts    │  │    Metrics   │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                  │                  │              │
│         └──────────────────┴──────────────────┘              │
│                            │                                 │
└────────────────────────────┼─────────────────────────────────┘
                             │
                    ┌────────▼────────┐
                    │  Trade Object   │
                    │  (trader.py)    │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │   WOOX API      │
                    │   (REST/WS)     │
                    └─────────────────┘
```

## 📈 Performance

- **Update Frequency**: 1 second (configurable)
- **Data Points**: Up to 500 per chart (configurable via deque maxlen)
- **Memory Usage**: ~100-200MB
- **CPU Usage**: ~2-5% (on modern hardware)

## 🔐 Security Notes

⚠️ **Important Security Considerations:**

1. **Never expose dashboard to public internet** without authentication
2. **Use firewall** to restrict access: `host='127.0.0.1'` for localhost only
3. **Don't commit** `.config` file with API keys
4. **Use environment variables** for sensitive data
5. **Enable HTTPS** for production deployment

### Adding Authentication (Optional)

```python
import dash_auth

VALID_USERNAME_PASSWORD_PAIRS = {
    'admin': 'secret_password'
}

auth = dash_auth.BasicAuth(
    app,
    VALID_USERNAME_PASSWORD_PAIRS
)
```

## 🚢 Deployment

### Local Network Access

```bash
# Find your IP
ifconfig | grep "inet "

# Start dashboard
python dashboard.py

# Access from other devices: http://YOUR_IP:8050
```

### Production Deployment (Gunicorn)

```bash
# Install Gunicorn
pip install gunicorn

# Run with multiple workers
gunicorn dashboard:server -w 4 -b 0.0.0.0:8050
```

### Docker Deployment

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8050

CMD ["python", "dashboard.py"]
```

Build and run:

```bash
docker build -t woox-dashboard .
docker run -p 8050:8050 woox-dashboard
```

## 📱 Mobile Access

The dashboard is responsive and works on mobile devices:

1. Ensure `host='0.0.0.0'` in `app.run_server()`
2. Connect to same WiFi network
3. Open `http://YOUR_IP:8050` on mobile browser

## 🛠️ Advanced Features

### Export Data

Add a download button:

```python
from dash import dcc

dcc.Download(id="download-data"),

@app.callback(
    Output("download-data", "data"),
    Input("export-btn", "n_clicks"),
    prevent_initial_call=True,
)
def export_data(n_clicks):
    df = pd.DataFrame(chart_data)
    return dcc.send_data_frame(df.to_csv, "trading_data.csv")
```

### Add Alerts

```python
from dash import html

html.Div(id='alert-div'),

@app.callback(
    Output('alert-div', 'children'),
    Input('interval-component', 'n_intervals')
)
def check_alerts(n):
    if trader and trader.current_price:
        if trader.current_price > 60000:
            return html.Div("🚨 Price above $60k!", style={'color': 'red'})
    return ""
```

### Integration with Telegram

```python
import requests

def send_telegram_alert(message):
    bot_token = "YOUR_BOT_TOKEN"
    chat_id = "YOUR_CHAT_ID"
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": message})
```

## 📚 Resources

- [Dash Documentation](https://dash.plotly.com/)
- [Plotly Python](https://plotly.com/python/)
- [Pandas Documentation](https://pandas.pydata.org/)
- [WOOX API Docs](https://docs.woox.io/)

## 🤝 Contributing

Feel free to enhance the dashboard:

1. Add new charts or metrics
2. Improve UI/UX design
3. Add more control features
4. Optimize performance
5. Add unit tests

## 📄 License

BSD 3-Clause License - Same as the main project

## 🆘 Support

If you encounter issues:

1. Check logs: `tail -f trade.log`
2. Check dashboard logs: `tail -f dashboard.log` (if running in background)
3. Verify dependencies: `pip list | grep dash`
4. Test bot separately: `python trade.py`

---

**Happy Trading! 🚀📈**
