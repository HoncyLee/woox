"""
Interactive Dash Dashboard for WOOX Trading Bot
Real-time monitoring, control, and analysis
"""
import dash
from dash import dcc, html, Input, Output, State, callback_context
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime, timedelta
import threading
import time
from trade import Trade
from account import Account
import config_loader
import logging
from collections import deque
import duckdb
import psutil

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('Dashboard')

# Initialize Dash app
app = dash.Dash(
    __name__,
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
    suppress_callback_exceptions=True
)
app.title = "WOOX Trading Bot Monitor"

# Global variables
trader = None
trader_thread = None
is_running = False
performance_metrics = {
    'total_trades': 0,
    'winning_trades': 0,
    'losing_trades': 0,
    'total_pnl': 0.0,
    'win_rate': 0.0,
    'sharpe_ratio': 0.0
}

# Store recent data for charts
chart_data = {
    'timestamps': deque(maxlen=500),
    'prices': deque(maxlen=500),
    'volumes': deque(maxlen=500),
    'pnl': deque(maxlen=500),
    'bid_depth': deque(maxlen=500),
    'ask_depth': deque(maxlen=500),
    'spread': deque(maxlen=500),
    'rsi': deque(maxlen=500),
    'ma_short': deque(maxlen=500),
    'ma_long': deque(maxlen=500)
}

