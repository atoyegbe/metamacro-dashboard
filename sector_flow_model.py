# sector_flow_model.py
# Integrated Yearly + Weekly + Daily + Session orderflow classifiers, caching, builders, and helpers.

from __future__ import annotations

import time
from typing import Dict, Optional

import numpy as np
import pandas as pd
import yfinance as yf

# ---- Optional Streamlit cache (no-op if Streamlit not present) ----------------
try:
    import streamlit as st  # type: ignore

    def cache_data(ttl: Optional[int] = None):
        return st.cache_data(ttl=ttl)
except Exception:  # pragma: no cover
    def cache_data(ttl: Optional[int] = None):
        def _decorator(func):
            return func
        return _decorator


# === Parameters ===
YEARLY_RANGE_DAYS = 28
ATR_PERIOD = 20
NEAR_THRESH_ATR = 0.5
FAST_LEN = 5
SLOW_LEN = 10


# -----------------------------------------------------------
# Utilities
# -----------------------------------------------------------
def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average True Range on OHLC DataFrame."""
    if df is None or df.empty:
        return pd.Series(dtype="float64")
    high_low = (df["High"] - df["Low"]).abs()
    high_close = (df["High"] - df["Close"].shift()).abs()
    low_close = (df["Low"] - df["Close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(period, min_periods=1).mean()


def resync_index(dfs: Dict[str, pd.DataFrame]) -> pd.DatetimeIndex:
    """Find the common index across multiple OHLC dataframes."""
    indices = [df.index for df in dfs.values() if isinstance(df, pd.DataFrame) and not df.empty]
    if not indices:
        return pd.DatetimeIndex([])
    common = indices[0]
    for idx in indices[1:]:
        common = common.intersection(idx)
    return common


def normalize_ohlc(df: pd.DataFrame, base: float = 100.0) -> pd.DataFrame:
    """Normalize an OHLC frame by its first close to a given base."""
    if df is None or df.empty:
        return df
    first_close = float(df["Close"].iloc[0])
    scale = base / first_close if first_close != 0 else 1.0
    return df[["Open", "High", "Low", "Close"]] * scale


def ew_index_from_members(ohlc_members: Dict[str, pd.DataFrame], base: float = 100.0) -> pd.DataFrame:
    """Equal-weight index from member OHLC frames."""
    members = {k: v[["Open", "High", "Low", "Close"]] for k, v in ohlc_members.items() if isinstance(v, pd.DataFrame) and not v.empty}
    if not members:
        return pd.DataFrame(columns=["Open", "High", "Low", "Close"])

    common_idx = resync_index(members)
    frames = []
    for df in members.values():
        if not common_idx.empty:
            df = df.reindex(common_idx).dropna()
        frames.append(normalize_ohlc(df, base=base))

    if not frames:
        return pd.DataFrame(columns=["Open", "High", "Low", "Close"])

    merged = pd.concat(frames, axis=1)
    out = pd.DataFrame(index=merged.index)
    for col in ["Open", "High", "Low", "Close"]:
        cols = [c for c in merged.columns if c.endswith(col)]
        out[col] = merged[cols].mean(axis=1)
    return out.dropna()


def ohlc_divide(numer: pd.DataFrame, denom: pd.DataFrame) -> pd.DataFrame:
    """Divide one OHLC series by another (ratio)."""
    if numer is None or denom is None or numer.empty or denom.empty:
        return pd.DataFrame(columns=["Open", "High", "Low", "Close"])
    idx = numer.index.intersection(denom.index)
    if idx.empty:
        return pd.DataFrame(columns=["Open", "High", "Low", "Close"])
    n = numer.loc[idx, ["Open", "High", "Low", "Close"]]
    d = denom.loc[idx, ["Open", "High", "Low", "Close"]].replace(0, np.nan)
    out = (n / d).dropna()
    return out


# -----------------------------------------------------------
# Data Fetch
# -----------------------------------------------------------
def _fetch_data_uncached(ticker: str, period="2y", interval="1d", retries=3, delay=5) -> pd.DataFrame:
    for attempt in range(retries):
        try:
            df = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [c[0] for c in df.columns]
            if not df.empty:
                cols = ["Open", "High", "Low", "Close"]
                if all(c in df.columns for c in cols):
                    return df[cols].dropna()
        except Exception:
            if attempt < retries - 1:
                time.sleep(delay)
    return pd.DataFrame(columns=["Open", "High", "Low", "Close"])


@cache_data(ttl=3600)
def fetch_data(ticker: str, period="2y", interval="1d", retries=3, delay=5) -> pd.DataFrame:
    """Cached Yahoo Finance fetch."""
    return _fetch_data_uncached(ticker, period=period, interval=interval, retries=retries, delay=delay)


# -----------------------------------------------------------
# Builders
# -----------------------------------------------------------
def load_universe(csv_path) -> pd.DataFrame:
    """Load the universe CSV. Required columns: Ticker, Sector, SubIndustry, SectorIndex"""
    df = pd.read_csv(csv_path)
    req = ["Ticker", "Sector", "SubIndustry", "SectorIndex"]
    missing = [c for c in req if c not in df.columns]
    if missing:
        raise ValueError(f"CSV missing: {missing}")
    for c in req:
        df[c] = df[c].astype(str).str.strip()
    return df


def build_subindustry_indices(universe: pd.DataFrame, ohlc_map: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    """Build synthetic OHLC series for each SubIndustry."""
    sub_idx: Dict[str, pd.DataFrame] = {}
    for sub, chunk in universe.groupby("SubIndustry"):
        tickers = chunk["Ticker"].dropna().unique().tolist()
        members = {t: ohlc_map.get(t, pd.DataFrame()) for t in tickers}
        idx_df = ew_index_from_members(members)
        if not idx_df.empty:
            sub_idx[sub] = idx_df
    return sub_idx


def build_yahoo_composite(period="2y", interval="1d") -> pd.DataFrame:
    """Geometric composite of major US indices."""
    tickers = ["^IXIC", "^GSPC", "^DJI", "^RUT"]
    fallbacks = ["QQQ", "SPY", "DIA", "IWM"]
    data = {}
    for i, t in enumerate(tickers):
        df = fetch_data(t, period=period, interval=interval)
        if df.empty:
            alt = fallbacks[i]
            df = fetch_data(alt, period=period, interval=interval)
        if not df.empty:
            data[t] = df[["Open", "High", "Low", "Close"]]

    if not data:
        return pd.DataFrame(columns=["Open", "High", "Low", "Close"])

    idx = resync_index(data)
    frames = []
    for t, df in data.items():
        if not df.empty:
            df = df.reindex(idx).dropna()
            frames.append(df)

    merged = pd.concat(frames, axis=1, keys=list(data.keys()))
    out = pd.DataFrame(index=idx)
    for col in ["Open", "High", "Low", "Close"]:
        cols = merged.xs(col, axis=1, level=1)
        out[col] = np.exp(np.log(cols).mean(axis=1))
    return out.dropna()


# -----------------------------------------------------------
# Regime Models
# -----------------------------------------------------------
def _classify_macro(close, hi, lo, mid):
    if close > mid and close > hi:
        return "Strong Bull"
    elif close > mid:
        return "Weak Bull"
    elif close < mid and close < lo:
        return "Strong Bear"
    elif close < mid:
        return "Weak Bear"
    return "Neutral"


def _classify_micro(df, fast_len=FAST_LEN, slow_len=SLOW_LEN, macro="Neutral"):
    fast_ma = df["Close"].rolling(fast_len).mean().iloc[-1]
    slow_ma = df["Close"].rolling(slow_len).mean().iloc[-1]
    if "Bull" in macro:
        return "Micro Bull+" if fast_ma > slow_ma else "Micro Bear"
    elif "Bear" in macro:
        return "Micro Bear" if fast_ma < slow_ma else "Micro Bull"
    return "Neutral"


def _classify_transition(close, hi, lo, mid, atr_val, near_thresh_atr=NEAR_THRESH_ATR):
    if atr_val <= 0:
        return "None"
    dist_hi = (hi - close) / atr_val
    dist_lo = (close - lo) / atr_val
    if close < hi and close > mid and dist_hi < near_thresh_atr:
        return "Approaching Weak Bull"
    elif close > hi and dist_hi < near_thresh_atr:
        return "Approaching Strong Bull"
    elif close > lo and close < mid and dist_lo < near_thresh_atr:
        return "Approaching Weak Bear"
    elif close < lo and dist_lo < near_thresh_atr:
        return "Approaching Strong Bear"
    return "None"


def classify_regime(df: pd.DataFrame, atr_len: int = ATR_PERIOD) -> pd.DataFrame:
    """Yearly regime using 28-day OR."""
    if df is None or df.empty:
        return pd.DataFrame(columns=["Macro","Micro","Transition","Close","Hi","Lo","Mid"])
    hi = df["High"].rolling(YEARLY_RANGE_DAYS).max()
    lo = df["Low"].rolling(YEARLY_RANGE_DAYS).min()
    mid = (hi + lo) / 2
    atr_val = atr(df, atr_len)
    out = []
    for i in range(len(df)):
        if pd.isna(hi.iloc[i]) or pd.isna(lo.iloc[i]):
            out.append((np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan))
            continue
        close = df["Close"].iloc[i]
        macro = _classify_macro(close, hi.iloc[i], lo.iloc[i], mid.iloc[i])
        micro = _classify_micro(df.iloc[:i+1], macro=macro)
        trans = _classify_transition(close, hi.iloc[i], lo.iloc[i], mid.iloc[i], atr_val.iloc[i])
        out.append((macro, micro, trans, close, hi.iloc[i], lo.iloc[i], mid.iloc[i]))
    return pd.DataFrame(out, columns=["Macro","Micro","Transition","Close","Hi","Lo","Mid"], index=df.index)


def classify_weekly_regime(df: pd.DataFrame, atr_len: int = 14) -> pd.DataFrame:
    """Weekly regime using 5-day OR."""
    if df is None or df.empty:
        return pd.DataFrame(columns=["WeeklyMacro","WeeklyMicro","WeeklyTransition","Close","Hi","Lo","Mid"])
    hi = df["High"].rolling(5).max()
    lo = df["Low"].rolling(5).min()
    mid = (hi + lo) / 2
    atr_val = atr(df, atr_len)
    out = []
    for i in range(len(df)):
        if pd.isna(hi.iloc[i]) or pd.isna(lo.iloc[i]):
            out.append((np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan))
            continue
        close = df["Close"].iloc[i]
        macro = _classify_macro(close, hi.iloc[i], lo.iloc[i], mid.iloc[i])
        micro = _classify_micro(df.iloc[:i+1], macro=macro)
        trans = _classify_transition(close, hi.iloc[i], lo.iloc[i], mid.iloc[i], atr_val.iloc[i])
        out.append((macro, micro, trans, close, hi.iloc[i], lo.iloc[i], mid.iloc[i]))
    return pd.DataFrame(out, columns=["WeeklyMacro","WeeklyMicro","WeeklyTransition","Close","Hi","Lo","Mid"], index=df.index)


def classify_daily_regime(df: pd.DataFrame, atr_len: int = 14) -> pd.DataFrame:
    """Daily regime using 1-day OR."""
    if df is None or df.empty:
        return pd.DataFrame(columns=["DailyMacro","DailyMicro","DailyTransition","Close","Hi","Lo","Mid"])
    hi = df["High"].rolling(1).max()
    lo = df["Low"].rolling(1).min()
    mid = (hi + lo) / 2
    atr_val = atr(df, atr_len)
    out = []
    for i in range(len(df)):
        close = df["Close"].iloc[i]
        macro = _classify_macro(close, hi.iloc[i], lo.iloc[i], mid.iloc[i])
        micro = _classify_micro(df.iloc[:i+1], macro=macro)
        trans = _classify_transition(close, hi.iloc[i], lo.iloc[i], mid.iloc[i], atr_val.iloc[i])
        out.append((macro, micro, trans, close, hi.iloc[i], lo.iloc[i], mid.iloc[i]))
    return pd.DataFrame(out, columns=["DailyMacro","DailyMicro","DailyTransition","Close","Hi","Lo","Mid"], index=df.index)


def compute_latest_labels(
    entity: str,
    y: pd.DataFrame,
    w: pd.DataFrame,
    d: pd.DataFrame,
    s: pd.DataFrame | None = None
) -> dict:
    """Latest values across Yearly, Weekly, Daily, and Session regimes."""
    row = {"Entity": entity}
    if isinstance(y, pd.DataFrame) and not y.empty:
        row["Macro"] = y["Macro"].iloc[-1]
        row["Micro"] = y["Micro"].iloc[-1]
        row["Transition"] = y["Transition"].iloc[-1]
        row["Close"] = y["Close"].iloc[-1]
    if isinstance(w, pd.DataFrame) and not w.empty:
        row["WeeklyMacro"] = w["WeeklyMacro"].iloc[-1]
        row["WeeklyMicro"] = w["WeeklyMicro"].iloc[-1]
        row["WeeklyTransition"] = w["WeeklyTransition"].iloc[-1]
    if isinstance(d, pd.DataFrame) and not d.empty:
        row["DailyMacro"] = d["DailyMacro"].iloc[-1]
        row["DailyMicro"] = d["DailyMicro"].iloc[-1]
        row["DailyTransition"] = d["DailyTransition"].iloc[-1]
    if isinstance(s, pd.DataFrame) and not s.empty:
        last = s.iloc[-1]
        row["Session"] = last["Session"]
        row["SessionMacro"] = last["Macro"]
        row["SessionMicro"] = last["Micro"]
        row["SessionTransition"] = last["Transition"]
    return row


# -----------------------------------------------------------
# Session-Specific Regimes
# -----------------------------------------------------------
def classify_session_regimes(
    df: pd.DataFrame,
    fast_len: int = 5,
    slow_len: int = 10,
    atr_len: int = 14,
    near_thresh_atr: float = 0.5,
    tz: str = "America/New_York",
) -> pd.DataFrame:
    """Classify session-specific regimes (Asia, London, NY AM, NY PM)."""
    if df is None or df.empty:
        return pd.DataFrame(columns=["Session","Close","Macro","Micro","Transition","Hi","Lo","Mid"])

    # If df index is daily/weekly frequency, no session info is available
    if pd.infer_freq(df.index) in ("B", "D", "W", "M", "Q", "A", None):
        return pd.DataFrame(columns=["Session","Close","Macro","Micro","Transition","Hi","Lo","Mid"])

    if df.index.tz is None:
        df = df.tz_localize("UTC").tz_convert(tz)
    else:
        df = df.tz_convert(tz)

    sessions = {
        "Asia":   ("04:00", "05:00"),
        "London": ("09:00", "10:00"),
        "NY AM":  ("12:00", "13:00"),
        "NY PM":  ("13:00", "14:00"),
    }

    df["ATR"] = atr(df, atr_len)
    results = []

    for session_name, (start, end) in sessions.items():
        mask = (df.index.strftime("%H:%M") >= start) & (df.index.strftime("%H:%M") < end)
        sess_df = df.loc[mask]

        if sess_df.empty:
            continue

        hi = sess_df["High"].max()
        lo = sess_df["Low"].min()
        mid = (hi + lo) / 2.0
        close = sess_df["Close"].iloc[-1]

        macro = _classify_macro(close, hi, lo, mid)
        micro = _classify_micro(sess_df, fast_len, slow_len, macro)
        trans = _classify_transition(close, hi, lo, mid, df["ATR"].iloc[-1], near_thresh_atr)

        results.append({
            "Session": session_name,
            "Close": close,
            "Macro": macro,
            "Micro": micro,
            "Transition": trans,
            "Hi": hi,
            "Lo": lo,
            "Mid": mid,
        })

    return pd.DataFrame(results)
