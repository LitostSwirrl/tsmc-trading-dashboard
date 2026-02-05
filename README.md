# TSMC Trading Bot Dashboard

A Streamlit dashboard for monitoring paper trading of TSMC (2330.TW) stock.

## Features

- **Overview**: Portfolio value, equity curve, trade statistics
- **Performance**: Sharpe ratio, drawdown, volatility metrics
- **Trades**: Trade history and P&L analysis
- **Risk**: Portfolio exposure and position limits

## Live Dashboard

Visit: [Your Streamlit Cloud URL]

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run dashboard
streamlit run app.py
```

## Data Sync

The dashboard reads from `data/paper_trading/` directory:
- `portfolio_state.json` - Current portfolio status
- `trade_history.json` - Trade records
- `daily_logs/*.json` - Daily equity snapshots

To sync data from the trading bot, update these files.

## Demo Mode

Enable "Show Demo Data" in the sidebar to preview charts with sample data.
