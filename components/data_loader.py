"""
Data loading component for MetaMacro TUI
Handles loading and caching of market and universe data
"""

import asyncio
from pathlib import Path
from typing import Dict, Optional, Any
import pandas as pd
from datetime import datetime, timedelta

# Import the existing sector flow model functions
import sys
sys.path.append(str(Path(__file__).parent.parent))

from sector_flow_model import (
    load_universe,
    fetch_data,
    build_subindustry_indices,
    build_yahoo_composite,
    ohlc_divide,
    classify_regime,
    classify_weekly_regime,
    classify_daily_regime,
    classify_session_regimes,
    compute_latest_labels,
)


class DataCache:
    """Simple in-memory cache for data"""

    def __init__(self, ttl: int = 3600):
        self.ttl = ttl
        self.cache: Dict[str, Dict[str, Any]] = {}

    def get(self, key: str) -> Optional[Any]:
        """Get cached data if not expired"""
        if key in self.cache:
            data, timestamp = self.cache[key]["data"], self.cache[key]["timestamp"]
            if datetime.now() - timestamp < timedelta(seconds=self.ttl):
                return data
            else:
                # Remove expired data
                del self.cache[key]
        return None

    def set(self, key: str, data: Any) -> None:
        """Cache data with timestamp"""
        self.cache[key] = {
            "data": data,
            "timestamp": datetime.now()
        }

    def clear(self) -> None:
        """Clear all cached data"""
        self.cache.clear()


