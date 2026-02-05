"""
Dashboard Data Loader

Loads data from paper trading files for dashboard display.
"""

from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np
import json

from .config import load_config


class DashboardDataLoader:
    """Loads data for dashboard display."""

    def __init__(self, config_path: str = "config/dashboard_config.yaml"):
        """Initialize data loader."""
        self.config = load_config(config_path)
        self.data_dir = Path(self.config.get('data_directory', 'data'))

    def get_portfolio_status(self) -> Dict[str, Any]:
        """Get current portfolio status."""
        paper_portfolio_file = self.data_dir / "paper_trading" / "portfolio_state.json"

        if paper_portfolio_file.exists():
            with open(paper_portfolio_file, 'r') as f:
                data = json.load(f)

            cash = data.get('cash', 100000)
            positions = data.get('positions', {})
            invested = sum(
                p.get('quantity', 0) * p.get('current_price', p.get('avg_price', 0))
                for p in positions.values()
            )
            initial = data.get('initial_capital', 100000)
            total_equity = cash + invested

            return {
                'total_equity': total_equity,
                'cash': cash,
                'invested': invested,
                'positions': positions,
                'total_return_pct': ((total_equity / initial) - 1) * 100 if initial > 0 else 0,
                'initial_capital': initial
            }

        return {
            'total_equity': 100000,
            'cash': 100000,
            'invested': 0,
            'positions': {},
            'total_return_pct': 0.0,
            'initial_capital': 100000
        }

    def get_performance_metrics(self, days: int = 30) -> Dict[str, float]:
        """Get performance metrics."""
        equity_curve = self.get_equity_curve(days=days)

        if equity_curve.empty:
            return {}

        returns = equity_curve['equity'].pct_change().dropna()

        metrics = {
            'total_return_pct': (equity_curve['equity'].iloc[-1] / equity_curve['equity'].iloc[0] - 1),
            'annual_return_pct': self._annualize_return(returns),
            'sharpe_ratio': self._calculate_sharpe(returns),
            'sortino_ratio': self._calculate_sortino(returns),
            'max_drawdown': self._calculate_max_drawdown(equity_curve['equity']),
            'win_rate': self._calculate_win_rate(days),
            'volatility': returns.std() * np.sqrt(252),
            'calmar_ratio': 0.0,
        }

        if metrics['max_drawdown'] != 0:
            metrics['calmar_ratio'] = metrics['annual_return_pct'] / abs(metrics['max_drawdown'])

        return metrics

    def get_equity_curve(self, days: Optional[int] = None) -> pd.DataFrame:
        """Get equity curve data from paper trading daily logs."""
        paper_trading_logs = self.data_dir / "paper_trading" / "daily_logs"

        if paper_trading_logs.exists():
            equity_data = []
            for log_file in sorted(paper_trading_logs.glob("*.json")):
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

            if equity_data:
                df = pd.DataFrame(equity_data)
                df['date'] = pd.to_datetime(df['date'])
                df = df.sort_values('date')

                if days:
                    cutoff_date = datetime.now() - timedelta(days=days)
                    df = df[df['date'] >= cutoff_date]

                return df

        return pd.DataFrame(columns=['date', 'equity'])

    def get_drawdown_data(self, days: Optional[int] = None) -> pd.DataFrame:
        """Calculate drawdown data from equity curve."""
        equity_curve = self.get_equity_curve(days=days)

        if equity_curve.empty:
            return pd.DataFrame()

        running_max = equity_curve['equity'].expanding().max()
        drawdown = (equity_curve['equity'] - running_max) / running_max

        return pd.DataFrame({
            'date': equity_curve['date'],
            'drawdown': drawdown
        })

    def get_trade_history(self, days: Optional[int] = None) -> pd.DataFrame:
        """Get trade history from paper trading."""
        paper_trades_file = self.data_dir / "paper_trading" / "trade_history.json"

        if paper_trades_file.exists():
            try:
                with open(paper_trades_file, 'r') as f:
                    trades = json.load(f)

                if trades:
                    df = pd.DataFrame(trades)
                    df['date'] = pd.to_datetime(df['date'])

                    if days:
                        cutoff_date = datetime.now() - timedelta(days=days)
                        df = df[df['date'] >= cutoff_date]

                    return df
            except:
                pass

        return pd.DataFrame()

    def get_risk_status(self) -> Dict[str, Any]:
        """Get current risk status."""
        portfolio = self.get_portfolio_status()
        risk_config = load_config('config/risk_params.yaml')

        total_equity = portfolio.get('total_equity', 100000)
        invested = portfolio.get('invested', 0)
        num_positions = len(portfolio.get('positions', {}))

        equity_curve = self.get_equity_curve(days=90)
        current_drawdown = 0.0
        if not equity_curve.empty:
            peak = equity_curve['equity'].max()
            current = equity_curve['equity'].iloc[-1]
            current_drawdown = (current - peak) / peak if peak > 0 else 0

        return {
            'portfolio_exposure': invested / total_equity if total_equity > 0 else 0,
            'max_exposure': risk_config.get('max_portfolio_exposure', 0.50),
            'num_positions': num_positions,
            'max_positions': risk_config.get('max_positions', 3),
            'current_drawdown': abs(current_drawdown),
            'max_drawdown_limit': risk_config.get('max_drawdown_alert', 0.15),
        }

    # Helper methods
    def _annualize_return(self, returns: pd.Series) -> float:
        if returns.empty:
            return 0.0
        total_return = (1 + returns).prod() - 1
        num_days = len(returns)
        if num_days == 0:
            return 0.0
        return (1 + total_return) ** (252 / num_days) - 1

    def _calculate_sharpe(self, returns: pd.Series) -> float:
        if returns.empty or returns.std() == 0:
            return 0.0
        return (returns.mean() / returns.std()) * np.sqrt(252)

    def _calculate_sortino(self, returns: pd.Series) -> float:
        if returns.empty:
            return 0.0
        downside_returns = returns[returns < 0]
        if downside_returns.empty or downside_returns.std() == 0:
            return 0.0
        return (returns.mean() / downside_returns.std()) * np.sqrt(252)

    def _calculate_max_drawdown(self, equity: pd.Series) -> float:
        if equity.empty:
            return 0.0
        running_max = equity.expanding().max()
        drawdown = (equity - running_max) / running_max
        return drawdown.min()

    def _calculate_win_rate(self, days: int) -> float:
        trades = self.get_trade_history(days=days)
        if trades.empty or 'pnl' not in trades.columns:
            return 0.0
        winning_trades = len(trades[trades['pnl'] > 0])
        return winning_trades / len(trades)

    # Demo mode methods
    def get_demo_equity_curve(self, days: int = 60) -> pd.DataFrame:
        """Generate demo equity curve data."""
        np.random.seed(42)
        start_date = datetime.now() - timedelta(days=days)
        dates = pd.date_range(start=start_date, periods=days, freq='D')

        initial_capital = 100000
        daily_returns = np.random.normal(0.001, 0.015, days)

        equity = [initial_capital]
        for ret in daily_returns[1:]:
            equity.append(equity[-1] * (1 + ret))

        return pd.DataFrame({'date': dates, 'equity': equity})

    def get_demo_trade_history(self) -> pd.DataFrame:
        """Generate demo trade history."""
        trades = [
            {'date': '2025-12-05', 'symbol': '2330.TW', 'action': 'BUY', 'quantity': 100, 'price': 580, 'pnl': 0},
            {'date': '2025-12-15', 'symbol': '2330.TW', 'action': 'SELL', 'quantity': 100, 'price': 610, 'pnl': 3000},
            {'date': '2025-12-20', 'symbol': '2330.TW', 'action': 'BUY', 'quantity': 120, 'price': 595, 'pnl': 0},
            {'date': '2026-01-05', 'symbol': '2330.TW', 'action': 'SELL', 'quantity': 120, 'price': 575, 'pnl': -2400},
            {'date': '2026-01-10', 'symbol': '2330.TW', 'action': 'BUY', 'quantity': 150, 'price': 560, 'pnl': 0},
            {'date': '2026-01-20', 'symbol': '2330.TW', 'action': 'SELL', 'quantity': 150, 'price': 590, 'pnl': 4500},
            {'date': '2026-01-25', 'symbol': '2330.TW', 'action': 'BUY', 'quantity': 130, 'price': 585, 'pnl': 0},
        ]
        df = pd.DataFrame(trades)
        df['date'] = pd.to_datetime(df['date'])
        return df
