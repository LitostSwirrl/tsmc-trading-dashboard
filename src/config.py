"""
Simplified configuration loader for dashboard.
"""

from pathlib import Path
from typing import Any, Dict
import yaml


def load_config(config_path: str) -> Dict[str, Any]:
    """
    Load configuration from YAML file.

    Args:
        config_path: Path to YAML config file

    Returns:
        Dictionary with configuration
    """
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}
    except Exception:
        return {}