class DataLoader:
    """Data loading and management class"""

    def __init__(self, cache_ttl: int = 3600):
        self.cache = DataCache(cache_ttl)
        self.loading_status = "idle"
        self.progress = 0.0
        self.status_message = ""

    def clear_cache(self) -> None:
        """Clear data cache"""
        self.cache.clear()

    async def load_market_data(self, period: str = "2y", interval: str = "1d") -> Dict[str, Any]:
        """Load market data including indices and composite"""
        cache_key = f"market_data_{period}_{interval}"
        cached_data = self.cache.get(cache_key)

        if cached_data:
            return cached_data

        self.loading_status = "loading"
        self.progress = 0.0

        try:
            market_data = {}

            # Load composite market data
            self.status_message = "Loading composite market data..."
            self.progress = 0.1
            await asyncio.sleep(0.1)  # Allow UI to update

            custom_mkt = await asyncio.to_thread(
                build_yahoo_composite, period=period, interval=interval
            )
            market_data["composite_market"] = custom_mkt

            # Load VIX
            self.status_message = "Loading VIX data..."
            self.progress = 0.2
            await asyncio.sleep(0.1)

            vix = await asyncio.to_thread(
                fetch_data, "^VIX", period=period, interval=interval
            )
            market_data["vix"] = vix

            # Calculate composite vs VIX
            if not custom_mkt.empty and not vix.empty:
                idx = custom_mkt.index.intersection(vix.index)
                if len(idx) > 0:
                    comp_vs_vix = ohlc_divide(custom_mkt.loc[idx], vix.loc[idx])
                    market_data["composite_vs_vix"] = comp_vs_vix
                else:
                    market_data["composite_vs_vix"] = pd.DataFrame()
            else:
                market_data["composite_vs_vix"] = pd.DataFrame()

            # Load major indices
            self.status_message = "Loading major indices..."
            index_tickers = ["^IXIC", "^GSPC", "^DJI", "^RUT"]
            index_data = {}

            for i, ticker in enumerate(index_tickers):
                self.progress = 0.3 + (i / len(index_tickers)) * 0.4
                await asyncio.sleep(0.1)

                try:
                    df = await asyncio.to_thread(
                        fetch_data, ticker, period=period, interval=interval
                    )
                    if not df.empty:
                        index_data[ticker] = df
                except Exception as e:
                    # Continue if individual ticker fails
                    continue

            market_data["indices"] = index_data

            # Calculate index flows vs market
            flows = {}
            if not custom_mkt.empty:
                flow_names = {
                    "^RUT": "Russell 2000 / Market",
                    "^IXIC": "Nasdaq / Market",
                    "^DJI": "Dow / Market",
                    "^GSPC": "S&P 500 / Market"
                }

                for ticker, name in flow_names.items():
                    if ticker in index_data:
                        flow = ohlc_divide(index_data[ticker], custom_mkt)
                        flows[name] = flow

            market_data["flows"] = flows

            # Calculate regime classifications for market entities
            self.status_message = "Calculating market regimes..."
            self.progress = 0.8
            await asyncio.sleep(0.1)

            market_entities = {
                "Composite Market": custom_mkt,
                "Composite / VIX": market_data["composite_vs_vix"],
                **flows
            }

            regime_rows = []
            for name, df in market_entities.items():
                if isinstance(df, pd.DataFrame) and not df.empty:
                    y = await asyncio.to_thread(classify_regime, df)
                    w = await asyncio.to_thread(classify_weekly_regime, df)
                    d = await asyncio.to_thread(classify_daily_regime, df)
                    s = await asyncio.to_thread(classify_session_regimes, df)

                    row = compute_latest_labels(name, y, w, d, s)
                    regime_rows.append(row)

            market_data["regime_table"] = pd.DataFrame(regime_rows)

            self.progress = 1.0
            self.status_message = "Market data loaded successfully"
            self.loading_status = "completed"

            # Cache the data
            self.cache.set(cache_key, market_data)

            return market_data

        except Exception as e:
            self.loading_status = "error"
            self.status_message = f"Error loading market data: {str(e)}"
            raise

    async def load_universe_data(self, csv_file: Path, period: str = "2y", interval: str = "1d") -> Dict[str, Any]:
        """Load universe data from CSV file"""
        cache_key = f"universe_data_{csv_file.name}_{period}_{interval}"
        cached_data = self.cache.get(cache_key)

        if cached_data:
            return cached_data

        self.loading_status = "loading"
        self.progress = 0.0

        try:
            universe_data = {}

            # Load universe CSV
            self.status_message = f"Loading universe from {csv_file.name}..."
            self.progress = 0.1
            await asyncio.sleep(0.1)

            uni = await asyncio.to_thread(load_universe, csv_file)
            universe_data["universe"] = uni

            # Get all tickers
            tickers = sorted(set(uni['Ticker']) | set(uni['SectorIndex']))
            universe_data["tickers"] = tickers

            # Load OHLC data for all tickers
            self.status_message = "Loading ticker data..."
            ohlc_map = {}
            failed_tickers = []

            for i, ticker in enumerate(tickers):
                self.progress = 0.2 + (i / len(tickers)) * 0.6
                await asyncio.sleep(0.01)  # Small delay to allow UI updates

                try:
                    df = await asyncio.to_thread(
                        fetch_data, ticker, period=period, interval=interval
                    )
                    if isinstance(df, pd.DataFrame) and not df.empty:
                        ohlc_map[ticker] = df
                    else:
                        failed_tickers.append(ticker)
                except Exception as e:
                    failed_tickers.append(f"{ticker} (Error: {str(e)[:50]})")

            universe_data["ohlc_map"] = ohlc_map
            universe_data["failed_tickers"] = failed_tickers

            # Build sub-industry indices
            self.status_message = "Building sub-industry indices..."
            self.progress = 0.8
            await asyncio.sleep(0.1)

            sub_idx = await asyncio.to_thread(
                build_subindustry_indices, uni, ohlc_map
            )
            universe_data["sub_indices"] = sub_idx

            self.progress = 1.0
            self.status_message = f"Universe data loaded successfully from {csv_file.name}"
            self.loading_status = "completed"

            # Cache the data
            self.cache.set(cache_key, universe_data)

            return universe_data

        except Exception as e:
            self.loading_status = "error"
            self.status_message = f"Error loading universe data: {str(e)}"
            raise
