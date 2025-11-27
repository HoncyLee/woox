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
import logging
from collections import deque

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
                padding: 20px;
                margin: 10px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.2);
                border-left: 4px solid #667eea;
            }
            .metric-value {
                font-size: 32px;
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
        html.H3("Control Panel", style={'color': '#ffffff', 'marginBottom': '15px'}),
        html.Div([
            html.Button("▶ Start Bot", id='start-btn', n_clicks=0, className='control-button start-btn'),
            html.Button("⏸ Stop Bot", id='stop-btn', n_clicks=0, className='control-button stop-btn'),
            html.Button("❌ Close Position", id='close-btn', n_clicks=0, className='control-button close-btn'),
            html.Button("🖨️ Print Report", id='print-btn', n_clicks=0, className='control-button print-btn'),
            html.Div(id='control-feedback', style={'color': '#ffffff', 'marginTop': '10px', 'fontSize': '14px'})
        ]),
    ], style={'backgroundColor': '#1e2130', 'padding': '20px', 'borderRadius': '10px', 'marginBottom': '20px'}, className='no-print'),
    
    # Metrics Row
    html.Div([
        # Price Metric
        html.Div([
            html.Div("Current Price", className='metric-label'),
            html.Div(id='price-metric', className='metric-value'),
            html.Div(id='price-change', className='metric-change'),
        ], className='metric-card', style={'width': '18%', 'display': 'inline-block'}),
        
        # Position Metric
        html.Div([
            html.Div("Position", className='metric-label'),
            html.Div(id='position-metric', className='metric-value'),
            html.Div(id='position-size', className='metric-change'),
        ], className='metric-card', style={'width': '18%', 'display': 'inline-block'}),
        
        # P&L Metric
        html.Div([
            html.Div("Unrealized P&L", className='metric-label'),
            html.Div(id='pnl-metric', className='metric-value'),
            html.Div(id='pnl-percent', className='metric-change'),
        ], className='metric-card', style={'width': '18%', 'display': 'inline-block'}),
        
        # Total Trades
        html.Div([
            html.Div("Total Trades", className='metric-label'),
            html.Div(id='trades-metric', className='metric-value'),
            html.Div(id='win-rate', className='metric-change'),
        ], className='metric-card', style={'width': '18%', 'display': 'inline-block'}),
        
        # Data Points
        html.Div([
            html.Div("Data Points", className='metric-label'),
            html.Div(id='datapoints-metric', className='metric-value'),
            html.Div(id='data-coverage', className='metric-change'),
        ], className='metric-card', style={'width': '18%', 'display': 'inline-block'}),
    ], style={'marginBottom': '20px'}),
    
    # Main Charts Row
    html.Div([
        html.Div([
            dcc.Graph(id='price-chart', config={'displayModeBar': False}),
        ], style={'width': '66%', 'display': 'inline-block', 'verticalAlign': 'top'}),
        
        html.Div([
            dcc.Graph(id='orderbook-chart', config={'displayModeBar': False}),
        ], style={'width': '33%', 'display': 'inline-block', 'verticalAlign': 'top'}),
    ], className='no-print'),
    
    # Secondary Charts Row
    html.Div([
        html.Div([
            dcc.Graph(id='volume-chart', config={'displayModeBar': False}),
        ], style={'width': '50%', 'display': 'inline-block'}),
        
        html.Div([
            dcc.Graph(id='pnl-chart', config={'displayModeBar': False}),
        ], style={'width': '50%', 'display': 'inline-block'}),
    ], className='no-print'),
    
    # Technical Analysis Charts Row
    html.Div([
        html.Div([
            dcc.Graph(id='rsi-chart', config={'displayModeBar': False}),
        ], style={'width': '33%', 'display': 'inline-block'}),
        
        html.Div([
            dcc.Graph(id='ma-chart', config={'displayModeBar': False}),
        ], style={'width': '33%', 'display': 'inline-block'}),
        
        html.Div([
            dcc.Graph(id='spread-chart', config={'displayModeBar': False}),
        ], style={'width': '33%', 'display': 'inline-block'}),
    ], className='no-print'),
    
    # Trade Analytics Row
    html.Div([
        html.Div([
            dcc.Graph(id='trade-distribution-chart', config={'displayModeBar': False}),
        ], style={'width': '50%', 'display': 'inline-block'}),
        
        html.Div([
            dcc.Graph(id='cumulative-return-chart', config={'displayModeBar': False}),
        ], style={'width': '50%', 'display': 'inline-block'}),
    ], className='no-print'),
    
    # Performance Metrics and Logs
    html.Div([
        html.Div([
            html.H3("Performance Metrics", style={'color': '#ffffff', 'marginBottom': '15px'}),
            html.Div(id='performance-table', style={'color': '#e0e0e0'}),
        ], style={'width': '50%', 'display': 'inline-block', 'backgroundColor': '#1e2130', 
                  'padding': '20px', 'borderRadius': '10px', 'marginRight': '10px', 'verticalAlign': 'top'}),
        
        html.Div([
            html.H3("Recent Activity Log", style={'color': '#ffffff', 'marginBottom': '15px'}),
            html.Div(id='activity-log', style={'height': '200px', 'overflowY': 'scroll', 
                                                'backgroundColor': '#0e1117', 'padding': '10px',
                                                'borderRadius': '5px', 'fontFamily': 'monospace',
                                                'fontSize': '12px', 'color': '#a0a0a0'}),
        ], style={'width': '48%', 'display': 'inline-block', 'backgroundColor': '#1e2130', 
                  'padding': '20px', 'borderRadius': '10px', 'verticalAlign': 'top'}),
    ]),
    
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
                trader = Trade(trade_mode='paper')
                is_running = True
                trader_thread = threading.Thread(target=trader.run, daemon=True)
                trader_thread.start()
                logger.info("Trading bot started")
                return "✅ Bot started successfully", {'color': '#00c853'}
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
    Input('interval-component', 'n_intervals')
)
def update_status(n):
    global is_running
    
    if is_running:
        return html.Span([
            html.Span(className='status-indicator status-running'),
            "Running"
        ])
    else:
        return html.Span([
            html.Span(className='status-indicator status-stopped'),
            "Stopped"
        ])


