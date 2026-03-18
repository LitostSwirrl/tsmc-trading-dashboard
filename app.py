"""
TSMC Trading Bot Dashboard

Streamlit-based web dashboard for monitoring paper trading.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from pathlib import Path

from src.metrics import DashboardMetrics
from src.data_loader import DashboardDataLoader
from src.visualizations import ChartGenerator

# Page configuration
st.set_page_config(
    page_title="TSMC Trading Bot",
    page_icon="T",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; }
    .stMetric > div { background: #f8f9fa; padding: 12px 16px; border-radius: 8px; }
    div[data-testid="stSidebar"] > div:first-child { padding-top: 1rem; }
    .sidebar-title {
        font-size: 1.3rem; font-weight: 700; color: #1f77b4;
        cursor: pointer; margin-bottom: 0.2rem;
    }
    .sidebar-title:hover { text-decoration: underline; }
    .sidebar-subtitle { font-size: 0.8rem; color: #666; margin-bottom: 1rem; }
    /* Fix: selected menu icon invisible on blue bg — target all possible icon elements */
    .nav-link.nav-link-selected * { color: white !important; fill: white !important; }
    a.nav-link.nav-link-selected span { color: white !important; }
    [class*="nav-link-selected"] * { color: white !important; }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def init_dashboard():
    """Initialize dashboard components."""
    try:
        data_loader = DashboardDataLoader()
        metrics = DashboardMetrics()
        chart_gen = ChartGenerator()
        return data_loader, metrics, chart_gen
    except Exception as e:
        st.error(f"Failed to initialize dashboard: {e}")
        return None, None, None


def render_sidebar():
    """Render sidebar with navigation."""
    # Title links back to Overview via query param
    st.sidebar.markdown(
        '<a href="?page=Overview" target="_self" style="text-decoration:none;">'
        '<div class="sidebar-title">TSMC Trading Bot</div></a>',
        unsafe_allow_html=True
    )
    st.sidebar.markdown('<div class="sidebar-subtitle">Paper Trading Dashboard</div>', unsafe_allow_html=True)
    st.sidebar.markdown("---")

    try:
        from streamlit_option_menu import option_menu
        # Check for query param override (from title click)
        query_page = st.query_params.get("page", None)
        pages = ["Overview", "Price Chart", "Performance", "Trades", "Risk"]
        default_idx = pages.index(query_page) if query_page in pages else 0

        with st.sidebar:
            page = option_menu(
                None,
                pages,
                icons=["speedometer2", "graph-up-arrow", "bar-chart-line", "arrow-left-right", "shield-check"],
                menu_icon="cast",
                default_index=default_idx,
                orientation="vertical",
                styles={
                    "container": {"padding": "4px !important", "background-color": "transparent"},
                    "icon": {"color": "#1f77b4", "font-size": "16px"},
                    "nav-link": {
                        "font-size": "14px", "text-align": "left", "margin": "2px 0",
                        "padding": "8px 12px", "border-radius": "6px",
                    },
                    "nav-link-selected": {
                        "background-color": "#1f77b4", "color": "white", "font-weight": "600",
                    },
                }
            )
    except ImportError:
        page = st.sidebar.radio(
            "Navigation",
            ["Overview", "Price Chart", "Performance", "Trades", "Risk"],
            index=0
        )

    st.sidebar.markdown("---")
    st.sidebar.subheader("Date Range")
    lookback_days = st.sidebar.selectbox(
        "Lookback Period",
        [7, 30, 90, 180, 365, "All"],
        index=2
    )

    st.sidebar.markdown("---")
    st.sidebar.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    return page, lookback_days if lookback_days != "All" else None


@st.cache_data(ttl=3600)
def fetch_tsmc_price(days: int) -> pd.DataFrame:
    """Fetch TSMC price data from Yahoo Finance (cached 1 hour)."""
    try:
        import yfinance as yf
        period_map = {7: "1mo", 30: "3mo", 90: "6mo", 180: "1y", 365: "2y"}
        period = period_map.get(days, "1y")
        df = yf.download("2330.TW", period=period, progress=False)
        if df.empty:
            return pd.DataFrame()
        # Flatten MultiIndex columns: ('Close', '2330.TW') -> 'close'
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0].lower() for c in df.columns]
        else:
            df.columns = [c.lower() for c in df.columns]
        df = df.reset_index()
        # reset_index may produce 'Date' or 'date'
        df.columns = [c.lower() if isinstance(c, str) else c for c in df.columns]
        return df
    except Exception as e:
        return pd.DataFrame()


def render_price_chart(data_loader, chart_gen, days):
    """Render TSMC price chart with trade markers."""
    st.header("TSMC (2330.TW) Price Chart")

    price_days = days or 365
    price_data = fetch_tsmc_price(price_days)
    trades = data_loader.get_trade_history(days=days)

    if not price_data.empty:
        fig = chart_gen.plot_price_chart(price_data, trades)
        if fig:
            st.plotly_chart(fig, use_container_width=True, key=f"price_{days}")
    else:
        st.warning("Could not fetch TSMC price data. Please try again later.")


def format_trades_table(trades: pd.DataFrame) -> pd.DataFrame:
    """Format trades DataFrame for display."""
    display = trades.copy()
    if 'price' in display.columns:
        display['price'] = display['price'].apply(lambda x: f"${x:,.0f}" if pd.notna(x) else "")
    if 'cost' in display.columns:
        display['cost'] = display['cost'].apply(lambda x: f"${x:,.0f}" if pd.notna(x) else "")
    if 'pnl' in display.columns:
        display['pnl'] = display['pnl'].apply(
            lambda x: f"${x:+,.0f}" if pd.notna(x) and x != 0 else ""
        )
    if 'pnl_pct' in display.columns:
        display['pnl_pct'] = display['pnl_pct'].apply(
            lambda x: f"{x:+.1f}%" if pd.notna(x) and x != 0 else ""
        )
    if 'confidence' in display.columns:
        display['confidence'] = display['confidence'].apply(
            lambda x: f"{x:.0%}" if pd.notna(x) and isinstance(x, float) and x <= 1 else (f"{x:.1f}%" if pd.notna(x) else "")
        )
    if 'date' in display.columns:
        display['date'] = pd.to_datetime(display['date']).dt.strftime('%Y-%m-%d')

    rename_map = {
        'date': 'Date', 'action': 'Action', 'symbol': 'Symbol',
        'shares': 'Shares', 'price': 'Price', 'cost': 'Cost',
        'pnl': 'P&L', 'pnl_pct': 'P&L %', 'confidence': 'Confidence',
        'regime': 'Regime'
    }
    display = display.rename(columns={k: v for k, v in rename_map.items() if k in display.columns})
    return display


def render_overview(data_loader, metrics, chart_gen, days):
    """Render overview page."""
    st.header("Trading Bot Overview")

    portfolio = data_loader.get_portfolio_status()

    has_position = len(portfolio.get('positions', {})) > 0
    position_label = "LONG" if has_position else "No Position"

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Equity", f"${portfolio['total_equity']:,.0f}",
                  f"{portfolio['total_return_pct']:+.2f}%")
    with col2:
        st.metric("Cash", f"${portfolio['cash']:,.0f}")
    with col3:
        st.metric("Invested", f"${portfolio['invested']:,.0f}")
    with col4:
        st.metric("TSMC Position", position_label)

    st.markdown("---")

    # Equity curve
    st.subheader("Portfolio Value Over Time")
    st.caption(f"Initial capital: $100,000 NTD | Long-only TSMC (2330.TW) | Odd-lot trading")
    equity_data = data_loader.get_equity_curve(days=days)
    trades = data_loader.get_trade_history(days=days)

    if not equity_data.empty:
        fig = chart_gen.plot_equity_curve(equity_data, trades)
        if fig:
            st.plotly_chart(fig, use_container_width=True, key=f"equity_{days}")
    else:
        st.info("No equity data available yet. Paper trading will populate this chart.")

    # Trade statistics
    st.markdown("---")
    st.subheader("Trade Statistics")
    trade_stats = metrics.get_trade_statistics()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Trades", trade_stats.get('closed_trades', trade_stats['total_trades']))
    with col2:
        st.metric("Win Rate", f"{trade_stats['win_rate']:.1f}%")
    with col3:
        st.metric("Total P&L", f"${trade_stats['total_pnl']:,.0f}")
    with col4:
        st.metric("Avg P&L", f"${trade_stats['avg_pnl']:,.0f}")


def render_performance(data_loader, metrics, chart_gen, days):
    """Render performance page."""
    st.header("Performance Metrics")

    perf = metrics.get_performance_metrics(days=days or 30)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Return", f"{perf.get('total_return_pct', 0):.2f}%")
    with col2:
        st.metric("Sharpe Ratio", f"{perf.get('sharpe_ratio', 0):.2f}")
    with col3:
        st.metric("Volatility", f"{perf.get('volatility', 0):.1f}%")
    with col4:
        st.metric("Win Rate", f"{perf.get('win_rate', 0)*100:.1f}%")

    st.markdown("---")
    st.subheader("Drawdown")

    drawdown_data = data_loader.get_drawdown_data(days=days)
    if not drawdown_data.empty:
        fig = chart_gen.plot_drawdown(drawdown_data)
        if fig:
            st.plotly_chart(fig, use_container_width=True, key=f"drawdown_{days}")
    else:
        st.info("No drawdown data available yet.")


def render_trades(data_loader, metrics, chart_gen, days):
    """Render trades page."""
    st.header("Trade History")

    trades = data_loader.get_trade_history(days=days)

    if not trades.empty:
        st.subheader("Recent Trades")
        display = format_trades_table(trades.sort_values('date', ascending=False))
        st.dataframe(display, use_container_width=True, hide_index=True)

        st.markdown("---")

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("P&L Distribution")
            fig = chart_gen.plot_pnl_distribution(trades)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("P&L data not available yet.")

        with col2:
            st.subheader("Cumulative P&L")
            fig = chart_gen.plot_cumulative_pnl(trades)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("P&L data not available yet.")
    else:
        st.info("No trades executed yet. The bot is waiting for high-confidence signals.")


def render_risk(data_loader, metrics, chart_gen, days):
    """Render risk page."""
    st.header("Risk Management")

    risk_status = data_loader.get_risk_status()

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Portfolio Exposure")
        exposure_pct = risk_status['portfolio_exposure'] * 100
        max_exposure_pct = risk_status['max_exposure'] * 100
        st.progress(min(exposure_pct / max_exposure_pct, 1.0) if max_exposure_pct > 0 else 0.0)
        st.caption(f"{exposure_pct:.1f}% / {max_exposure_pct:.0f}% max")

    with col2:
        st.subheader("Positions")
        num_pos = risk_status['num_positions']
        max_pos = risk_status['max_positions']
        st.progress(min(num_pos / max_pos, 1.0) if max_pos > 0 else 0.0)
        st.caption(f"{num_pos} / {max_pos} max")

    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Current Drawdown", f"{risk_status['current_drawdown']*100:.2f}%")
    with col2:
        st.metric("Max Drawdown Limit", f"{risk_status['max_drawdown_limit']*100:.0f}%")


def main():
    """Main dashboard application."""
    data_loader, metrics, chart_gen = init_dashboard()

    if data_loader is None:
        st.error("Failed to initialize dashboard components.")
        return

    page, days = render_sidebar()

    if page == "Overview":
        render_overview(data_loader, metrics, chart_gen, days)
    elif page == "Price Chart":
        render_price_chart(data_loader, chart_gen, days)
    elif page == "Performance":
        render_performance(data_loader, metrics, chart_gen, days)
    elif page == "Trades":
        render_trades(data_loader, metrics, chart_gen, days)
    elif page == "Risk":
        render_risk(data_loader, metrics, chart_gen, days)


if __name__ == "__main__":
    main()
