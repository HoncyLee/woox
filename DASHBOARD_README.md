# 📊 WOOX Trading Bot Dashboard

Interactive web-based dashboard for monitoring and controlling your WOOX trading bot built with **Dash** and **Plotly**.

![Dashboard](https://img.shields.io/badge/Dash-2.18-blue) ![Plotly](https://img.shields.io/badge/Plotly-5.24-green) ![Python](https://img.shields.io/badge/Python-3.12-yellow)

## ✨ Features

### 📈 Real-Time Monitoring
- **Live Price Chart** with 24-hour history
- **Order Book Visualization** with cumulative depth (20 levels)
- **Trading Volume** bar chart
- **P&L Tracking** with real-time updates

### 🎮 Interactive Controls
- **Start/Stop Bot** with one click
- **Emergency Close Position** button
- **Real-time Status Indicator**
- **Control Feedback** with color-coded messages

### 📊 Performance Metrics
- **Current Price** with % change
- **Position Status** (LONG/SHORT/NONE)
- **Unrealized P&L** with percentage
- **Total Trades** and win rate
- **Data Coverage** (collected data points)
- **Performance Table** (Sharpe ratio, total P&L, etc.)

### 📝 Activity Monitoring
- **Live Activity Log** (last 20 entries)
- **Color-coded Log Levels** (ERROR/WARNING/INFO)
- **Auto-scrolling** log viewer

### 🎨 Beautiful UI
- **Dark Theme** optimized for trading
- **Gradient Colors** and modern design
- **Responsive Layout** works on all screen sizes
- **Animated Status** indicator
- **Professional Charts** with Plotly

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