# Callback: Update metrics
@app.callback(
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
    Output('datapoints-metric', 'children'),
    Output('data-coverage', 'children'),
    Input('interval-component', 'n_intervals')
)
def update_metrics(n):
    global trader, chart_data, performance_metrics
    
    if not trader or not is_running:
        return ("--", "No data", "metric-change neutral", 
                "NONE", "No position", 
                "$0.00", "0.0%", "metric-change neutral",
                "0", "Win Rate: 0%",
                "0", "0/1440 mins")
    
    try:
        # Price metrics
        price = trader.current_price or 0
        price_str = f"${price:,.2f}" if price else "--"
        
        # Calculate price change
        price_change = 0
        price_change_pct = 0
        if len(chart_data['prices']) > 1:
            old_price = list(chart_data['prices'])[0]
            if old_price:
                price_change = price - old_price
                price_change_pct = (price_change / old_price) * 100
        
        price_change_str = f"{'+' if price_change >= 0 else ''}{price_change:.2f} ({price_change_pct:+.2f}%)"
        price_change_class = "metric-change positive" if price_change >= 0 else "metric-change negative"
        
        # Position metrics
        position = trader.current_position
        if position:
            position_side = position['side'].upper()
            position_qty = position['quantity']
            position_str = f"{position_side}"
            position_size_str = f"{position_qty:.6f} BTC"
            
            # Calculate P&L
            entry_price = position['entry_price']
            current_price = price
            if position['side'] == 'long':
                pnl = (current_price - entry_price) * position_qty
            else:
                pnl = (entry_price - current_price) * position_qty
            
            pnl_pct = (pnl / (entry_price * position_qty)) * 100
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
        
        # Data points
        data_points = len(trader.trade_px_list)
        coverage = (data_points / 1440) * 100
        coverage_str = f"{data_points}/1440 mins ({coverage:.0f}%)"
        
        # Update chart data
        if price:
            chart_data['timestamps'].append(datetime.now())
            chart_data['prices'].append(price)
            chart_data['volumes'].append(trader.current_volume or 0)
            
            if trader.orderbook:
                chart_data['bid_depth'].append(trader.orderbook.get('bid_depth', 0))
                chart_data['ask_depth'].append(trader.orderbook.get('ask_depth', 0))
        
        return (price_str, price_change_str, price_change_class,
                position_str, position_size_str,
                pnl_str, pnl_pct_str, pnl_class,
                str(trades_count), win_rate_str,
                str(data_points), coverage_str)
    
    except Exception as e:
        logger.error(f"Error updating metrics: {str(e)}")
        return ("Error", "Error", "metric-change neutral",
                "Error", "Error",
                "Error", "Error", "metric-change neutral",
                "Error", "Error",
                "Error", "Error")


