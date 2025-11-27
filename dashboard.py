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
    'ask_depth': deque(maxlen=500)
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
            .control-button:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 8px rgba(0,0,0,0.3);
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
            html.Div(id='control-feedback', style={'color': '#ffffff', 'marginTop': '10px', 'fontSize': '14px'})
        ]),
    ], style={'backgroundColor': '#1e2130', 'padding': '20px', 'borderRadius': '10px', 'marginBottom': '20px'}),
    
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
    ]),
    
    # Secondary Charts Row
    html.Div([
        html.Div([
            dcc.Graph(id='volume-chart', config={'displayModeBar': False}),
        ], style={'width': '50%', 'display': 'inline-block'}),
        
        html.Div([
            dcc.Graph(id='pnl-chart', config={'displayModeBar': False}),
        ], style={'width': '50%', 'display': 'inline-block'}),
    ]),
    
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
    prevent_initial_call=True
)
def control_bot(start_clicks, stop_clicks, close_clicks):
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