# Custom CSS
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <script>
            var serverDownAlertShown = false;
            setInterval(function() {
                fetch('/', { method: 'HEAD' })
                    .then(function(response) {
                        if (response.ok) {
                            if (serverDownAlertShown) {
                                // Server came back
                                serverDownAlertShown = false;
                                document.body.style.opacity = "1";
                                document.body.style.pointerEvents = "auto";
                                console.log("Server connection restored");
                            }
                        }
                    })
                    .catch(function(error) {
                        if (!serverDownAlertShown) {
                            alert('⚠️ CRITICAL: Connection to server lost! The bot process has stopped.');
                            serverDownAlertShown = true;
                            document.body.style.opacity = "0.5";
                            document.body.style.pointerEvents = "none";
                        }
                    });
            }, 2000);
        </script>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background-color: #0e1117;
                color: #e0e0e0;
                margin: 0;
                padding: 0;
            }
            .container {
                max-width: 1800px;
                margin: 0 auto;
                padding: 20px;
            }
            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 20px;
                border-radius: 10px;
                margin-bottom: 20px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }
            .metric-card {
                background-color: #1e2130;
                border-radius: 8px;
                padding: 15px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.2);
                border-left: 4px solid #667eea;
            }
            .metric-value {
                font-size: 24px;
                font-weight: bold;
                color: #ffffff;
                margin: 5px 0;
            }
            .metric-label {
                font-size: 14px;
                color: #b0b0b0;
                text-transform: uppercase;
                font-weight: 500;
            }
            .metric-change {
                font-size: 14px;
                margin-top: 5px;
            }
            .positive { color: #00c853; }
            .negative { color: #ff1744; }
            .neutral { color: #ffd600; }
            .control-button {
                padding: 12px 24px;
                margin: 5px;
                border: none;
                border-radius: 6px;
                font-size: 16px;
                font-weight: bold;
                cursor: pointer;
                transition: all 0.3s;
                box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            }
            .start-btn {
                background: linear-gradient(135deg, #00c853 0%, #00e676 100%);
                color: white;
            }
            .stop-btn {
                background: linear-gradient(135deg, #ff1744 0%, #ff5252 100%);
                color: white;
            }
            .close-btn {
                background: linear-gradient(135deg, #ffd600 0%, #ffea00 100%);
                color: #1a1a1a;
                font-weight: bold;
            }
            .print-btn {
                background: linear-gradient(135deg, #2196F3 0%, #42A5F5 100%);
                color: white;
            }
            .control-button:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 8px rgba(0,0,0,0.3);
            }
            @media print {
                body {
                    background-color: white !important;
                    color: black !important;
                }
                .no-print {
                    display: none !important;
                }
                .print-only {
                    display: block !important;
                }
                .header {
                    background: white !important;
                    color: black !important;
                    border: 2px solid #667eea;
                }
                .metric-card {
                    background-color: white !important;
                    color: black !important;
                    border: 1px solid #ddd;
                    page-break-inside: avoid;
                }
                .metric-value {
                    color: black !important;
                }
                .metric-label {
                    color: #555 !important;
                }
                h1, h2, h3, h4, h5, h6 {
                    color: black !important;
                }
                table {
                    border-collapse: collapse;
                    width: 100%;
                }
                table td, table th {
                    border: 1px solid #ddd;
                    padding: 8px;
                    color: black !important;
                }
                table th {
                    background-color: #f0f0f0 !important;
                }
            }
            .status-indicator {
                display: inline-block;
                width: 12px;
                height: 12px;
                border-radius: 50%;
                margin-right: 8px;
            }
            .status-running { background-color: #00c853; animation: pulse 2s infinite; }
            .status-stopped { background-color: #ff1744; }
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.5; }
            }
            .print-only {
                display: none;
            }
            /* Modal Styles */
            .modal {
                display: none;
                position: fixed;
                z-index: 1000;
                left: 0;
                top: 0;
                width: 100%;
                height: 100%;
                overflow: auto;
                background-color: rgba(0,0,0,0.5);
            }
            .modal-content {
                background-color: #1e2130;
                margin: 5% auto;
                padding: 20px;
                border: 1px solid #667eea;
                border-radius: 10px;
                width: 80%;
                max-width: 1200px;
                color: white;
                box-shadow: 0 4px 8px rgba(0,0,0,0.2);
                font-size: 11px;
            }
            .close {
                color: #aaa;
                float: right;
                font-size: 28px;
                font-weight: bold;
            }
            .close:hover,
            .close:focus {
                color: white;
                text-decoration: none;
                cursor: pointer;
            }
            .form-group {
                margin-bottom: 15px;
            }
            .form-label {
                display: block;
                margin-bottom: 5px;
                color: #a0a0a0;
                font-size: 11px;
            }
            .form-input {
                width: 100%;
                padding: 8px;
                border-radius: 4px;
                border: 1px solid #444;
                background-color: #2d3142;
                color: white;
                font-size: 11px;
            }
            /* Dropdown Dark Mode */
            .Select-control {
                background-color: #2d3142 !important;
                border: 1px solid #444 !important;
                color: white !important;
                font-size: 11px !important;
            }
            .Select-value-label {
                color: white !important;
            }
            .Select-menu-outer {
                background-color: #2d3142 !important;
                border: 1px solid #444 !important;
            }
            .Select-option {
                background-color: #2d3142 !important;
                color: white !important;
            }
            .Select-option:hover {
                background-color: #667eea !important;
            }
            .Select-placeholder {
                color: #a0a0a0 !important;
            }
            .Select-arrow-zone {
                color: white !important;
            }
            .Select-clear-zone {
                color: white !important;
            }
            .chart-card {
                background-color: #1e2130;
                border-radius: 10px;
                padding: 20px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                overflow: hidden;
            }
            /* Neon Mode Indicators */
            @keyframes neon-green {
                0% { box-shadow: 0 0 5px #00ff00, 0 0 10px #00ff00; opacity: 1; }
                50% { box-shadow: 0 0 2px #00ff00, 0 0 5px #00ff00; opacity: 0.7; }
                100% { box-shadow: 0 0 5px #00ff00, 0 0 10px #00ff00; opacity: 1; }
            }
            @keyframes neon-orange {
                0% { box-shadow: 0 0 5px #ff9900, 0 0 10px #ff9900; opacity: 1; }
                50% { box-shadow: 0 0 2px #ff9900, 0 0 5px #ff9900; opacity: 0.7; }
                100% { box-shadow: 0 0 5px #ff9900, 0 0 10px #ff9900; opacity: 1; }
            }
            .mode-indicator {
                padding: 5px 15px;
                border-radius: 15px;
                font-weight: bold;
                text-transform: uppercase;
                font-size: 12px;
                letter-spacing: 1px;
                transition: all 0.5s ease;
                display: inline-block;
            }
            .mode-live {
                color: #00ff00;
                border: 1px solid #00ff00;
                animation: neon-green 2s infinite alternate;
            }
            .mode-paper {
                color: #ff9900;
                border: 1px solid #ff9900;
                animation: neon-orange 2s infinite alternate;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# Layout
app.layout = html.Div([
    # Header
    html.Div([
        html.H1("🚀 WOOX Trading Bot Dashboard", 
                style={'color': 'white', 'margin': '0', 'display': 'inline-block'}),
        html.Div(id='status-indicator', 
                 style={'float': 'right', 'color': 'white', 'fontSize': '18px'}),
    ], className='header'),
    
    # Control Panel
    html.Div([
        html.Div([
            html.H3("Control Panel", style={'color': '#ffffff', 'margin': '0', 'display': 'inline-block'}),
            html.Div(id='mode-indicator', style={'float': 'right'})
        ], style={'marginBottom': '15px'}),
        
        html.Div([
            html.Button("▶ Start Bot", id='start-btn', n_clicks=0, className='control-button start-btn'),
            html.Button("⏸ Stop Bot", id='stop-btn', n_clicks=0, className='control-button stop-btn'),
            html.Button("❌ Close Position", id='close-btn', n_clicks=0, className='control-button close-btn'),
            html.Button("⚙️ Config", id='config-btn', n_clicks=0, className='control-button', style={'backgroundColor': '#607d8b', 'color': 'white'}),
            html.Button("🖨️ Print Report", id='print-btn', n_clicks=0, className='control-button print-btn'),
            html.Div(id='control-feedback', style={'color': '#ffffff', 'marginTop': '10px', 'fontSize': '14px'})
        ]),
    ], style={'backgroundColor': '#1e2130', 'padding': '20px', 'borderRadius': '10px', 'marginBottom': '20px'}, className='no-print'),
    
    # Metrics Row
    html.Div([
        # Price Metric
        html.Div([
            html.Div("Current Price", id='price-label', className='metric-label'),
            html.Div(id='price-metric', className='metric-value'),
            html.Div(id='price-change', className='metric-change'),
        ], className='metric-card', style={'flex': '1'}),
        
        # Position Metric
        html.Div([
            html.Div("Position", className='metric-label'),
            html.Div(id='position-metric', className='metric-value'),
            html.Div(id='position-size', className='metric-change'),
        ], className='metric-card', style={'flex': '1'}),
        
        # P&L Metric
        html.Div([
            html.Div("Unrealized P&L", className='metric-label'),
            html.Div(id='pnl-metric', className='metric-value'),
            html.Div(id='pnl-percent', className='metric-change'),
        ], className='metric-card', style={'flex': '1'}),
        
        # Total Trades
        html.Div([
            html.Div("Total Trades", className='metric-label'),
            html.Div(id='trades-metric', className='metric-value'),
            html.Div(id='win-rate', className='metric-change'),
        ], className='metric-card', style={'flex': '1'}),
        
        # Account Balance
        html.Div([
            html.Div("Account Balance", className='metric-label'),
            html.Div(id='balance-metric', className='metric-value'),
            html.Div(id='monthly-return', className='metric-change'),
        ], className='metric-card', style={'flex': '1'}),
    ], style={'display': 'flex', 'gap': '10px', 'marginBottom': '20px'}),
    
    # Strategy Info Row
    html.Div([
        # Entry Strategy
        html.Div([
            html.Div("Entry Strategy", className='metric-label'),
            html.Div(id='entry-strategy-metric', className='metric-value', style={'fontSize': '18px'}),
        ], className='metric-card', style={'flex': '1'}),
        
        # Exit Strategy
        html.Div([
            html.Div("Exit Strategy", className='metric-label'),
            html.Div(id='exit-strategy-metric', className='metric-value', style={'fontSize': '18px'}),
        ], className='metric-card', style={'flex': '1'}),
        
        # Take Profit
        html.Div([
            html.Div("Take Profit", className='metric-label'),
            html.Div(id='take-profit-metric', className='metric-value', style={'color': '#00c853'}),
        ], className='metric-card', style={'flex': '1'}),
        
        # Stop Loss
        html.Div([
            html.Div("Stop Loss", className='metric-label'),
            html.Div(id='stop-loss-metric', className='metric-value', style={'color': '#ff1744'}),
        ], className='metric-card', style={'flex': '1'}),
    ], style={'display': 'flex', 'gap': '10px', 'marginBottom': '20px'}),

    # System Monitor Row
    html.Div([
        # CPU Usage
        html.Div([
            html.Div("CPU Usage", className='metric-label'),
            html.Div(id='cpu-usage-metric', className='metric-value'),
            dcc.Graph(id='cpu-gauge', config={'displayModeBar': False}, style={'height': '100px', 'marginTop': '-20px'}),
        ], className='metric-card', style={'flex': '1'}),
        
        # Memory Usage
        html.Div([
            html.Div("Memory Usage", className='metric-label'),
            html.Div(id='memory-usage-metric', className='metric-value'),
            dcc.Graph(id='memory-gauge', config={'displayModeBar': False}, style={'height': '100px', 'marginTop': '-20px'}),
        ], className='metric-card', style={'flex': '1'}),
    ], style={'display': 'flex', 'gap': '10px', 'marginBottom': '20px'}),

    # Performance & P&L Row
    html.Div([
        html.Div([
            html.H3("Performance Metrics", style={'color': '#ffffff', 'marginBottom': '15px'}),
            html.Div(id='performance-table', style={'color': '#e0e0e0'}),
        ], style={'flex': '1', 'backgroundColor': '#1e2130', 'padding': '20px', 'borderRadius': '10px'}),
        
        html.Div([
            dcc.Graph(id='pnl-chart', config={'displayModeBar': False}),
        ], className='chart-card', style={'flex': '2'}),
    ], className='no-print', style={'display': 'flex', 'gap': '20px', 'marginBottom': '20px'}),

    # Main Charts Row
    html.Div([
        html.Div([
            dcc.Graph(id='price-chart', config={'displayModeBar': False}),
        ], className='chart-card', style={'flex': '2'}),
        
        html.Div([
            dcc.Graph(id='orderbook-chart', config={'displayModeBar': False}),
        ], className='chart-card', style={'flex': '1'}),
    ], className='no-print', style={'display': 'flex', 'gap': '20px', 'marginBottom': '20px'}),
    
    # Technical Analysis Charts Row
    html.Div([
        html.Div([
            dcc.Graph(id='rsi-chart', config={'displayModeBar': False}),
        ], className='chart-card', style={'width': '33%', 'display': 'inline-block'}),
        
        html.Div([
            dcc.Graph(id='ma-chart', config={'displayModeBar': False}),
        ], className='chart-card', style={'width': '33%', 'display': 'inline-block'}),
        
        html.Div([
            dcc.Graph(id='spread-chart', config={'displayModeBar': False}),
        ], className='chart-card', style={'width': '33%', 'display': 'inline-block'}),
    ], className='no-print', style={'marginBottom': '20px'}),
    
    # Trade Analytics Row
    html.Div([
        html.Div([
            dcc.Graph(id='trade-distribution-chart', config={'displayModeBar': False}),
        ], className='chart-card', style={'width': '50%', 'display': 'inline-block'}),
        
        html.Div([
            dcc.Graph(id='cumulative-return-chart', config={'displayModeBar': False}),
        ], className='chart-card', style={'width': '50%', 'display': 'inline-block'}),
    ], className='no-print', style={'marginBottom': '20px'}),

    # Trading Record Row
    html.Div([
        html.Div([
            html.H3("Trading Record", style={'color': '#ffffff', 'marginBottom': '15px'}),
            html.Div(id='trading-record-table', style={'overflowX': 'auto', 'maxHeight': '300px', 'overflowY': 'auto'}),
        ], style={'width': '100%', 'display': 'inline-block', 'backgroundColor': '#1e2130', 
                  'padding': '20px', 'borderRadius': '10px', 'verticalAlign': 'top'}),
    ], className='no-print', style={'marginBottom': '20px'}),

    # Activity Log Row
    html.Div([
        html.Div([
            html.H3("Recent Activity Log", style={'color': '#ffffff', 'marginBottom': '15px'}),
            html.Div(id='activity-log', style={'height': '200px', 'overflowY': 'scroll', 
                                                'backgroundColor': '#0e1117', 'padding': '10px',
                                                'borderRadius': '5px', 'fontFamily': 'monospace',
                                                'fontSize': '12px', 'color': '#a0a0a0'}),
        ], style={'width': '100%', 'display': 'inline-block', 'backgroundColor': '#1e2130', 
                  'padding': '20px', 'borderRadius': '10px', 'verticalAlign': 'top'}),
    ], className='no-print', style={'marginBottom': '20px'}),
    
    # Detailed Report Section (visible only when printing)
    html.Div([
        html.Div([
            html.H2("📊 WOOX Trading Bot - Detailed Report", 
                    style={'textAlign': 'center', 'marginBottom': '20px', 'color': '#667eea', 'borderBottom': '3px solid #667eea', 'paddingBottom': '10px'}),
            html.P(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 
                   style={'textAlign': 'center', 'color': '#666', 'fontSize': '14px', 'marginBottom': '30px'}),
            
            # Trading Records Section
            html.Div(id='print-trading-records'),
            
            # Account Summary Section
            html.Div(id='print-account-summary'),
            
        ], style={'backgroundColor': 'white', 'padding': '40px', 'maxWidth': '1200px', 'margin': '0 auto'})
    ], style={'display': 'none'}, className='print-only'),
    
    # Auto-refresh interval
    dcc.Interval(id='interval-component', interval=1000, n_intervals=0),  # Update every second
    
    # Hidden div to store logs
    html.Div(id='log-store', style={'display': 'none'}),
    
    # Store to track config loading state
    dcc.Store(id='config-loaded-flag', data=False),

    # Config Modal
    html.Div(id='config-modal', className='modal', children=[
        html.Div(className='modal-content', children=[
            html.Span("×", id='close-config-btn', className='close'),
            html.H2("⚙️ Configuration Settings"),
            
            html.Div(style={'display': 'flex', 'gap': '30px', 'flexWrap': 'wrap'}, children=[
                # Column 1: General
                html.Div(style={'flex': '1', 'minWidth': '300px'}, children=[
                    html.H3("General Settings", style={'color': '#2196F3', 'borderBottom': '1px solid #444', 'paddingBottom': '10px', 'marginTop': '0'}),
                    
                    html.Div(className='form-group', children=[
                        html.Label("Trading Mode", className='form-label'),
                        dcc.Dropdown(
                            id='conf-trade-mode',
                            options=[
                                {'label': 'Paper Trading', 'value': 'paper'},
                                {'label': 'Live Trading', 'value': 'live'}
                            ],
                            className='form-input',
                        )
                    ]),
                    
                    html.Div(className='form-group', children=[
                        html.Label("Trade Type", className='form-label'),
                        dcc.Dropdown(
                            id='conf-trade-type',
                            options=[
                                {'label': 'Future (Perpetual)', 'value': 'future'},
                                {'label': 'Spot', 'value': 'spot'}
                            ],
                            className='form-input',
                        ),
                        html.Div(id='spot-warning', style={'color': '#ff9900', 'fontSize': '12px', 'marginTop': '5px'})
                    ]),
                    
                    html.Div(className='form-group', children=[
                        html.Label("Symbol", className='form-label'),
                        dcc.Dropdown(id='conf-symbol', className='form-input')
                    ]),
                    
                    html.Div(className='form-group', children=[
                        html.Label("Position Size Type", className='form-label'),
                        dcc.Dropdown(
                            id='conf-pos-size-type',
                            options=[
                                {'label': 'Fixed Value (USDT)', 'value': 'value'},
                                {'label': 'Percentage of Balance (%)', 'value': 'percentage'},
                                {'label': 'Fixed Quantity (Asset)', 'value': 'quantity'}
                            ],
                            className='form-input',
                        )
                    ]),

                    html.Div(className='form-group', children=[
                        html.Label("Position Size Value", id='pos-size-value-label', className='form-label'),
                        dcc.Input(id='conf-pos-size-value', type='number', className='form-input')
                    ]),

                    html.Div(className='form-group', children=[
                        html.Label("Max Open Position", className='form-label'),
                        dcc.Input(id='conf-max-pos', type='number', min=1, step=1, className='form-input')
                    ]),
                ]),

                # Column 2: Signal
                html.Div(style={'flex': '1', 'minWidth': '300px'}, children=[
                    html.H3("Signal Strategy", style={'color': '#00e676', 'borderBottom': '1px solid #444', 'paddingBottom': '10px', 'marginTop': '0'}),
                    
                    html.Div(className='form-group', children=[
                        html.Label("Entry Strategy", className='form-label'),
                        dcc.Dropdown(
                            id='conf-strategy',
                            options=[
                                {'label': 'MA Crossover', 'value': 'ma_crossover'},
                                {'label': 'RSI', 'value': 'rsi'},
                                {'label': 'Bollinger Bands', 'value': 'bollinger_bands'}
                            ],
                            className='form-input',
                        )
                    ]),
                    
                    html.Div(style={'border': '1px solid #444', 'padding': '10px', 'borderRadius': '5px', 'marginTop': '10px'}, children=[
                        html.H4("MA Settings", style={'marginTop': '0', 'color': '#b0b0b0', 'fontSize': '12px'}),
                        
                        html.Div(className='form-group', children=[
                            html.Label("Timeframe", className='form-label'),
                            dcc.Dropdown(
                                id='conf-ma-timeframe',
                                options=[
                                    {'label': '1 Second', 'value': 1},
                                    {'label': '1 Minute', 'value': 60},
                                    {'label': '5 Minutes', 'value': 300},
                                    {'label': '15 Minutes', 'value': 900},
                                    {'label': '1 Hour', 'value': 3600}
                                ],
                                className='form-input',
                            )
                        ]),

                        html.Div(className='form-group', children=[
                            html.Label("Short MA Period", className='form-label'),
                            dcc.Input(id='conf-short-ma', type='number', className='form-input')
                        ]),
                        
                        html.Div(className='form-group', children=[
                            html.Label("Long MA Period", className='form-label'),
                            dcc.Input(id='conf-long-ma', type='number', className='form-input')
                        ]),

                        html.Div(className='form-group', children=[
                            html.Label("Threshold % (Diff)", className='form-label'),
                            dcc.Input(id='conf-ma-threshold', type='number', step=0.1, className='form-input')
                        ]),
                    ]),

                    html.Div(style={'border': '1px solid #444', 'padding': '10px', 'borderRadius': '5px', 'marginTop': '10px'}, children=[
                        html.H4("RSI Settings", style={'marginTop': '0', 'color': '#b0b0b0', 'fontSize': '12px'}),
                        
                        html.Div(className='form-group', children=[
                            html.Label("Timeframe", className='form-label'),
                            dcc.Dropdown(
                                id='conf-rsi-timeframe',
                                options=[
                                    {'label': '1 Second', 'value': 1},
                                    {'label': '1 Minute', 'value': 60},
                                    {'label': '5 Minutes', 'value': 300},
                                    {'label': '15 Minutes', 'value': 900},
                                    {'label': '1 Hour', 'value': 3600}
                                ],
                                className='form-input',
                            )
                        ]),

                        html.Div(className='form-group', children=[
                            html.Label("Period", className='form-label'),
                            dcc.Input(id='conf-rsi-period', type='number', className='form-input')
                        ]),
                    ]),
                ]),

                # Column 3: Risk Control
                html.Div(style={'flex': '1', 'minWidth': '300px'}, children=[
                    html.H3("Risk Control", style={'color': '#ff5252', 'borderBottom': '1px solid #444', 'paddingBottom': '10px', 'marginTop': '0'}),
                    
                    html.Div(className='form-group', children=[
                        html.Label("Stop Loss %", className='form-label'),
                        dcc.Input(id='conf-sl', type='number', step=0.1, className='form-input')
                    ]),
                    
                    html.Div(className='form-group', children=[
                        html.Label("Take Profit %", className='form-label'),
                        dcc.Input(id='conf-tp', type='number', step=0.1, className='form-input')
                    ]),
                ]),
            ]),
            
            html.Div(style={'marginTop': '30px', 'textAlign': 'right', 'borderTop': '1px solid #444', 'paddingTop': '20px'}, children=[
                html.Button("Cancel", id='cancel-config-btn', className='control-button', style={'backgroundColor': '#757575', 'marginRight': '10px'}),
                html.Button("Save Changes", id='save-config-btn', className='control-button', style={'backgroundColor': '#00c853'})
            ]),
            
            html.Div(id='config-feedback', style={'marginTop': '10px', 'fontWeight': 'bold'})
        ])
    ]),

    # Alert Dialog
    dcc.ConfirmDialog(
        id='alert-dialog',
        message='⚠️ Warning: The trading bot has stopped unexpectedly! Please check the logs.',
    ),
    
], className='container', style={'backgroundColor': '#0e1117', 'minHeight': '100vh', 'padding': '20px'})


# Callback: Control buttons
@app.callback(
    Output('control-feedback', 'children'),
    Output('control-feedback', 'style'),
    Input('start-btn', 'n_clicks'),
    Input('stop-btn', 'n_clicks'),
    Input('close-btn', 'n_clicks'),
    Input('print-btn', 'n_clicks'),
    prevent_initial_call=True
)
def control_bot(start_clicks, stop_clicks, close_clicks, print_clicks):
    global trader, trader_thread, is_running
    
    ctx = callback_context
    if not ctx.triggered:
        return "", {}
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    try:
        if button_id == 'start-btn':
            if not is_running:
                # Load config to get trade mode
                config = config_loader.load_config()
                trade_mode = config.get('TRADE_MODE', 'paper')
                
                trader = Trade(trade_mode=trade_mode)
                is_running = True
                trader_thread = threading.Thread(target=trader.run, daemon=True)
                trader_thread.start()
                logger.info(f"Trading bot started in {trade_mode} mode")
                return f"✅ Bot started successfully ({trade_mode})", {'color': '#00c853'}
            else:
                return "⚠️ Bot is already running", {'color': '#ffd600'}
        
        elif button_id == 'stop-btn':
            if is_running and trader:
                trader.stop()
                is_running = False
                logger.info("Trading bot stopped")
                return "✅ Bot stopped successfully", {'color': '#00c853'}
            else:
                return "⚠️ Bot is not running", {'color': '#ffd600'}
        
        elif button_id == 'close-btn':
            if trader and trader.current_position:
                success = trader.closePosition(trader.current_price)
                if success:
                    return "✅ Position closed successfully", {'color': '#00c853'}
                else:
                    return "❌ Failed to close position", {'color': '#ff1744'}
            else:
                return "⚠️ No open position", {'color': '#ffd600'}
        
        elif button_id == 'print-btn':
            # Trigger browser print dialog using JavaScript
            return html.Div([
                "📄 Preparing report... Please use Ctrl+P (Cmd+P on Mac) or browser print to print the report.",
                dcc.Store(id='trigger-print', data={'print': True})
            ]), {'color': '#2196F3'}
    
    except Exception as e:
        logger.error(f"Control error: {str(e)}")
        return f"❌ Error: {str(e)}", {'color': '#ff1744'}
    
    return "", {}


# Callback: Update status indicator
@app.callback(
    Output('status-indicator', 'children'),
    Output('mode-indicator', 'children'),
    Output('mode-indicator', 'className'),
    Output('alert-dialog', 'displayed'),
    Input('interval-component', 'n_intervals')
)
def update_status(n):
    global is_running, trader, trader_thread
    
    show_alert = False
    
    # Check for unexpected stop
    if is_running and trader_thread and not trader_thread.is_alive():
        is_running = False
        logger.warning("Trading bot thread died unexpectedly")
        show_alert = True
    
    # Status indicator logic
    if is_running:
        status_child = html.Span([
            html.Span(className='status-indicator status-running'),
            "Running"
        ])
    else:
        status_child = html.Span([
            html.Span(className='status-indicator status-stopped'),
            "Stopped"
        ])
        
    # Mode indicator logic
    mode = 'paper'
    if trader:
        mode = trader.trade_mode
    else:
        try:
            config = config_loader.load_config()
            mode = config.get('TRADE_MODE', 'paper')
        except:
            mode = 'paper'
            
    if mode == 'live':
        mode_text = "LIVE MODE"
        mode_class = "mode-indicator mode-live"
    else:
        mode_text = "PAPER MODE"
        mode_class = "mode-indicator mode-paper"
        
    return status_child, mode_text, mode_class, show_alert


# Callback: Update metrics
@app.callback(
    Output('price-label', 'children'),
    Output('price-metric', 'children'),
    Output('price-change', 'children'),
    Output('price-change', 'className'),
    Output('position-metric', 'children'),
    Output('position-size', 'children'),
    Output('pnl-metric', 'children'),
    Output('pnl-percent', 'children'),
    Output('pnl-percent', 'className'),
    Output('trades-metric', 'children'),
    Output('win-rate', 'children'),
    Output('balance-metric', 'children'),
    Output('monthly-return', 'children'),
    Input('interval-component', 'n_intervals')
)
def update_metrics(n):
    global trader, chart_data, performance_metrics
    
    if not trader or not is_running:
        return ("Current Price", "--", "No data", "metric-change neutral", 
                "NONE", "No position", 
                "$0.00", "0.0%", "metric-change neutral",
                "0", "Win Rate: 0%",
                "$0.00", "Return: 0.0%")
    
    try:
        # Price metrics
        symbol_label = "Current Price"
        if trader and trader.symbol:
            # Format symbol: PERP_BTC_USDT -> BTC/USDT
            s = trader.symbol.replace('PERP_', '').replace('SPOT_', '').replace('_', '/')
            symbol_label = f"{s}"

        price = trader.current_price or 0
        price_str = f"${price:,.2f}" if price else "--"
        
        # Calculate price change (24h)
        price_change = 0
        price_change_pct = 0
        used_24h_stats = False
        
        if trader and hasattr(trader, 'stats_24h') and trader.stats_24h:
            try:
                # Ensure we are using stats for the correct symbol
                stats_symbol = trader.stats_24h.get('symbol', '')
                if stats_symbol == trader.symbol:
                    open_24h = float(trader.stats_24h.get('24h_open', 0))
                    if open_24h > 0:
                        price_change = price - open_24h
                        price_change_pct = (price_change / open_24h) * 100
                        used_24h_stats = True
            except (ValueError, TypeError):
                pass
        
        # Fallback to session change if 24h stats not available
        if not used_24h_stats and len(chart_data['prices']) > 1:
            old_price = list(chart_data['prices'])[0]
            if old_price:
                price_change = price - old_price
                price_change_pct = (price_change / old_price) * 100
        
        price_change_str = f"{'+' if price_change >= 0 else ''}{price_change:.2f} ({price_change_pct:+.2f}%)"
        price_change_class = "metric-change positive" if price_change >= 0 else "metric-change negative"
        
        # Position metrics
        position = trader.current_position
        if position and isinstance(position, dict) and 'side' in position:
            position_side = position.get('side', 'NONE').upper()
            position_qty = position.get('quantity', 0)
            position_str = f"{position_side}"
            position_size_str = f"{position_qty:.6f} BTC" # Assuming BTC for now, should be dynamic
            
            # Calculate P&L
            entry_price = position.get('entry_price', 0)
            current_price = price
            if entry_price > 0:
                if position_side == 'LONG':
                    pnl = (current_price - entry_price) * position_qty
                else:
                    pnl = (entry_price - current_price) * position_qty
                
                pnl_pct = (pnl / (entry_price * position_qty)) * 100 if position_qty > 0 else 0
            else:
                pnl = 0
                pnl_pct = 0

            pnl_str = f"${pnl:,.2f}"
            pnl_pct_str = f"{pnl_pct:+.2f}%"
            pnl_class = "metric-change positive" if pnl >= 0 else "metric-change negative"
        else:
            position_str = "NONE"
            position_size_str = "No position"
            pnl_str = "$0.00"
            pnl_pct_str = "0.0%"
            pnl_class = "metric-change neutral"
        
        # Trade metrics
        trades_count = performance_metrics['total_trades']
        win_rate = performance_metrics['win_rate']
        win_rate_str = f"Win Rate: {win_rate:.1f}%"
        
        # Account Balance & Monthly Return
        account = Account(trade_mode=trader.trade_mode)
        balance_val = "$0.00"
        return_val = "Return: 0.0%"
        
        if trader.trade_mode == 'paper':
            summary = account.get_transaction_summary()
            net_pnl = summary.get('net_pnl', 0.0)
            initial_balance = 100000.0
            current_balance = initial_balance + net_pnl
            balance_val = f"${current_balance:,.2f}"
            roi = (net_pnl / initial_balance) * 100
            return_val = f"Return: {roi:+.2f}%"
        else:
            # Live mode
            acct_info = account.get_account_info()
            if acct_info and 'totalCollateral' in acct_info:
                 total = float(acct_info.get('totalCollateral', 0))
                 balance_val = f"${total:,.2f}"
                 return_val = "Live Balance"
            else:
                 # Fallback to balance check if account info fails
                 api_bal = account.get_api_balance()
                 if api_bal:
                     # Try to sum up holdings if totalCollateral not available
                     balance_val = "Check Logs"
                     return_val = "Partial Data"
                 else:
                     balance_val = "N/A"
                     return_val = "Check API"
        
        # Update chart data
        if price:
            chart_data['timestamps'].append(datetime.now())
            chart_data['prices'].append(price)
            chart_data['volumes'].append(trader.current_volume or 0)
            
            if trader.orderbook:
                chart_data['bid_depth'].append(trader.orderbook.get('bid_depth', 0))
                chart_data['ask_depth'].append(trader.orderbook.get('ask_depth', 0))
        
        return (symbol_label, price_str, price_change_str, price_change_class,
                position_str, position_size_str,
                pnl_str, pnl_pct_str, pnl_class,
                str(trades_count), win_rate_str,
                balance_val, return_val)
    
    except Exception as e:
        logger.error(f"Error updating metrics: {str(e)}")
        return ("Error", "Error", "Error", "metric-change neutral",
                "Error", "Error",
                "Error", "Error", "metric-change neutral",
                "Error", "Error",
                "Error", "Error")


# Callback: Update Strategy Info
@app.callback(
    Output('entry-strategy-metric', 'children'),
    Output('exit-strategy-metric', 'children'),
    Output('take-profit-metric', 'children'),
    Output('stop-loss-metric', 'children'),
    Input('interval-component', 'n_intervals')
)
def update_strategy_info(n):
    try:
        # Load config (it's fast enough)
        config = config_loader.load_config()
        
        entry_strat = config.get('ENTRY_STRATEGY', 'ma_crossover').replace('_', ' ').title()
        exit_strat = config.get('EXIT_STRATEGY', 'ma_crossover').replace('_', ' ').title()
        tp_pct = float(config.get('TAKE_PROFIT_PCT', 5.0))
        sl_pct = float(config.get('STOP_LOSS_PCT', 2.0))
        
        return (
            entry_strat,
            exit_strat,
            f"{tp_pct}%",
            f"{sl_pct}%"
        )
    except Exception as e:
        logger.error(f"Error updating strategy info: {str(e)}")
        return ("--", "--", "--", "--")


# Callback: Update System Metrics
@app.callback(
    Output('cpu-usage-metric', 'children'),
    Output('cpu-gauge', 'figure'),
    Output('memory-usage-metric', 'children'),
    Output('memory-gauge', 'figure'),
    Input('interval-component', 'n_intervals')
)
def update_system_metrics(n):
    try:
        # Get CPU usage
        cpu_percent = psutil.cpu_percent(interval=None)
        
        # Get Memory usage
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        # Create CPU Gauge
        cpu_fig = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = cpu_percent,
            domain = {'x': [0, 1], 'y': [0, 1]},
            gauge = {
                'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "white"},
                'bar': {'color': "#667eea"},
                'bgcolor': "rgba(0,0,0,0)",
                'borderwidth': 2,
                'bordercolor': "#444",
                'steps': [
                    {'range': [0, 50], 'color': "rgba(0, 200, 83, 0.3)"},
                    {'range': [50, 80], 'color': "rgba(255, 214, 0, 0.3)"},
                    {'range': [80, 100], 'color': "rgba(255, 23, 68, 0.3)"}
                ],
            }
        ))
        cpu_fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font={'color': "white"},
            margin={'t': 0, 'b': 0, 'l': 20, 'r': 20},
            height=100
        )
        
        # Create Memory Gauge
        mem_fig = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = memory_percent,
            domain = {'x': [0, 1], 'y': [0, 1]},
            gauge = {
                'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "white"},
                'bar': {'color': "#764ba2"},
                'bgcolor': "rgba(0,0,0,0)",
                'borderwidth': 2,
                'bordercolor': "#444",
                'steps': [
                    {'range': [0, 50], 'color': "rgba(0, 200, 83, 0.3)"},
                    {'range': [50, 80], 'color': "rgba(255, 214, 0, 0.3)"},
                    {'range': [80, 100], 'color': "rgba(255, 23, 68, 0.3)"}
                ],
            }
        ))
        mem_fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font={'color': "white"},
            margin={'t': 0, 'b': 0, 'l': 20, 'r': 20},
            height=100
        )
        
        return (
            f"{cpu_percent}%",
            cpu_fig,
            f"{memory_percent}%",
            mem_fig
        )
    except Exception as e:
        # logger.error(f"Error updating system metrics: {str(e)}")
        empty_fig = go.Figure()
        empty_fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        return ("--", empty_fig, "--", empty_fig)


# Callback: Update price chart
@app.callback(
    Output('price-chart', 'figure'),
    Input('interval-component', 'n_intervals')
)
def update_price_chart(n):
    global chart_data, trader
    
    symbol_display = "BTC/USDT"
    if trader and trader.symbol:
        symbol_display = trader.symbol.replace('PERP_', '').replace('SPOT_', '').replace('_', '/')
    
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.6, 0.2, 0.2],
        subplot_titles=(f'{symbol_display} Price', f'{symbol_display} Volume', f'{symbol_display} Order Book Depth')
    )
    
    if len(chart_data['timestamps']) > 0:
        # Filter data for last 10 minutes
        now = datetime.now()
        cutoff = now - timedelta(minutes=10)
        
        timestamps = list(chart_data['timestamps'])
        prices = list(chart_data['prices'])
        volumes = list(chart_data['volumes'])
        bid_depth = list(chart_data['bid_depth'])
        ask_depth = list(chart_data['ask_depth'])
        
        # Find indices where timestamp >= cutoff
        indices = [i for i, t in enumerate(timestamps) if t >= cutoff]
        
        if indices:
            filtered_timestamps = [timestamps[i] for i in indices]
            filtered_prices = [prices[i] for i in indices]
            filtered_volumes = [volumes[i] for i in indices]
            filtered_bid_depth = [bid_depth[i] for i in indices]
            filtered_ask_depth = [ask_depth[i] for i in indices]
            
            # Price line
            fig.add_trace(
                go.Scatter(
                    x=filtered_timestamps,
                    y=filtered_prices,
                    mode='lines',
                    name='Price',
                    line=dict(color='#667eea', width=2),
                    fill='tozeroy',
                    fillcolor='rgba(102, 126, 234, 0.1)'
                ),
                row=1, col=1
            )
            
            # Bid/Ask depth
            fig.add_trace(
                go.Scatter(
                    x=filtered_timestamps,
                    y=filtered_bid_depth,
                    mode='lines',
                    name='Bid Depth',
                    line=dict(color='#00c853', width=1.5)
                ),
                row=3, col=1
            )
            
            fig.add_trace(
                go.Scatter(
                    x=filtered_timestamps,
                    y=filtered_ask_depth,
                    mode='lines',
                    name='Ask Depth',
                    line=dict(color='#ff1744', width=1.5)
                ),
                row=3, col=1
            )
            
            # Volume
            up_x, up_y = [], []
            down_x, down_y = [], []
            
            for i in range(len(filtered_prices)):
                if i == 0 or filtered_prices[i] >= filtered_prices[i-1]:
                    up_x.append(filtered_timestamps[i])
                    up_y.append(filtered_volumes[i])
                else:
                    down_x.append(filtered_timestamps[i])
                    down_y.append(filtered_volumes[i])
            
            if up_x:
                fig.add_trace(go.Bar(
                    x=up_x,
                    y=up_y,
                    name='Up Volume',
                    marker=dict(color='#00c853')
                ), row=2, col=1)
                
            if down_x:
                fig.add_trace(go.Bar(
                    x=down_x,
                    y=down_y,
                    name='Down Volume',
                    marker=dict(color='#ff1744')
                ), row=2, col=1)
            
            # Set y-axis range for Price chart (row 1) based on filtered min/max
            if filtered_prices:
                min_price = min(filtered_prices)
                max_price = max(filtered_prices)
                if min_price > 0 and max_price > 0:
                    fig.update_yaxes(range=[min_price * 0.99, max_price * 1.01], row=1, col=1)
    
    fig.update_xaxes(showgrid=False, gridcolor='#2e2e2e')
    fig.update_yaxes(showgrid=True, gridcolor='#2e2e2e')
    
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='#1e2130',
        plot_bgcolor='#1e2130',
        font=dict(color='#ffffff'),
        height=500,
        margin=dict(l=50, r=20, t=40, b=40),
        hovermode='x unified',
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    return fig


# Callback: Update orderbook chart
@app.callback(
    Output('orderbook-chart', 'figure'),
    Input('interval-component', 'n_intervals')
)
def update_orderbook_chart(n):
    global trader
    
    fig = go.Figure()
    
    if trader and trader.orderbook and trader.orderbook.get('bids') and trader.orderbook.get('asks'):
        bids = trader.orderbook['bids'][:20]
        asks = trader.orderbook['asks'][:20]
        
        # Cumulative depth
        bid_prices = [b['price'] for b in bids]
        bid_quantities = [b['quantity'] for b in bids]
        bid_cumsum = [sum(bid_quantities[:i+1]) for i in range(len(bid_quantities))]
        
        ask_prices = [a['price'] for a in asks]
        ask_quantities = [a['quantity'] for a in asks]
        ask_cumsum = [sum(ask_quantities[:i+1]) for i in range(len(ask_quantities))]
        
        # Bids (green)
        fig.add_trace(go.Scatter(
            x=bid_prices,
            y=bid_cumsum,
            mode='lines',
            name='Bids',
            fill='tozeroy',
            line=dict(color='#00c853', width=0),
            fillcolor='rgba(0, 200, 83, 0.3)'
        ))
        
        # Asks (red)
        fig.add_trace(go.Scatter(
            x=ask_prices,
            y=ask_cumsum,
            mode='lines',
            name='Asks',
            fill='tozeroy',
            line=dict(color='#ff1744', width=0),
            fillcolor='rgba(255, 23, 68, 0.3)'
        ))
    
    symbol_display = ""
    if trader and trader.symbol:
        symbol_display = trader.symbol.replace('PERP_', '').replace('SPOT_', '').replace('_', '/') + " "

    fig.update_layout(
        title=f'{symbol_display}Order Book Depth',
        template='plotly_dark',
        paper_bgcolor='#1e2130',
        plot_bgcolor='#1e2130',
        font=dict(color='#ffffff'),
        height=500,
        margin=dict(l=50, r=20, t=40, b=40),
        xaxis_title='Price',
        yaxis_title='Cumulative Volume',
        showlegend=True,
        hovermode='x unified'
    )
    
    return fig


# Callback: Update volume chart (Deprecated - Merged into Price Chart)
# @app.callback(
#     Output('volume-chart', 'figure'),
#     Input('interval-component', 'n_intervals')
# )
def update_volume_chart(n):
    return go.Figure()


# Callback: Update P&L chart
@app.callback(
    Output('pnl-chart', 'figure'),
    Input('interval-component', 'n_intervals')
)
def update_pnl_chart(n):
    global trader, chart_data
    
    fig = go.Figure()
    
    # Calculate cumulative P&L from position history
    if trader and len(trader.trade_px_list) > 0:
        pnl_data = []
        timestamps = []
        
        for entry in list(trader.trade_px_list):
            if trader.current_position:
                price = entry['price']
                entry_price = trader.current_position['entry_price']
                quantity = trader.current_position['quantity']
                
                if trader.current_position['side'] == 'long':
                    pnl = (price - entry_price) * quantity
                else:
                    pnl = (entry_price - price) * quantity
                
                pnl_data.append(pnl)
                timestamps.append(entry.get('timestamp', time.time()))
        
        if pnl_data:
            colors = ['#00c853' if p >= 0 else '#ff1744' for p in pnl_data]
            
            fig.add_trace(go.Scatter(
                x=[datetime.fromtimestamp(t) for t in timestamps],
                y=pnl_data,
                mode='lines',
                name='P&L',
                line=dict(color='#ffd600', width=2),
                fill='tozeroy',
                fillcolor='rgba(255, 214, 0, 0.1)'
            ))
    
    fig.update_layout(
        title='Profit & Loss',
        template='plotly_dark',
        paper_bgcolor='#1e2130',
        plot_bgcolor='#1e2130',
        font=dict(color='#ffffff'),
        height=300,
        margin=dict(l=50, r=20, t=40, b=40),
        xaxis_title='Time',
        yaxis_title='P&L ($)',
        showlegend=False,
        hovermode='x unified'
    )
    
    # Add zero line
    fig.add_hline(y=0, line_dash="dash", line_color="#666666", line_width=1)
    
    return fig


# Callback: Update RSI chart
@app.callback(
    Output('rsi-chart', 'figure'),
    Input('interval-component', 'n_intervals')
)
def update_rsi_chart(n):
    global trader
    
    fig = go.Figure()
    
    if trader and len(trader.trade_px_list) >= 14:
        try:
            # Get config
            config = config_loader.load_config()
            timeframe = int(config.get('RSI_TIMEFRAME', 60))
            period = int(config.get('RSI_PERIOD', 14))
            
            # Resample data
            prices_resampled = []
            timestamps_resampled = []
            
            history_list = list(trader.trade_px_list)
            
            if timeframe > 1:
                current_bucket = None
                last_entry_in_bucket = None
                
                for entry in history_list:
                    if not entry.get('price') or not entry.get('timestamp'):
                        continue
                        
                    ts = entry['timestamp']
                    bucket = int(ts // timeframe)
                    
                    if current_bucket is not None and bucket != current_bucket:
                        prices_resampled.append(last_entry_in_bucket['price'])
                        timestamps_resampled.append(datetime.fromtimestamp(last_entry_in_bucket['timestamp']))
                    
                    current_bucket = bucket
                    last_entry_in_bucket = entry
                
                # Add the last partial bucket
                if last_entry_in_bucket is not None:
                    prices_resampled.append(last_entry_in_bucket['price'])
                    timestamps_resampled.append(datetime.fromtimestamp(last_entry_in_bucket['timestamp']))
            else:
                # Raw data
                prices_resampled = [entry['price'] for entry in history_list if entry.get('price')]
                timestamps_resampled = [datetime.fromtimestamp(entry['timestamp']) for entry in history_list if entry.get('timestamp')]

            # Calculate RSI
            rsi_values = []
            
            if len(prices_resampled) >= period + 1:
                # Calculate deltas
                deltas = [prices_resampled[i] - prices_resampled[i-1] for i in range(1, len(prices_resampled))]
                
                # Calculate RSI for each point (simple moving average method for simplicity in chart)
                # For accurate RSI we should use Wilder's Smoothing, but simple SMA is often used for quick visualization
                # Let's stick to the simple method used before but applied to the window
                
                for i in range(len(prices_resampled)):
                    if i < period:
                        rsi_values.append(None)
                        continue
                        
                    # Get slice for this window
                    window_deltas = deltas[i-period : i]
                    gains = [d if d > 0 else 0 for d in window_deltas]
                    losses = [-d if d < 0 else 0 for d in window_deltas]
                    
                    avg_gain = sum(gains) / period
                    avg_loss = sum(losses) / period
                    
                    if avg_loss != 0:
                        rs = avg_gain / avg_loss
                        rsi = 100 - (100 / (1 + rs))
                    else:
                        rsi = 100
                    
                    rsi_values.append(rsi)
            
            # Plotting
            display_limit = 200
            
            plot_timestamps = timestamps_resampled[-display_limit:]
            plot_rsi = rsi_values[-display_limit:]
            
            if len(plot_timestamps) > 0 and len(plot_rsi) > 0:
                fig.add_trace(go.Scatter(
                    x=plot_timestamps,
                    y=plot_rsi,
                    mode='lines',
                    name='RSI',
                    line=dict(color='#2196F3', width=2)
                ))
                
                # Add overbought/oversold lines
                fig.add_hline(y=70, line_dash="dash", line_color="#ff1744", line_width=1, annotation_text="Overbought")
                fig.add_hline(y=30, line_dash="dash", line_color="#00c853", line_width=1, annotation_text="Oversold")
                fig.add_hline(y=50, line_dash="dot", line_color="#666666", line_width=1)
                
        except Exception as e:
            print(f"Error updating RSI chart: {e}")
    
    symbol_display = ""
    if trader and trader.symbol:
        symbol_display = trader.symbol.replace('PERP_', '').replace('SPOT_', '').replace('_', '/') + " "

    fig.update_layout(
        title=f'{symbol_display}RSI Indicator ({config_loader.get_config_value("RSI_PERIOD", 14)})',
        xaxis_title='Time',
        yaxis_title='RSI',
        template='plotly_dark',
        paper_bgcolor='#1e2130',
        plot_bgcolor='#1e2130',
        height=300,
        margin=dict(l=50, r=20, t=40, b=40),
        hovermode='x unified',
        yaxis=dict(range=[0, 100])
    )
    
    return fig


# Callback: Update Moving Averages chart
@app.callback(
    Output('ma-chart', 'figure'),
    Input('interval-component', 'n_intervals')
)
def update_ma_chart(n):
    global trader
    
    fig = go.Figure()
    
    if trader and len(trader.trade_px_list) > 0:
        try:
            # Get config
            config = config_loader.load_config()
            timeframe = int(config.get('MA_TIMEFRAME', 60))
            short_period = int(config.get('SHORT_MA_PERIOD', 20))
            long_period = int(config.get('LONG_MA_PERIOD', 50))
            
            # Resample data
            prices_resampled = []
            timestamps_resampled = []
            
            history_list = list(trader.trade_px_list)
            
            if timeframe > 1:
                current_bucket = None
                last_entry_in_bucket = None
                
                for entry in history_list:
                    if not entry.get('price') or not entry.get('timestamp'):
                        continue
                        
                    ts = entry['timestamp']
                    bucket = int(ts // timeframe)
                    
                    if current_bucket is not None and bucket != current_bucket:
                        prices_resampled.append(last_entry_in_bucket['price'])
                        timestamps_resampled.append(datetime.fromtimestamp(last_entry_in_bucket['timestamp']))
                    
                    current_bucket = bucket
                    last_entry_in_bucket = entry
                
                # Add the last partial bucket
                if last_entry_in_bucket is not None:
                    prices_resampled.append(last_entry_in_bucket['price'])
                    timestamps_resampled.append(datetime.fromtimestamp(last_entry_in_bucket['timestamp']))
            else:
                # Raw data
                prices_resampled = [entry['price'] for entry in history_list if entry.get('price')]
                timestamps_resampled = [datetime.fromtimestamp(entry['timestamp']) for entry in history_list if entry.get('timestamp')]

            # Calculate MAs
            ma_short_values = []
            ma_long_values = []
            
            # Simple Moving Average Calculation
            for i in range(len(prices_resampled)):
                # Short MA
                if i + 1 >= short_period:
                    ma = sum(prices_resampled[i+1-short_period : i+1]) / short_period
                    ma_short_values.append(ma)
                else:
                    ma_short_values.append(None)
                
                # Long MA
                if i + 1 >= long_period:
                    ma = sum(prices_resampled[i+1-long_period : i+1]) / long_period
                    ma_long_values.append(ma)
                else:
                    ma_long_values.append(None)
            
            # Plotting
            # Limit to last 200 points for better visibility
            display_limit = 200
            
            plot_timestamps = timestamps_resampled[-display_limit:]
            plot_prices = prices_resampled[-display_limit:]
            plot_ma_short = ma_short_values[-display_limit:]
            plot_ma_long = ma_long_values[-display_limit:]
            
            # Price line
            fig.add_trace(go.Scatter(
                x=plot_timestamps,
                y=plot_prices,
                mode='lines',
                name='Price',
                line=dict(color='#ffd600', width=2)
            ))
            
            # MA Short
            fig.add_trace(go.Scatter(
                x=plot_timestamps,
                y=plot_ma_short,
                mode='lines',
                name=f'MA{short_period}',
                line=dict(color='#00c853', width=1.5, dash='dash')
            ))
            
            # MA Long
            fig.add_trace(go.Scatter(
                x=plot_timestamps,
                y=plot_ma_long,
                mode='lines',
                name=f'MA{long_period}',
                line=dict(color='#ff1744', width=1.5, dash='dot')
            ))
            
        except Exception as e:
            print(f"Error updating MA chart: {e}")

    symbol_display = ""
    if trader and trader.symbol:
        symbol_display = trader.symbol.replace('PERP_', '').replace('SPOT_', '').replace('_', '/') + " "

    fig.update_layout(
        title=f'{symbol_display}Moving Averages Strategy',
        xaxis_title='Time',
        yaxis_title='Price',
        template='plotly_dark',
        paper_bgcolor='#1e2130',
        plot_bgcolor='#1e2130',
        height=350,
        margin=dict(l=50, r=20, t=40, b=40),
        hovermode='x unified',
        legend=dict(x=0.01, y=0.99)
    )
    
    return fig


# Callback: Update Spread chart
@app.callback(
    Output('spread-chart', 'figure'),
    Input('interval-component', 'n_intervals')
)
def update_spread_chart(n):
    global trader, chart_data
    
    fig = go.Figure()
    
    if trader and trader.orderbook:
        # Calculate spread
        bids = trader.orderbook.get('bids', [])
        asks = trader.orderbook.get('asks', [])
        
        if bids and asks:
            best_bid = bids[0]['price']
            best_ask = asks[0]['price']
            spread = best_ask - best_bid
            spread_pct = (spread / best_bid) * 100
            
            chart_data['spread'].append(spread_pct)
            
            if len(chart_data['timestamps']) > 0 and len(chart_data['spread']) > 0:
                spread_values = list(chart_data['spread'])[-len(chart_data['timestamps']):]
                
                fig.add_trace(go.Scatter(
                    x=list(chart_data['timestamps'])[-len(spread_values):],
                    y=spread_values,
                    mode='lines',
                    name='Spread %',
                    line=dict(color='#9C27B0', width=2),
                    fill='tozeroy',
                    fillcolor='rgba(156, 39, 176, 0.1)'
                ))
    
    symbol_display = ""
    if trader and trader.symbol:
        symbol_display = trader.symbol.replace('PERP_', '').replace('SPOT_', '').replace('_', '/') + " "

    fig.update_layout(
        title=f'{symbol_display}Bid-Ask Spread %',
        xaxis_title='Time',
        yaxis_title='Spread (%)',
        template='plotly_dark',
        paper_bgcolor='#1e2130',
        plot_bgcolor='#1e2130',
        height=300,
        margin=dict(l=50, r=20, t=40, b=40),
        hovermode='x unified'
    )
    
    return fig


# Callback: Update Trade Distribution chart
@app.callback(
    Output('trade-distribution-chart', 'figure'),
    Input('interval-component', 'n_intervals')
)
def update_trade_distribution_chart(n):
    global performance_metrics, trader
    
    fig = go.Figure()
    
    winning = performance_metrics['winning_trades']
    losing = performance_metrics['losing_trades']
    
    if winning > 0 or losing > 0:
        fig.add_trace(go.Pie(
            labels=['Winning Trades', 'Losing Trades'],
            values=[winning, losing],
            marker=dict(colors=['#00c853', '#ff1744']),
            hole=0.4,
            textinfo='label+percent+value',
            textfont=dict(size=14, color='white')
        ))
    
    symbol_display = ""
    if trader and trader.symbol:
        symbol_display = trader.symbol.replace('PERP_', '').replace('SPOT_', '').replace('_', '/') + " "

    fig.update_layout(
        title=f'{symbol_display}Trade Distribution',
        template='plotly_dark',
        paper_bgcolor='#1e2130',
        plot_bgcolor='#1e2130',
        height=300,
        margin=dict(l=20, r=20, t=40, b=20),
        showlegend=True,
        legend=dict(font=dict(color='white'))
    )
    
    return fig


# Callback: Update Cumulative Return chart
@app.callback(
    Output('cumulative-return-chart', 'figure'),
    Input('interval-component', 'n_intervals')
)
def update_cumulative_return_chart(n):
    global trader, performance_metrics
    
    fig = go.Figure()
    
    if trader:
        try:
            account = Account(trade_mode=trader.trade_mode)
            summary = account.get_transaction_summary()
            
            if summary:
                # Get cumulative P&L over time (simplified)
                cumulative_pnl = []
                running_total = 0
                
                # This is a placeholder - you'd need actual trade history with timestamps
                for i in range(min(len(chart_data['timestamps']), performance_metrics['total_trades'])):
                    # Simplified: divide total P&L by number of trades
                    running_total += performance_metrics['total_pnl'] / max(performance_metrics['total_trades'], 1)
                    cumulative_pnl.append(running_total)
                
                if cumulative_pnl and len(chart_data['timestamps']) > 0:
                    timestamps = list(chart_data['timestamps'])[-len(cumulative_pnl):]
                    
                    fig.add_trace(go.Scatter(
                        x=timestamps,
                        y=cumulative_pnl,
                        mode='lines',
                        name='Cumulative P&L',
                        line=dict(color='#00e676', width=2),
                        fill='tozeroy',
                        fillcolor='rgba(0, 230, 118, 0.1)'
                    ))
        except Exception as e:
            logger.error(f"Error calculating cumulative return: {e}")
    
    symbol_display = ""
    if trader and trader.symbol:
        symbol_display = trader.symbol.replace('PERP_', '').replace('SPOT_', '').replace('_', '/') + " "

    fig.update_layout(
        title=f'{symbol_display}Cumulative Return',
        xaxis_title='Time',
        yaxis_title='Total P&L (USD)',
        template='plotly_dark',
        paper_bgcolor='#1e2130',
        plot_bgcolor='#1e2130',
        height=300,
        margin=dict(l=50, r=20, t=40, b=40),
        hovermode='x unified'
    )
    
    fig.add_hline(y=0, line_dash="dash", line_color="#666666", line_width=1)
    
    return fig


# Callback: Update performance table
@app.callback(
    Output('performance-table', 'children'),
    Input('interval-component', 'n_intervals')
)
def update_performance_table(n):
    global trader, performance_metrics
    
    # Always load latest config to determine which DB to read from
    try:
        config = config_loader.load_config()
        trade_mode = config.get('TRADE_MODE', 'paper')
        
        with Account(trade_mode=trade_mode) as account:
            # Pass current price to calculate Total P&L (Realized + Unrealized)
            current_price = trader.current_price if trader else None
            summary = account.get_transaction_summary(current_price=current_price)
            
            if summary:
                performance_metrics['total_trades'] = summary['buy_count'] + summary['sell_count']
                performance_metrics['total_pnl'] = summary.get('net_pnl', 0.0)
                performance_metrics['winning_trades'] = summary.get('winning_trades', 0)
                performance_metrics['losing_trades'] = summary.get('losing_trades', 0)
                performance_metrics['unrealized_pnl'] = summary.get('unrealized_pnl', 0.0)
                
                # Calculate win rate
                total_closed = performance_metrics['winning_trades'] + performance_metrics['losing_trades']
                if total_closed > 0:
                    performance_metrics['win_rate'] = (performance_metrics['winning_trades'] / total_closed) * 100
                else:
                    performance_metrics['win_rate'] = 0.0
    except Exception as e:
        logger.error(f"Error getting account summary: {str(e)}")
    
    metrics = [
        ("Total Trades", performance_metrics['total_trades']),
        ("Winning Trades", performance_metrics['winning_trades']),
        ("Losing Trades", performance_metrics['losing_trades']),
        ("Win Rate", f"{performance_metrics['win_rate']:.1f}%"),
        ("Total P&L", f"${performance_metrics['total_pnl']:.2f}"),
        ("Unrealized P&L", f"${performance_metrics.get('unrealized_pnl', 0.0):.2f}"),
        ("Sharpe Ratio", f"{performance_metrics['sharpe_ratio']:.2f}"),
    ]
    
    table_rows = []
    for label, value in metrics:
        table_rows.append(html.Tr([
            html.Td(label, style={'color': '#d0d0d0', 'padding': '8px', 'fontSize': '14px'}),
            html.Td(str(value), style={'color': '#ffffff', 'padding': '8px', 'textAlign': 'right', 'fontWeight': 'bold', 'fontSize': '15px'})
        ]))
    
    return html.Table(table_rows, style={'width': '100%', 'borderCollapse': 'collapse'})


# Callback: Update activity log
@app.callback(
    Output('activity-log', 'children'),
    Input('interval-component', 'n_intervals')
)
def update_activity_log(n):
    # Read recent log entries
    try:
        with open('trade.log', 'r') as f:
            # Use deque to efficiently get the last 20 lines
            lines = deque(f, maxlen=20)
            log_entries = []
            for line in lines:
                # Color code based on log level
                if 'ERROR' in line:
                    color = '#ff5252'
                elif 'WARNING' in line:
                    color = '#ffea00'
                elif 'INFO' in line:
                    color = '#00e676'
                else:
                    color = '#b0b0b0'
                
                log_entries.append(html.Div(line.strip(), style={'color': color, 'marginBottom': '5px', 'fontSize': '13px', 'fontFamily': 'monospace'}))
            
            # Reverse to show newest at top if desired, but usually logs are top-down. 
            # If the UI scrolls to bottom, standard order is fine.
            # The current UI has overflowY: scroll, so it's a scrollable box.
            # Usually logs are appended.
            
            return log_entries
    except FileNotFoundError:
        return html.Div("No log file found", style={'color': '#888888', 'fontSize': '14px'})
    except Exception as e:
        return html.Div(f"Error reading logs: {str(e)}", style={'color': '#ff5252', 'fontSize': '14px'})


# Callback: Update print report - Trading Records
@app.callback(
    Output('print-trading-records', 'children'),
    Input('interval-component', 'n_intervals')
)
def update_print_trading_records(n):
    global trader, chart_data
    
    try:
        # Collect trading data
        rows = []
        
        # Add current position if exists
        if trader and trader.current_position:
            pos = trader.current_position
            rows.append(html.Tr([
                html.Td("CURRENT", style={'fontWeight': 'bold', 'color': '#2196F3'}),
                html.Td(pos['side'].upper()),
                html.Td(f"{pos['quantity']:.6f}"),
                html.Td(f"${pos['entry_price']:.2f}"),
                html.Td(f"${trader.current_price:.2f}" if trader.current_price else "N/A"),
                html.Td("OPEN", style={'color': '#00c853', 'fontWeight': 'bold'}),
            ]))
        
        # Add price history data
        if len(chart_data['timestamps']) > 0:
            for i, (ts, price, vol) in enumerate(zip(
                list(chart_data['timestamps'])[-50:], 
                list(chart_data['prices'])[-50:],
                list(chart_data['volumes'])[-50:]
            )):
                if i % 5 == 0:  # Sample every 5th entry to avoid too much data
                    rows.append(html.Tr([
                        html.Td(ts.strftime('%H:%M:%S')),
                        html.Td("MONITOR"),
                        html.Td("N/A"),
                        html.Td("N/A"),
                        html.Td(f"${price:.2f}"),
                        html.Td(f"{vol:.2f}"),
                    ]))
        
        if not rows:
            rows.append(html.Tr([
                html.Td("No trading data available", colSpan=6, style={'textAlign': 'center', 'color': '#666'})
            ]))
        
        return html.Div([
            html.H3("Trading Records", style={'color': '#333', 'borderBottom': '2px solid #667eea', 'paddingBottom': '10px', 'marginBottom': '20px'}),
            html.Table([
                html.Thead(html.Tr([
                    html.Th("Time", style={'backgroundColor': '#f0f0f0', 'padding': '12px', 'fontWeight': 'bold'}),
                    html.Th("Side", style={'backgroundColor': '#f0f0f0', 'padding': '12px', 'fontWeight': 'bold'}),
                    html.Th("Quantity", style={'backgroundColor': '#f0f0f0', 'padding': '12px', 'fontWeight': 'bold'}),
                    html.Th("Entry Price", style={'backgroundColor': '#f0f0f0', 'padding': '12px', 'fontWeight': 'bold'}),
                    html.Th("Current Price", style={'backgroundColor': '#f0f0f0', 'padding': '12px', 'fontWeight': 'bold'}),
                    html.Th("Status/Volume", style={'backgroundColor': '#f0f0f0', 'padding': '12px', 'fontWeight': 'bold'}),
                ])),
                html.Tbody(rows)
            ], style={'width': '100%', 'borderCollapse': 'collapse', 'marginBottom': '30px', 'border': '1px solid #ddd'})
        ])
        
    except Exception as e:
        logger.error(f"Error generating print trading records: {str(e)}")
        return html.Div(f"Error: {str(e)}", style={'color': 'red'})


# Callback: Update print report - Account Summary
@app.callback(
    Output('print-account-summary', 'children'),
    Input('interval-component', 'n_intervals')
)
def update_print_account_summary(n):
    global trader, performance_metrics
    
    try:
        summary_items = []
        
        # Performance metrics
        metrics_data = [
            ("Total Trades", str(performance_metrics['total_trades'])),
            ("Winning Trades", str(performance_metrics['winning_trades'])),
            ("Losing Trades", str(performance_metrics['losing_trades'])),
            ("Win Rate", f"{performance_metrics['win_rate']:.1f}%"),
            ("Total P&L", f"${performance_metrics['total_pnl']:.2f}"),
            ("Sharpe Ratio", f"{performance_metrics['sharpe_ratio']:.2f}"),
        ]
        
        # Current bot status
        if trader:
            summary_items.append(html.Div([
                html.H4("Current Status", style={'color': '#333', 'marginTop': '0'}),
                html.Table([
                    html.Tr([
                        html.Td("Bot Status:", style={'fontWeight': 'bold', 'padding': '8px', 'width': '200px'}),
                        html.Td("Running" if is_running else "Stopped", style={'padding': '8px'})
                    ]),
                    html.Tr([
                        html.Td("Current Price:", style={'fontWeight': 'bold', 'padding': '8px'}),
                        html.Td(f"${trader.current_price:.2f}" if trader.current_price else "N/A", style={'padding': '8px'})
                    ]),
                    html.Tr([
                        html.Td("Data Points:", style={'fontWeight': 'bold', 'padding': '8px'}),
                        html.Td(f"{len(trader.trade_px_list)}/1440", style={'padding': '8px'})
                    ]),
                ], style={'width': '100%', 'border': '1px solid #ddd', 'marginBottom': '20px'})
            ]))
        
        # Performance summary
        summary_items.append(html.Div([
            html.H4("Performance Summary", style={'color': '#333'}),
            html.Table([
                html.Tr([
                    html.Td(label + ":", style={'fontWeight': 'bold', 'padding': '8px', 'width': '200px', 'borderBottom': '1px solid #ddd'}),
                    html.Td(value, style={'padding': '8px', 'borderBottom': '1px solid #ddd'})
                ]) for label, value in metrics_data
            ], style={'width': '100%', 'border': '1px solid #ddd'})
        ]))
        
        return html.Div([
            html.H3("Account Summary", style={'color': '#333', 'borderBottom': '2px solid #667eea', 'paddingBottom': '10px', 'marginBottom': '20px'}),
            html.Div(summary_items)
        ])
        
    except Exception as e:
        logger.error(f"Error generating print account summary: {str(e)}")
        return html.Div(f"Error: {str(e)}", style={'color': 'red'})


# Callback: Update Symbol Options based on Trade Type
@app.callback(
    Output('conf-symbol', 'options'),
    Input('conf-trade-type', 'value')
)
def update_symbol_options(trade_type):
    if trade_type == 'spot':
        return [
            {'label': 'BTC/USDT', 'value': 'SPOT_BTC_USDT'},
            {'label': 'ETH/USDT', 'value': 'SPOT_ETH_USDT'},
            {'label': 'XRP/USDT', 'value': 'SPOT_XRP_USDT'},
            {'label': 'SOL/USDT', 'value': 'SPOT_SOL_USDT'}
        ]
    else:
        return [
            {'label': 'BTC/USDT', 'value': 'PERP_BTC_USDT'},
            {'label': 'ETH/USDT', 'value': 'PERP_ETH_USDT'},
            {'label': 'XRP/USDT', 'value': 'PERP_XRP_USDT'},
            {'label': 'SOL/USDT', 'value': 'PERP_SOL_USDT'}
        ]


@app.callback(
    Output('spot-warning', 'children'),
    Input('conf-trade-type', 'value')
)
def update_spot_warning(trade_type):
    if trade_type == 'spot':
        return "⚠️ Spot trading does not support short selling."
    return ""


# Callback: Update Position Size Label and Default Value
@app.callback(
    [Output('pos-size-value-label', 'children'),
     Output('conf-pos-size-value', 'value', allow_duplicate=True),
     Output('config-loaded-flag', 'data', allow_duplicate=True)],
    [Input('conf-pos-size-type', 'value'),
     Input('conf-symbol', 'value'),
     Input('config-loaded-flag', 'data')],
    prevent_initial_call=True
)
def update_pos_size_ui(size_type, symbol, is_loading):
    label = "Position Size Value"
    new_value = dash.no_update
    
    # Determine label
    if size_type == 'value':
        label = "Position Size Value ($ USDT)"
    elif size_type == 'percentage':
        label = "Position Size Value (% of Balance)"
    elif size_type == 'quantity':
        asset = "Asset"
        if symbol:
            parts = symbol.split('_')
            if len(parts) >= 2:
                asset = parts[1]
        label = f"Position Size Value (Number of {asset})"
    
    # Determine default value if not loading from config
    if not is_loading:
        if size_type == 'quantity' and symbol:
            asset = symbol.split('_')[1] if len(symbol.split('_')) >= 2 else ''
            defaults = {
                'BTC': 0.0001,
                'ETH': 0.002,
                'SOL': 0.05,
                'XRP': 5.0
            }
            if asset in defaults:
                new_value = defaults[asset]
        elif size_type == 'value':
            new_value = 10.0
            
    return label, new_value, False


# Callback: Toggle Config Modal and Load Settings
@app.callback(
    [Output('config-modal', 'style'),
     Output('conf-trade-mode', 'value'),
     Output('conf-trade-type', 'value'),
     Output('conf-symbol', 'value'),
     Output('conf-pos-size-type', 'value'),
     Output('conf-pos-size-value', 'value'),
     Output('conf-max-pos', 'value'),
     Output('conf-strategy', 'value'),
     Output('conf-short-ma', 'value'),
     Output('conf-long-ma', 'value'),
     Output('conf-ma-timeframe', 'value'),
     Output('conf-ma-threshold', 'value'),
     Output('conf-rsi-timeframe', 'value'),
     Output('conf-rsi-period', 'value'),
     Output('conf-sl', 'value'),
     Output('conf-tp', 'value'),
     Output('config-loaded-flag', 'data')],
    [Input('config-btn', 'n_clicks'),
     Input('close-config-btn', 'n_clicks'),
     Input('cancel-config-btn', 'n_clicks'),
     Input('save-config-btn', 'n_clicks')],
    [State('config-modal', 'style')]
)
def toggle_config_modal(n1, n2, n3, n4, current_style):
    ctx = callback_context
    if not ctx.triggered:
        return {'display': 'none'}, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, False
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if button_id == 'config-btn':
        # Open modal and load config
        try:
            config = config_loader.load_config()
            return (
                {'display': 'block'},
                config.get('TRADE_MODE', 'paper'),
                config.get('TRADE_TYPE', 'future'),
                config.get('SYMBOL', 'PERP_BTC_USDT'),
                config.get('MAX_POS_SIZE_TYPE', 'value'),
                float(config.get('MAX_POS_SIZE_VALUE', 10.0)),
                int(config.get('MAX_OPEN_POSITIONS', 1)),
                config.get('ENTRY_STRATEGY', 'ma_crossover'),
                int(config.get('SHORT_MA_PERIOD', 20)),
                int(config.get('LONG_MA_PERIOD', 50)),
                int(config.get('MA_TIMEFRAME', 60)),
                float(config.get('MA_THRESHOLD', 5.0)),
                int(config.get('RSI_TIMEFRAME', 60)),
                int(config.get('RSI_PERIOD', 14)),
                float(config.get('STOP_LOSS_PCT', 3.0)),
                float(config.get('TAKE_PROFIT_PCT', 5.0)),
                True # Set flag to True indicating config just loaded
            )
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return {'display': 'block'}, 'paper', 'future', 'PERP_BTC_USDT', 'value', 10.0, 1, 'ma_crossover', 20, 50, 60, 5.0, 60, 14, 3.0, 5.0, True
            
    elif button_id in ['close-config-btn', 'cancel-config-btn', 'save-config-btn']:
        return {'display': 'none'}, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, False
    
    return {'display': 'none'}, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, False

# Callback: Save Config
@app.callback(
    Output('config-feedback', 'children'),
    Input('save-config-btn', 'n_clicks'),
    [State('conf-trade-mode', 'value'),
     State('conf-trade-type', 'value'),
     State('conf-symbol', 'value'),
     State('conf-pos-size-type', 'value'),
     State('conf-pos-size-value', 'value'),
     State('conf-max-pos', 'value'),
     State('conf-strategy', 'value'),
     State('conf-short-ma', 'value'),
     State('conf-long-ma', 'value'),
     State('conf-ma-timeframe', 'value'),
     State('conf-ma-threshold', 'value'),
     State('conf-rsi-timeframe', 'value'),
     State('conf-rsi-period', 'value'),
     State('conf-sl', 'value'),
     State('conf-tp', 'value')],
    prevent_initial_call=True
)
def save_config(n_clicks, trade_mode, trade_type, symbol, pos_size_type, pos_size_value, max_pos, strategy, ma_short, ma_long, ma_timeframe, ma_threshold, rsi_timeframe, rsi_period, sl, tp):
    try:
        # Read existing config to preserve comments
        with open('.config', 'r') as f:
            lines = f.readlines()
        
        new_lines = []
        updates = {
            'TRADE_MODE': trade_mode,
            'TRADE_TYPE': trade_type,
            'SYMBOL': symbol,
            'MAX_POS_SIZE_TYPE': pos_size_type,
            'MAX_POS_SIZE_VALUE': str(pos_size_value),
            'MAX_OPEN_POSITIONS': str(max_pos),
            'ENTRY_STRATEGY': strategy,
            'EXIT_STRATEGY': strategy, # Assume same for now
            'SHORT_MA_PERIOD': str(ma_short),
            'LONG_MA_PERIOD': str(ma_long),
            'MA_TIMEFRAME': str(ma_timeframe),
            'MA_THRESHOLD': str(ma_threshold),
            'RSI_TIMEFRAME': str(rsi_timeframe),
            'RSI_PERIOD': str(rsi_period),
            'STOP_LOSS_PCT': str(sl),
            'TAKE_PROFIT_PCT': str(tp)
        }
        
        for line in lines:
            key = line.split('=')[0].strip() if '=' in line else None
            if key and key in updates:
                new_lines.append(f"{key}={updates[key]}\n")
                del updates[key]
            else:
                new_lines.append(line)
        
        # Append any new keys
        for key, value in updates.items():
            new_lines.append(f'{key}={value}\n')
            
        with open('.config', 'w') as f:
            f.writelines(new_lines)
            
        return html.Span("✅ Settings saved successfully! Restart bot to apply.", style={'color': '#00c853'})
    except Exception as e:
        logger.error(f"Error saving config: {e}")
        return html.Span(f"❌ Error saving settings: {str(e)}", style={'color': '#ff1744'})


def get_trading_records():
    try:
        # Determine DB file based on config
        config = config_loader.load_config()
        trade_mode = config.get('TRADE_MODE', 'paper')
        db_file = 'live_transaction.db' if trade_mode == 'live' else 'paper_transaction.db'
        
        # Use read_only=True to avoid locking issues if the bot is writing
        conn = duckdb.connect(db_file, read_only=True)
        
        # Check if table exists
        try:
            conn.execute("SELECT 1 FROM trades LIMIT 1")
        except:
            conn.close()
            return []
            
        # Fetch records, latest first
        records = conn.execute("SELECT * FROM trades ORDER BY trade_datetime DESC LIMIT 50").fetchall()
        columns = [desc[0] for desc in conn.description]
        conn.close()
        
        return [dict(zip(columns, row)) for row in records]
    except Exception as e:
        # logger.error(f"Error fetching trading records: {e}") # Reduce noise if DB doesn't exist yet
        return []


# Callback: Update Trading Records
@app.callback(
    Output('trading-record-table', 'children'),
    Input('interval-component', 'n_intervals')
)
def update_trading_records(n):
    records = get_trading_records()
    
    if not records:
        return html.Div("No trading records found.", style={'color': '#a0a0a0', 'textAlign': 'center', 'padding': '20px'})
    
    # Create table header
    header = html.Tr([
        html.Th("Time", style={'textAlign': 'left', 'padding': '12px', 'borderBottom': '1px solid #444', 'color': '#888'}),
        html.Th("Symbol", style={'textAlign': 'left', 'padding': '12px', 'borderBottom': '1px solid #444', 'color': '#888'}),
        html.Th("Type", style={'textAlign': 'left', 'padding': '12px', 'borderBottom': '1px solid #444', 'color': '#888'}),
        html.Th("Action", style={'textAlign': 'left', 'padding': '12px', 'borderBottom': '1px solid #444', 'color': '#888'}),
        html.Th("Price", style={'textAlign': 'right', 'padding': '12px', 'borderBottom': '1px solid #444', 'color': '#888'}),
        html.Th("Quantity", style={'textAlign': 'right', 'padding': '12px', 'borderBottom': '1px solid #444', 'color': '#888'}),
        html.Th("Proceeds", style={'textAlign': 'right', 'padding': '12px', 'borderBottom': '1px solid #444', 'color': '#888'}),
    ])
    
    rows = []
    for r in records:
        # Format values
        dt = r.get('trade_datetime', '')
        symbol = r.get('symbol', '').replace('PERP_', '').replace('SPOT_', '').replace('_', '/')
        trade_type = r.get('trade_type', '')
        code = r.get('code', '') # O=Open, C=Close
        
        action_map = {'O': 'OPEN', 'C': 'CLOSE'}
        action = action_map.get(code, code)
        
        price = f"${r.get('price', 0):,.2f}"
        qty = f"{abs(r.get('quantity', 0)):.4f}"
        proceeds = f"${r.get('proceeds', 0):,.2f}"
        
        row_style = {'borderBottom': '1px solid #2e3241', 'color': '#e0e0e0', 'fontSize': '13px'}
        
        if trade_type == 'BUY':
            type_style = {'color': '#00c853', 'fontWeight': 'bold'}
        else:
            type_style = {'color': '#ff1744', 'fontWeight': 'bold'}
            
        rows.append(html.Tr([
            html.Td(str(dt), style={'padding': '10px'}),
            html.Td(symbol, style={'padding': '10px'}),
            html.Td(trade_type, style={'padding': '10px', **type_style}),
            html.Td(action, style={'padding': '10px'}),
            html.Td(price, style={'padding': '10px', 'textAlign': 'right'}),
            html.Td(qty, style={'padding': '10px', 'textAlign': 'right'}),
            html.Td(proceeds, style={'padding': '10px', 'textAlign': 'right'}),
        ], style=row_style))
        
    return html.Table([html.Thead(header), html.Tbody(rows)], style={'width': '100%', 'borderCollapse': 'collapse'})


if __name__ == '__main__':
    print("\n" + "="*70)
    print("🚀 WOOX Trading Bot Dashboard Starting...")
    print("="*70)
    print("\n📊 Dashboard URL: http://127.0.0.1:8050")
    print("\n💡 Features:")
    print("   - Real-time price monitoring")
    print("   - Interactive bot control (Start/Stop/Close)")
    print("   - Live orderbook visualization")
    print("   - P&L tracking and performance metrics")
    print("   - Activity log monitoring")
    print("\n⚠️  Note: The bot will start in PAPER mode by default")
    print("="*70 + "\n")
    
    # Note: debug=False to avoid signal module conflict with signal.py
    app.run(debug=False, port=8050, host='0.0.0.0')
