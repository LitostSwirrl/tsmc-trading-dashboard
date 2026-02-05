"""
Dashboard Visualizations Module

Chart generation using Plotly.
"""

from typing import Optional
import pandas as pd
import numpy as np

try:
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False


class ChartGenerator:
    """Generate charts for dashboard visualization."""

    def __init__(self):
        """Initialize chart generator."""
        self.colors = {
            'primary': '#1f77b4',
            'success': '#2ecc71',
            'danger': '#e74c3c',
            'warning': '#f39c12',
            'neutral': '#95a5a6',
            'background': '#ffffff'
        }

    def plot_equity_curve(self, equity_data: pd.DataFrame, trades: pd.DataFrame = None) -> Optional[go.Figure]:
        """Plot equity curve with optional trade markers."""
        if not PLOTLY_AVAILABLE or equity_data.empty:
            return None

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=equity_data['date'],
            y=equity_data['equity'],
            mode='lines',
            name='Portfolio Value',
            line=dict(color=self.colors['primary'], width=2),
            fill='tozeroy',
            fillcolor='rgba(31, 119, 180, 0.1)'
        ))

        if trades is not None and not trades.empty:
            trades_with_dates = trades.copy()
            if 'date' in trades_with_dates.columns:
                trades_with_dates['date'] = pd.to_datetime(trades_with_dates['date'])

                # BUY markers
                buys = trades_with_dates[trades_with_dates['action'] == 'BUY']
                if not buys.empty:
                    buy_equities = []
                    for buy_date in buys['date']:
                        matching = equity_data[equity_data['date'].dt.date <= buy_date.date()]
                        if not matching.empty:
                            buy_equities.append(matching['equity'].iloc[-1])
                        else:
                            buy_equities.append(equity_data['equity'].iloc[0])

                    hover_texts = []
                    for _, trade in buys.iterrows():
                        qty = trade.get('quantity', 'N/A')
                        price = trade.get('price', 'N/A')
                        symbol = trade.get('symbol', '2330.TW')
                        hover_texts.append(f"BUY {symbol}<br>Qty: {qty}<br>Price: ${price:,.0f}" if isinstance(price, (int, float)) else f"BUY {symbol}")

                    fig.add_trace(go.Scatter(
                        x=buys['date'],
                        y=buy_equities,
                        mode='markers',
                        name='BUY',
                        marker=dict(
                            symbol='triangle-up',
                            size=14,
                            color=self.colors['success'],
                            line=dict(width=2, color='white')
                        ),
                        text=hover_texts,
                        hovertemplate='%{text}<br>Date: %{x|%Y-%m-%d}<extra></extra>'
                    ))

                # SELL markers
                sells = trades_with_dates[trades_with_dates['action'] == 'SELL']
                if not sells.empty:
                    sell_equities = []
                    for sell_date in sells['date']:
                        matching = equity_data[equity_data['date'].dt.date <= sell_date.date()]
                        if not matching.empty:
                            sell_equities.append(matching['equity'].iloc[-1])
                        else:
                            sell_equities.append(equity_data['equity'].iloc[0])

                    hover_texts = []
                    for _, trade in sells.iterrows():
                        qty = trade.get('quantity', 'N/A')
                        price = trade.get('price', 'N/A')
                        pnl = trade.get('pnl', 0)
                        symbol = trade.get('symbol', '2330.TW')
                        pnl_str = f"+${pnl:,.0f}" if pnl >= 0 else f"-${abs(pnl):,.0f}"
                        hover_texts.append(f"SELL {symbol}<br>Qty: {qty}<br>Price: ${price:,.0f}<br>P&L: {pnl_str}" if isinstance(price, (int, float)) else f"SELL {symbol}")

                    fig.add_trace(go.Scatter(
                        x=sells['date'],
                        y=sell_equities,
                        mode='markers',
                        name='SELL',
                        marker=dict(
                            symbol='triangle-down',
                            size=14,
                            color=self.colors['danger'],
                            line=dict(width=2, color='white')
                        ),
                        text=hover_texts,
                        hovertemplate='%{text}<br>Date: %{x|%Y-%m-%d}<extra></extra>'
                    ))

        if 'equity' in equity_data.columns and len(equity_data) > 0:
            initial = equity_data['equity'].iloc[0]
            fig.add_hline(
                y=initial,
                line_dash="dash",
                line_color=self.colors['neutral'],
                annotation_text="Initial Capital"
            )

        fig.update_layout(
            title='Portfolio Equity Curve',
            xaxis_title='Date',
            yaxis_title='Value (NTD)',
            hovermode='x unified',
            template='plotly_white',
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )

        return fig

    def plot_drawdown(self, drawdown_data: pd.DataFrame) -> Optional[go.Figure]:
        """Plot drawdown over time."""
        if not PLOTLY_AVAILABLE or drawdown_data.empty:
            return None

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=drawdown_data['date'],
            y=drawdown_data['drawdown'],
            mode='lines',
            name='Drawdown',
            line=dict(color=self.colors['danger'], width=2),
            fill='tozeroy',
            fillcolor='rgba(231, 76, 60, 0.2)'
        ))

        fig.update_layout(
            title='Portfolio Drawdown',
            xaxis_title='Date',
            yaxis_title='Drawdown (%)',
            hovermode='x unified',
            template='plotly_white',
        )

        return fig

    def plot_pnl_distribution(self, trades: pd.DataFrame) -> Optional[go.Figure]:
        """Plot P&L distribution histogram."""
        if not PLOTLY_AVAILABLE or trades.empty or 'pnl' not in trades.columns:
            return None

        pnl_values = trades['pnl'].dropna()

        fig = go.Figure()

        wins = pnl_values[pnl_values > 0]
        losses = pnl_values[pnl_values < 0]

        if len(wins) > 0:
            fig.add_trace(go.Histogram(
                x=wins, name='Winning Trades',
                marker_color=self.colors['success'], opacity=0.7
            ))

        if len(losses) > 0:
            fig.add_trace(go.Histogram(
                x=losses, name='Losing Trades',
                marker_color=self.colors['danger'], opacity=0.7
            ))

        fig.update_layout(
            title='P&L Distribution',
            xaxis_title='P&L (NTD)',
            yaxis_title='Count',
            barmode='overlay',
            template='plotly_white'
        )

        return fig

    def plot_cumulative_pnl(self, trades: pd.DataFrame) -> Optional[go.Figure]:
        """Plot cumulative P&L over time."""
        if not PLOTLY_AVAILABLE or trades.empty:
            return None

        if 'pnl' not in trades.columns or 'date' not in trades.columns:
            return None

        trades_sorted = trades.sort_values('date').copy()
        trades_sorted['cumulative_pnl'] = trades_sorted['pnl'].cumsum()

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=trades_sorted['date'],
            y=trades_sorted['cumulative_pnl'],
            mode='lines+markers',
            name='Cumulative P&L',
            line=dict(color=self.colors['primary'], width=2),
            marker=dict(size=6)
        ))

        fig.add_hline(y=0, line_dash="dash", line_color=self.colors['neutral'])

        fig.update_layout(
            title='Cumulative P&L',
            xaxis_title='Date',
            yaxis_title='Cumulative P&L (NTD)',
            hovermode='x unified',
            template='plotly_white'
        )

        return fig
