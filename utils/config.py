"""
Configuration management for MetaMacro TUI
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any
import json


@dataclass
class Config:
    """Application configuration"""

    # Data settings
    default_period: str = "2y"
    default_interval: str = "1d"
    auto_refresh: bool = False
    refresh_interval: int = 300  # seconds

    # Display settings
    show_yearly_kpis: bool = True
    show_weekly_kpis: bool = True
    show_daily_kpis: bool = True
    show_session_kpis: bool = True
    show_weekly_cols: bool = True
    show_data_quality: bool = True

    # Chart settings
    chart_height: int = 15
    chart_width: int = 80

    # Export settings
    export_directory: str = "exports"

    # Cache settings
    cache_ttl: int = 3600  # seconds

    def __post_init__(self):
        """Initialize configuration"""
        self.config_file = Path.home() / ".metamacro_tui_config.json"
        self.load_config()

    def load_config(self) -> None:
        """Load configuration from file"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    config_data = json.load(f)

                # Update configuration with loaded values
                for key, value in config_data.items():
                    if hasattr(self, key):
                        setattr(self, key, value)

            except Exception as e:
                # If config file is corrupted, use defaults
                pass

    def save_config(self) -> None:
        """Save configuration to file"""
        try:
            config_data = {
                "default_period": self.default_period,
                "default_interval": self.default_interval,
                "auto_refresh": self.auto_refresh,
                "refresh_interval": self.refresh_interval,
                "show_yearly_kpis": self.show_yearly_kpis,
                "show_weekly_kpis": self.show_weekly_kpis,
                "show_daily_kpis": self.show_daily_kpis,
                "show_session_kpis": self.show_session_kpis,
                "show_weekly_cols": self.show_weekly_cols,
                "show_data_quality": self.show_data_quality,
                "chart_height": self.chart_height,
                "chart_width": self.chart_width,
                "export_directory": self.export_directory,
                "cache_ttl": self.cache_ttl,
            }

            with open(self.config_file, 'w') as f:
                json.dump(config_data, f, indent=2)

        except Exception as e:
            # Silently fail if we can't save config
            pass

    def get_available_periods(self) -> list[str]:
        """Get available time periods"""
        return ["1y", "2y", "5y", "max"]

    def get_available_intervals(self) -> list[str]:
        """Get available data intervals"""
        return ["1d", "1wk", "1mo"]

    def update_setting(self, key: str, value: Any) -> bool:
        """Update a configuration setting"""
        if hasattr(self, key):
            setattr(self, key, value)
            self.save_config()
            return True
        return False

    def reset_to_defaults(self) -> None:
        """Reset configuration to default values"""
        self.default_period = "2y"
        self.default_interval = "1d"
        self.auto_refresh = False
        self.refresh_interval = 300
        self.show_yearly_kpis = True
        self.show_weekly_kpis = True
        self.show_daily_kpis = True
        self.show_session_kpis = True
        self.show_weekly_cols = True
        self.show_data_quality = True
        self.chart_height = 15
        self.chart_width = 80
        self.export_directory = "exports"
        self.cache_ttl = 3600
        self.save_config()
