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
    page_title="TSMC Trading Bot Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .big-metric { font-size: 2rem; font-weight: bold; }
    .positive { color: #00c853; }
    .negative { color: #d32f2f; }
    .neutral { color: #ffa726; }
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
    """Render sidebar with navigation and filters."""
    st.sidebar.title("📊 TSMC Trading Bot")
    st.sidebar.markdown("---")

    page = st.sidebar.radio(
        "Navigation",
        ["Overview", "Performance", "Trades", "Risk"],
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
    st.sidebar.subheader("Demo Mode")
    demo_mode = st.sidebar.checkbox(
        "Show Demo Data", value=False,
        help="Display sample data to preview charts"
    )
    if demo_mode:
        st.sidebar.info("📊 Showing demo data with sample trades")

    st.sidebar.markdown("---")
    st.sidebar.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    return page, lookback_days if lookback_days != "All" else None, demo_mode


def render_overview(data_loader, metrics, chart_gen, days, demo_mode):
    """Render overview page."""
    st.title("📈 Trading Bot Overview")

    # Portfolio summary
    portfolio = data_loader.get_portfolio_status()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Total Equity",
            f"${portfolio['total_equity']:,.0f}",
            f"{portfolio['total_return_pct']:+.2f}%"
        )

    with col2:
        st.metric("Cash", f"${portfolio['cash']:,.0f}")

    with col3:
        st.metric("Invested", f"${portfolio['invested']:,.0f}")

    with col4:
        num_positions = len(portfolio.get('positions', {}))
        st.metric("Positions", num_positions)

    st.markdown("---")

    # Equity curve
    st.subheader("Portfolio Value Over Time")

    if demo_mode:
        equity_data = data_loader.get_demo_equity_curve(days=days or 60)
        trades = data_loader.get_demo_trade_history()
    else:
        equity_data = data_loader.get_equity_curve(days=days)
        trades = data_loader.get_trade_history(days=days)

    if not equity_data.empty:
        fig = chart_gen.plot_equity_curve(equity_data, trades)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No equity data available yet. Paper trading will populate this chart.")

    # Trade statistics
    st.markdown("---")
    st.subheader("Trade Statistics")

    trade_stats = metrics.get_trade_statistics()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Trades", trade_stats['total_trades'])

    with col2:
        st.metric("Win Rate", f"{trade_stats['win_rate']:.1f}%")

    with col3:
        st.metric("Total P&L", f"${trade_stats['total_pnl']:,.0f}")

    with col4:
        st.metric("Avg P&L", f"${trade_stats['avg_pnl']:,.0f}")


def render_performance(data_loader, metrics, chart_gen, days, demo_mode):
    """Render performance page."""
    st.title("📊 Performance Metrics")

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

    # Drawdown chart
    st.subheader("Drawdown")

    if demo_mode:
        equity_data = data_loader.get_demo_equity_curve(days=days or 60)
        if not equity_data.empty:
            running_max = equity_data['equity'].expanding().max()
            drawdown = (equity_data['equity'] - running_max) / running_max
            drawdown_data = pd.DataFrame({'date': equity_data['date'], 'drawdown': drawdown})
        else:
            drawdown_data = pd.DataFrame()
    else:
        drawdown_data = data_loader.get_drawdown_data(days=days)

    if not drawdown_data.empty:
        fig = chart_gen.plot_drawdown(drawdown_data)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No drawdown data available yet.")


def render_trades(data_loader, metrics, chart_gen, days, demo_mode):
    """Render trades page."""
    st.title("💰 Trade History")

    if demo_mode:
        trades = data_loader.get_demo_trade_history()
    else:
        trades = data_loader.get_trade_history(days=days)

    if not trades.empty:
        st.subheader("Recent Trades")
        st.dataframe(
            trades.sort_values('date', ascending=False),
            use_container_width=True,
            hide_index=True
        )

        st.markdown("---")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("P&L Distribution")
            fig = chart_gen.plot_pnl_distribution(trades)
            if fig:
                st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("Cumulative P&L")
            fig = chart_gen.plot_cumulative_pnl(trades)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No trades executed yet. The bot is waiting for high-confidence signals.")


def render_risk(data_loader, metrics, chart_gen, days, demo_mode):
    """Render risk page."""
    st.title("⚠️ Risk Management")

    risk_status = data_loader.get_risk_status()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Portfolio Exposure")
        exposure_pct = risk_status['portfolio_exposure'] * 100
        max_exposure_pct = risk_status['max_exposure'] * 100
        st.progress(min(exposure_pct / max_exposure_pct, 1.0))
        st.caption(f"{exposure_pct:.1f}% / {max_exposure_pct:.1f}% max")

    with col2:
        st.subheader("Positions")
        num_pos = risk_status['num_positions']
        max_pos = risk_status['max_positions']
        st.progress(min(num_pos / max_pos, 1.0))
        st.caption(f"{num_pos} / {max_pos} max")

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            "Current Drawdown",
            f"{risk_status['current_drawdown']*100:.2f}%",
            delta=None
        )

    with col2:
        st.metric(
            "Max Drawdown Limit",
            f"{risk_status['max_drawdown_limit']*100:.1f}%"
        )


def main():
    """Main dashboard application."""
    data_loader, metrics, chart_gen = init_dashboard()

    if data_loader is None:
        st.error("Failed to initialize dashboard components.")
        return

    page, days, demo_mode = render_sidebar()

    if page == "Overview":
        render_overview(data_loader, metrics, chart_gen, days, demo_mode)
    elif page == "Performance":
        render_performance(data_loader, metrics, chart_gen, days, demo_mode)
    elif page == "Trades":
        render_trades(data_loader, metrics, chart_gen, days, demo_mode)
    elif page == "Risk":
        render_risk(data_loader, metrics, chart_gen, days, demo_mode)


if __name__ == "__main__":
    main()
