"""
Dashboard Metrics Module

Calculates metrics for the dashboard display.
"""

from typing import Dict, Any
from pathlib import Path
import pandas as pd
import numpy as np
import json


class DashboardMetrics:
    """Calculate metrics for dashboard display."""

    def __init__(self):
        """Initialize metrics calculator."""
        self.data_dir = Path("data")
        self.paper_trading_dir = self.data_dir / "paper_trading"

    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get current portfolio summary."""
        state_file = self.paper_trading_dir / "portfolio_state.json"

        if not state_file.exists():
            return {
                'total_equity': 0,
                'cash': 0,
                'positions_value': 0,
                'total_return_pct': 0,
                'unrealized_pnl': 0
            }

        with open(state_file, 'r') as f:
            state = json.load(f)

        initial = state.get('initial_capital', 100000)
        cash = state.get('cash', initial)
        positions = state.get('positions', {})

        positions_value = sum(
            p.get('quantity', 0) * p.get('current_price', 0)
            for p in positions.values()
        )

        total_equity = cash + positions_value
        total_return_pct = ((total_equity / initial) - 1) * 100 if initial > 0 else 0

        return {
            'total_equity': total_equity,
            'cash': cash,
            'positions_value': positions_value,
            'total_return_pct': total_return_pct,
            'initial_capital': initial,
            'positions': positions
        }

    def get_trade_statistics(self) -> Dict[str, Any]:
        """Get trading statistics."""
        trades_file = self.paper_trading_dir / "trade_history.json"

        if not trades_file.exists():
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'total_pnl': 0,
                'avg_pnl': 0
            }

        with open(trades_file, 'r') as f:
            trades = json.load(f)

        if not trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'total_pnl': 0,
                'avg_pnl': 0
            }

        closed_trades = [t for t in trades if t.get('action') == 'SELL']

        if not closed_trades:
            return {
                'total_trades': len(trades),
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'total_pnl': 0,
                'avg_pnl': 0
            }

        pnls = [t.get('pnl', 0) for t in closed_trades]
        winning = sum(1 for pnl in pnls if pnl > 0)
        losing = sum(1 for pnl in pnls if pnl < 0)

        return {
            'total_trades': len(trades),
            'closed_trades': len(closed_trades),
            'winning_trades': winning,
            'losing_trades': losing,
            'win_rate': (winning / len(closed_trades) * 100) if closed_trades else 0,
            'total_pnl': sum(pnls),
            'avg_pnl': np.mean(pnls) if pnls else 0,
            'best_trade': max(pnls) if pnls else 0,
            'worst_trade': min(pnls) if pnls else 0
        }

    def calculate_sharpe_ratio(self, returns: pd.Series, risk_free_rate: float = 0.02) -> float:
        """Calculate Sharpe ratio from returns series."""
        if returns.empty or len(returns) < 2 or returns.std() == 0:
            return 0.0
        mean_return = returns.mean() * 252
        std_return = returns.std() * np.sqrt(252)
        return (mean_return - risk_free_rate) / std_return

    def calculate_max_drawdown(self, equity_curve: pd.Series) -> float:
        """Calculate maximum drawdown from equity curve."""
        if equity_curve.empty:
            return 0.0
        running_max = equity_curve.cummax()
        drawdown = (equity_curve / running_max - 1) * 100
        return drawdown.min()

    def get_daily_returns(self, days: int = 30) -> pd.Series:
        """Get daily returns from equity curve."""
        daily_logs = self.paper_trading_dir / "daily_logs"

        if not daily_logs.exists():
            return pd.Series()

        equity_data = []
        for log_file in sorted(daily_logs.glob("*.json")):
            try:
                with open(log_file, 'r') as f:
                    data = json.load(f)
                    if 'portfolio' in data:
                        equity_data.append({
                            'date': data['date'],
                            'equity': data['portfolio'].get('total_equity', 0)
                        })
            except:
                continue

        if not equity_data:
            return pd.Series()

        df = pd.DataFrame(equity_data)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').set_index('date')

        returns = df['equity'].pct_change().dropna()

        if days and len(returns) > days:
            returns = returns.tail(days)

        return returns

    def get_performance_metrics(self, days: int = 30) -> Dict[str, Any]:
        """Get comprehensive performance metrics."""
        returns = self.get_daily_returns(days)

        if returns.empty:
            return {
                'sharpe_ratio': 0,
                'sortino_ratio': 0,
                'max_drawdown': 0,
                'volatility': 0,
                'win_rate': 0,
                'total_return_pct': 0,
                'annual_return_pct': 0
            }

        sharpe = self.calculate_sharpe_ratio(returns)

        negative_returns = returns[returns < 0]
        if len(negative_returns) > 0:
            downside_std = negative_returns.std() * np.sqrt(252)
            sortino = (returns.mean() * 252 - 0.02) / downside_std if downside_std > 0 else 0
        else:
            sortino = float('inf')

        volatility = returns.std() * np.sqrt(252) * 100
        total_return = ((1 + returns).prod() - 1) * 100

        trading_days = len(returns)
        if trading_days > 0:
            annual_return = ((1 + total_return/100) ** (252/trading_days) - 1) * 100
        else:
            annual_return = 0

        trade_stats = self.get_trade_statistics()

        return {
            'sharpe_ratio': sharpe,
            'sortino_ratio': sortino,
            'max_drawdown': 0,
            'volatility': volatility,
            'win_rate': trade_stats.get('win_rate', 0) / 100,
            'total_return_pct': total_return,
            'annual_return_pct': annual_return,
        }
