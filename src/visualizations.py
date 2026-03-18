"""
Dashboard Visualizations Module

Chart generation using Plotly.
"""

from typing import Optional, List
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

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
            fillcolor='rgba(31, 119, 180, 0.1)',
            hovertemplate='%{x|%Y-%m-%d}<br>Value: $%{y:,.0f}<extra></extra>'
        ))

        if trades is not None and not trades.empty:
            trades_with_dates = trades.copy()
            if 'date' in trades_with_dates.columns:
                trades_with_dates['date'] = pd.to_datetime(trades_with_dates['date'])

                for action, color, symbol_shape, direction in [
                    ('BUY', self.colors['success'], 'triangle-up', 'Buy'),
                    ('SELL', self.colors['danger'], 'triangle-down', 'Sell')
                ]:
                    action_trades = trades_with_dates[trades_with_dates['action'] == action]
                    if action_trades.empty:
                        continue

                    equities = []
                    for trade_date in action_trades['date']:
                        matching = equity_data[equity_data['date'].dt.date <= trade_date.date()]
                        equities.append(matching['equity'].iloc[-1] if not matching.empty else equity_data['equity'].iloc[0])

                    hover_texts = []
                    for _, trade in action_trades.iterrows():
                        qty = trade.get('shares', trade.get('quantity', 'N/A'))
                        price = trade.get('price', 0)
                        text = f"{action} {trade.get('symbol', '2330')}<br>Qty: {qty}<br>Price: ${price:,.0f}"
                        if action == 'SELL' and 'pnl' in trade and trade['pnl'] != 0:
                            pnl = trade['pnl']
                            text += f"<br>P&L: ${pnl:+,.0f}"
                        hover_texts.append(text)

                    fig.add_trace(go.Scatter(
                        x=action_trades['date'],
                        y=equities,
                        mode='markers',
                        name=action,
                        marker=dict(symbol=symbol_shape, size=14, color=color,
                                    line=dict(width=2, color='white')),
                        text=hover_texts,
                        hovertemplate='%{text}<br>Date: %{x|%Y-%m-%d}<extra></extra>'
                    ))

        if 'equity' in equity_data.columns and len(equity_data) > 0:
            initial = equity_data['equity'].iloc[0]
            fig.add_hline(y=initial, line_dash="dash", line_color=self.colors['neutral'],
                         annotation_text="Initial Capital",
                         annotation_position="bottom left",
                         annotation=dict(font_size=11, font_color=self.colors['neutral']))

        fig.update_layout(
            title='Portfolio Equity Curve',
            xaxis_title='Date',
            yaxis_title='Value (NTD)',
            hovermode='x unified',
            template='plotly_white',
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            xaxis=dict(type='date', tickformat='%Y-%m-%d', tickangle=-45),
            yaxis=dict(tickformat='$,.0f'),
        )

        return fig

    def plot_drawdown(self, drawdown_data: pd.DataFrame) -> Optional[go.Figure]:
        """Plot drawdown over time."""
        if not PLOTLY_AVAILABLE or drawdown_data.empty:
            return None

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=drawdown_data['date'],
            y=drawdown_data['drawdown'] * 100,
            mode='lines',
            name='Drawdown',
            line=dict(color=self.colors['danger'], width=2),
            fill='tozeroy',
            fillcolor='rgba(231, 76, 60, 0.2)',
            hovertemplate='%{x|%Y-%m-%d}<br>Drawdown: %{y:.2f}%<extra></extra>'
        ))

        fig.update_layout(
            title='Portfolio Drawdown',
            xaxis_title='Date',
            yaxis_title='Drawdown from Peak (%)',
            hovermode='x unified',
            template='plotly_white',
            xaxis=dict(type='date', tickformat='%Y-%m-%d', tickangle=-45),
            yaxis=dict(tickformat='.1f', ticksuffix='%'),
        )

        return fig

    def plot_pnl_distribution(self, trades: pd.DataFrame) -> Optional[go.Figure]:
        """Plot P&L distribution histogram."""
        if not PLOTLY_AVAILABLE or trades.empty or 'pnl' not in trades.columns:
            return None

        pnl_values = trades['pnl'].dropna()
        pnl_values = pnl_values[pnl_values != 0]

        if pnl_values.empty:
            return None

        fig = go.Figure()

        wins = pnl_values[pnl_values > 0]
        losses = pnl_values[pnl_values < 0]

        if len(wins) > 0:
            fig.add_trace(go.Histogram(
                x=wins, name='Winning Trades',
                marker_color=self.colors['success'], opacity=0.7,
                hovertemplate='P&L: $%{x:,.0f}<br>Count: %{y}<extra></extra>'
            ))

        if len(losses) > 0:
            fig.add_trace(go.Histogram(
                x=losses, name='Losing Trades',
                marker_color=self.colors['danger'], opacity=0.7,
                hovertemplate='P&L: $%{x:,.0f}<br>Count: %{y}<extra></extra>'
            ))

        fig.update_layout(
            title='P&L Distribution',
            xaxis_title='P&L (NTD)',
            yaxis_title='Count',
            barmode='overlay',
            template='plotly_white',
            xaxis=dict(tickformat='$,.0f'),
        )

        return fig

    def plot_cumulative_pnl(self, trades: pd.DataFrame) -> Optional[go.Figure]:
        """Plot cumulative P&L over time."""
        if not PLOTLY_AVAILABLE or trades.empty:
            return None

        if 'pnl' not in trades.columns or 'date' not in trades.columns:
            return None

        # Only include SELL trades (which have P&L)
        sell_trades = trades[trades['action'] == 'SELL'].copy() if 'action' in trades.columns else trades.copy()
        if sell_trades.empty or sell_trades['pnl'].sum() == 0:
            return None

        sell_trades = sell_trades.sort_values('date')
        sell_trades['cumulative_pnl'] = sell_trades['pnl'].cumsum()

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=sell_trades['date'],
            y=sell_trades['cumulative_pnl'],
            mode='lines+markers',
            name='Cumulative P&L',
            line=dict(color=self.colors['primary'], width=2),
            marker=dict(size=6),
            hovertemplate='%{x|%Y-%m-%d}<br>Cumulative P&L: $%{y:,.0f}<extra></extra>'
        ))

        fig.add_hline(y=0, line_dash="dash", line_color=self.colors['neutral'])

        fig.update_layout(
            title='Cumulative P&L',
            xaxis_title='Date',
            yaxis_title='Cumulative P&L (NTD)',
            hovermode='x unified',
            template='plotly_white',
            xaxis=dict(type='date', tickformat='%Y-%m-%d', tickangle=-45),
            yaxis=dict(tickformat='$,.0f'),
        )

        return fig

    def plot_price_chart(self, price_data: pd.DataFrame, trades: pd.DataFrame = None) -> Optional[go.Figure]:
        """Plot TSMC price candlestick chart with trade markers and volume."""
        if not PLOTLY_AVAILABLE or price_data.empty:
            return None

        from plotly.subplots import make_subplots

        fig = make_subplots(
            rows=2, cols=1, shared_xaxes=True,
            vertical_spacing=0.03, row_heights=[0.75, 0.25],
        )

        fig.add_trace(go.Candlestick(
            x=price_data['date'],
            open=price_data['open'], high=price_data['high'],
            low=price_data['low'], close=price_data['close'],
            name='TSMC 2330',
            increasing_line_color=self.colors['success'],
            decreasing_line_color=self.colors['danger'],
        ), row=1, col=1)

        vol_colors = [self.colors['success'] if c >= o else self.colors['danger']
                      for c, o in zip(price_data['close'], price_data['open'])]
        fig.add_trace(go.Bar(
            x=price_data['date'], y=price_data['volume'],
            name='Volume', marker_color=vol_colors, opacity=0.5,
            showlegend=False,
            hovertemplate='%{x|%Y-%m-%d}<br>Vol: %{y:,.0f}<extra></extra>'
        ), row=2, col=1)

        if trades is not None and not trades.empty:
            tp = trades.copy()
            tp['date'] = pd.to_datetime(tp['date'])
            for action, color, shape in [
                ('BUY', self.colors['success'], 'triangle-up'),
                ('SELL', self.colors['danger'], 'triangle-down'),
            ]:
                subset = tp[tp['action'] == action]
                if subset.empty:
                    continue
                hovers = []
                for _, t in subset.iterrows():
                    h = f"{action} {t.get('shares', '')}sh @ ${t.get('price', 0):,.0f}"
                    if action == 'SELL' and t.get('pnl', 0) != 0:
                        h += f"<br>P&L: ${t['pnl']:+,.0f}"
                    hovers.append(h)
                fig.add_trace(go.Scatter(
                    x=subset['date'], y=subset['price'],
                    mode='markers', name=action,
                    marker=dict(symbol=shape, size=14, color=color,
                                line=dict(width=2, color='white')),
                    text=hovers,
                    hovertemplate='%{text}<br>%{x|%Y-%m-%d}<extra></extra>'
                ), row=1, col=1)

        fig.update_layout(
            title='TSMC (2330.TW) — Trade Decisions on Price Chart (NTD)',
            hovermode='x unified', template='plotly_white',
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            xaxis2=dict(type='date', tickformat='%Y-%m-%d', tickangle=-45),
            yaxis=dict(title='Price (NTD)', tickformat=',.0f'),
            yaxis2=dict(title='Volume'),
            xaxis_rangeslider_visible=False, height=620,
        )
        return fig
