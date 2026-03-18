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
        """Plot P&L distribution as a waterfall bar chart."""
        if not PLOTLY_AVAILABLE or trades.empty or 'pnl' not in trades.columns:
            return None

        pnl_values = trades['pnl'].dropna()
        pnl_values = pnl_values[pnl_values != 0]

        if pnl_values.empty:
            return None

        fig = go.Figure()

        # Individual trade P&L as a bar chart (sorted by value) — cleaner than histogram
        sorted_pnl = pnl_values.sort_values().reset_index(drop=True)
        bar_colors = ['rgba(231, 76, 60, 0.85)' if v < 0 else 'rgba(46, 204, 113, 0.85)' for v in sorted_pnl]
        border_colors = ['#c0392b' if v < 0 else '#27ae60' for v in sorted_pnl]

        fig.add_trace(go.Bar(
            x=list(range(len(sorted_pnl))),
            y=sorted_pnl,
            marker=dict(
                color=bar_colors,
                line=dict(width=1, color=border_colors),
            ),
            hovertemplate='Trade #%{x}<br>P&L: $%{y:,.0f}<extra></extra>',
            showlegend=False,
        ))

        # Zero line
        fig.add_hline(y=0, line_width=1.5, line_color='#555')

        # Annotations for summary stats
        avg_pnl = pnl_values.mean()
        total_pnl = pnl_values.sum()
        fig.add_annotation(
            text=f"Avg: ${avg_pnl:+,.0f} | Total: ${total_pnl:+,.0f}",
            xref="paper", yref="paper", x=0.5, y=1.08,
            showarrow=False, font=dict(size=12, color='#555'),
        )

        fig.update_layout(
            title='P&L per Trade',
            xaxis_title='Trades (sorted)',
            yaxis_title='P&L (NTD)',
            template='plotly_white',
            xaxis=dict(showticklabels=False),
            yaxis=dict(tickformat='$,.0f', zeroline=False),
            bargap=0.15,
            margin=dict(t=60),
        )

        return fig

    def plot_cumulative_pnl(self, trades: pd.DataFrame) -> Optional[go.Figure]:
        """Plot cumulative P&L over time with gradient fill."""
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

        cum_values = sell_trades['cumulative_pnl']
        final_val = cum_values.iloc[-1]
        is_positive = final_val >= 0

        # Gradient fill — green if net positive, red if net negative
        fill_color = 'rgba(46, 204, 113, 0.15)' if is_positive else 'rgba(231, 76, 60, 0.15)'
        line_color = '#27ae60' if is_positive else '#c0392b'

        fig.add_trace(go.Scatter(
            x=sell_trades['date'],
            y=cum_values,
            mode='lines+markers',
            name='Cumulative P&L',
            line=dict(color=line_color, width=2.5, shape='spline'),
            marker=dict(size=7, color=line_color, line=dict(width=1, color='white')),
            fill='tozeroy',
            fillcolor=fill_color,
            hovertemplate='%{x|%Y-%m-%d}<br>Cumulative P&L: $%{y:,.0f}<extra></extra>'
        ))

        # Zero line
        fig.add_hline(y=0, line_dash="dot", line_width=1, line_color='#999')

        # Annotate final value
        fig.add_annotation(
            x=sell_trades['date'].iloc[-1],
            y=final_val,
            text=f"${final_val:+,.0f}",
            showarrow=True, arrowhead=0, arrowcolor=line_color,
            font=dict(size=13, color=line_color, family='Arial Black'),
            bgcolor='white', bordercolor=line_color, borderwidth=1, borderpad=4,
        )

        # Annotate peak/trough
        peak_idx = cum_values.idxmax()
        trough_idx = cum_values.idxmin()
        if cum_values.loc[peak_idx] > 0:
            fig.add_annotation(
                x=sell_trades.loc[peak_idx, 'date'], y=cum_values.loc[peak_idx],
                text=f"Peak: ${cum_values.loc[peak_idx]:+,.0f}",
                showarrow=True, arrowhead=2, ay=-30,
                font=dict(size=10, color='#27ae60'), opacity=0.8,
            )
        if cum_values.loc[trough_idx] < 0:
            fig.add_annotation(
                x=sell_trades.loc[trough_idx, 'date'], y=cum_values.loc[trough_idx],
                text=f"Trough: ${cum_values.loc[trough_idx]:+,.0f}",
                showarrow=True, arrowhead=2, ay=30,
                font=dict(size=10, color='#c0392b'), opacity=0.8,
            )

        fig.update_layout(
            title='Cumulative P&L',
            xaxis_title='Date',
            yaxis_title='Cumulative P&L (NTD)',
            hovermode='x unified',
            template='plotly_white',
            xaxis=dict(type='date', tickformat='%Y-%m-%d', tickangle=-45),
            yaxis=dict(tickformat='$,.0f', zeroline=False),
            margin=dict(t=40),
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
            showlegend=False,
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
            marker_cfg = {
                'BUY': {'color': '#0066FF', 'shape': 'triangle-up', 'outline': '#001a44',
                         'vline': 'rgba(0, 102, 255, 0.22)'},
                'SELL': {'color': '#FF6600', 'shape': 'triangle-down', 'outline': '#441a00',
                          'vline': 'rgba(255, 102, 0, 0.22)'},
            }
            for action, cfg in marker_cfg.items():
                subset = tp[tp['action'] == action]
                if subset.empty:
                    continue

                # Dashed vertical lines spanning full chart height via shapes
                for trade_date in subset['date']:
                    date_str = trade_date.strftime('%Y-%m-%d')
                    fig.add_shape(
                        type='line',
                        x0=date_str, x1=date_str, y0=0, y1=1,
                        xref='x', yref='paper',
                        line=dict(color=cfg['vline'], width=1, dash='dash'),
                        layer='below',
                    )

                hovers = []
                for _, t in subset.iterrows():
                    h = f"{action} {t.get('shares', '')}sh @ ${t.get('price', 0):,.0f}"
                    if action == 'SELL' and t.get('pnl', 0) != 0:
                        h += f"<br>P&L: ${t['pnl']:+,.0f}"
                    hovers.append(h)
                fig.add_trace(go.Scatter(
                    x=subset['date'], y=subset['price'],
                    mode='markers+text', name=action,
                    marker=dict(
                        symbol=cfg['shape'], size=18, color=cfg['color'],
                        line=dict(width=2.5, color=cfg['outline']),
                        opacity=0.95,
                    ),
                    text=[action[0] for _ in subset.iterrows()],
                    textposition='top center' if action == 'BUY' else 'bottom center',
                    textfont=dict(size=10, color=cfg['color'], family='Arial Black'),
                    hovertext=hovers,
                    hovertemplate='%{hovertext}<br>%{x|%Y-%m-%d}<extra></extra>'
                ), row=1, col=1)

        fig.update_layout(
            title='TSMC (2330.TW) — Price Chart (NTD)',
            hovermode='x unified', template='plotly_white',
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            xaxis2=dict(type='date', tickformat='%Y-%m-%d', tickangle=-45),
            yaxis=dict(title='Price (NTD)', tickformat=',.0f'),
            yaxis2=dict(title='Volume'),
            xaxis_rangeslider_visible=False, height=620,
        )
        return fig
