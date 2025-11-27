#!/bin/bash
# Quick start script for WOOX Trading Bot Dashboard

echo "=========================================="
echo "🚀 Starting WOOX Trading Bot Dashboard"
echo "=========================================="
echo ""

# Check if dependencies are installed
if ! python -c "import dash" 2>/dev/null; then
    echo "⚠️  Installing required dependencies..."
    pip install dash plotly pandas -q
fi

# Run the dashboard
echo "📊 Starting dashboard on http://127.0.0.1:8050"
echo ""
echo "💡 Use Ctrl+C to stop the dashboard"
echo ""

python dashboard.py