# Callback: Update price chart
@app.callback(
    Output('price-chart', 'figure'),
    Input('interval-component', 'n_intervals')
)
def update_price_chart(n):
    global chart_data
    
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.7, 0.3],
        subplot_titles=('BTC/USDT Price', 'Order Book Depth')
    )
    
    if len(chart_data['timestamps']) > 0:
        # Price line
        fig.add_trace(
            go.Scatter(
                x=list(chart_data['timestamps']),
                y=list(chart_data['prices']),
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
                x=list(chart_data['timestamps']),
                y=list(chart_data['bid_depth']),
                mode='lines',
                name='Bid Depth',
                line=dict(color='#00c853', width=1.5)
            ),
            row=2, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=list(chart_data['timestamps']),
                y=list(chart_data['ask_depth']),
                mode='lines',
                name='Ask Depth',
                line=dict(color='#ff1744', width=1.5)
            ),
            row=2, col=1
        )
    
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
    
    fig.update_layout(
        title='Order Book Depth',
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


# Callback: Update volume chart
@app.callback(
    Output('volume-chart', 'figure'),
    Input('interval-component', 'n_intervals')
)
def update_volume_chart(n):
    global chart_data
    
    fig = go.Figure()
    
    if len(chart_data['timestamps']) > 0:
        fig.add_trace(go.Bar(
            x=list(chart_data['timestamps']),
            y=list(chart_data['volumes']),
            name='Volume',
            marker=dict(color='#764ba2')
        ))
    
    fig.update_layout(
        title='Trading Volume',
        template='plotly_dark',
        paper_bgcolor='#1e2130',
        plot_bgcolor='#1e2130',
        font=dict(color='#ffffff'),
        height=300,
        margin=dict(l=50, r=20, t=40, b=40),
        xaxis_title='Time',
        yaxis_title='Volume (BTC)',
        showlegend=False
    )
    
    return fig


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
    global trader, chart_data
    
    fig = go.Figure()
    
    if trader and len(trader.trade_px_list) >= 14:
        # Calculate RSI
        prices = list(trader.trade_px_list)
        period = 14
        
        if len(prices) >= period:
            deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
            gains = [d if d > 0 else 0 for d in deltas]
            losses = [-d if d < 0 else 0 for d in deltas]
            
            avg_gain = sum(gains[-period:]) / period
            avg_loss = sum(losses[-period:]) / period
            
            if avg_loss != 0:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
            else:
                rsi = 100
            
            chart_data['rsi'].append(rsi)
            
            if len(chart_data['timestamps']) > 0 and len(chart_data['rsi']) > 0:
                # Trim to match timestamps
                rsi_values = list(chart_data['rsi'])[-len(chart_data['timestamps']):]
                
                fig.add_trace(go.Scatter(
                    x=list(chart_data['timestamps'])[-len(rsi_values):],
                    y=rsi_values,
                    mode='lines',
                    name='RSI',
                    line=dict(color='#2196F3', width=2)
                ))
                
                # Add overbought/oversold lines
                fig.add_hline(y=70, line_dash="dash", line_color="#ff1744", line_width=1, annotation_text="Overbought")
                fig.add_hline(y=30, line_dash="dash", line_color="#00c853", line_width=1, annotation_text="Oversold")
                fig.add_hline(y=50, line_dash="dot", line_color="#666666", line_width=1)
    
    fig.update_layout(
        title='RSI Indicator (14)',
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
    global trader, chart_data
    
    fig = go.Figure()
    
    if trader and len(trader.trade_px_list) >= 50:
        prices = list(trader.trade_px_list)
        
        # Calculate MAs
        if len(prices) >= 20:
            ma_short = sum(prices[-20:]) / 20
            chart_data['ma_short'].append(ma_short)
        
        if len(prices) >= 50:
            ma_long = sum(prices[-50:]) / 50
            chart_data['ma_long'].append(ma_long)
        
        if len(chart_data['timestamps']) > 0:
            # Price line
            fig.add_trace(go.Scatter(
                x=list(chart_data['timestamps']),
                y=list(chart_data['prices']),
                mode='lines',
                name='Price',
                line=dict(color='#ffd600', width=2)
            ))
            
            # MA20
            if len(chart_data['ma_short']) > 0:
                ma_short_values = list(chart_data['ma_short'])[-len(chart_data['timestamps']):]
                fig.add_trace(go.Scatter(
                    x=list(chart_data['timestamps'])[-len(ma_short_values):],
                    y=ma_short_values,
                    mode='lines',
                    name='MA20',
                    line=dict(color='#00c853', width=1.5, dash='dash')
                ))
            
            # MA50
            if len(chart_data['ma_long']) > 0:
                ma_long_values = list(chart_data['ma_long'])[-len(chart_data['timestamps']):]
                fig.add_trace(go.Scatter(
                    x=list(chart_data['timestamps'])[-len(ma_long_values):],
                    y=ma_long_values,
                    mode='lines',
                    name='MA50',
                    line=dict(color='#ff1744', width=1.5, dash='dot')
                ))
    
    fig.update_layout(
        title='Moving Averages (MA20/MA50)',
        xaxis_title='Time',
        yaxis_title='Price (USD)',
        template='plotly_dark',
        paper_bgcolor='#1e2130',
        plot_bgcolor='#1e2130',
        height=300,
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
    
    fig.update_layout(
        title='Bid-Ask Spread %',
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
    global performance_metrics
    
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
    
    fig.update_layout(
        title='Trade Distribution',
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
    
    fig.update_layout(
        title='Cumulative Return',
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
    
    if trader:
        try:
            account = Account(trade_mode=trader.trade_mode)
            summary = account.get_transaction_summary()
            
            if summary:
                performance_metrics['total_trades'] = summary['buy_count'] + summary['sell_count']
                # Calculate win rate from realized P&L
                # This is simplified - you may want to enhance this
        except Exception as e:
            logger.error(f"Error getting account summary: {str(e)}")
    
    metrics = [
        ("Total Trades", performance_metrics['total_trades']),
        ("Winning Trades", performance_metrics['winning_trades']),
        ("Losing Trades", performance_metrics['losing_trades']),
        ("Win Rate", f"{performance_metrics['win_rate']:.1f}%"),
        ("Total P&L", f"${performance_metrics['total_pnl']:.2f}"),
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
            lines = f.readlines()[-20:]  # Last 20 lines
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
