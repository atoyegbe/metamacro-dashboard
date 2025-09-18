# dashboard.py
# Enhanced UI/UX with progress indicators, data validation, Excel export, auto-refresh,
# robust plotting guards, and fully integrated Yearly + Weekly + Daily + Session regime KPIs.

import io
import time
from datetime import datetime

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet

from sector_flow_model import (
    load_universe,
    fetch_data,
    build_subindustry_indices,
    build_yahoo_composite,
    ohlc_divide,
    classify_regime,
    classify_weekly_regime,
    classify_daily_regime,
    classify_session_regimes,   # sessions
    compute_latest_labels,      # now supports session df as 4th arg
)

# ---------------- SESSION STATE INITIALIZATION ----------------
if 'user_settings' not in st.session_state:
    st.session_state.user_settings = {
        'default_period': '2y',
        'show_transitions': True,
        'chart_theme': 'dark',
        'auto_refresh': False
    }

if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False

if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = None

# ---------------- ENHANCED STYLING ----------------
st.set_page_config(page_title="MetaMacro — Sector Flow Dashboard", layout="wide")

enhanced_css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

body, .stApp {
    font-family: 'Inter', sans-serif;
    background-color: #0e1117;
    color: #e0e0e0;
    margin: 0;
    padding: 0;
}

/* Progress indicators */
.progress-container {
    background: linear-gradient(135deg, #111520 0%, #151922 100%);
    padding: 16px 20px;
    border-radius: 10px;
    margin: 16px 0;
    border: 1px solid #252a3a;
}

.progress-text {
    color: #9ca3af;
    font-size: 14px;
    margin-bottom: 8px;
}

/* Alert boxes */
.alert-success {
    background: linear-gradient(135deg, #065f46 0%, #047857 100%);
    border-left: 4px solid #10b981;
    padding: 12px 16px;
    border-radius: 8px;
    margin: 12px 0;
    color: #d1fae5;
}

.alert-warning {
    background: linear-gradient(135deg, #92400e 0%, #b45309 100%);
    border-left: 4px solid #fbbf24;
    padding: 12px 16px;
    border-radius: 8px;
    margin: 12px 0;
    color: #fef3c7;
}

.alert-error {
    background: linear-gradient(135deg, #991b1b 0%, #dc2626 100%);
    border-left: 4px solid #ef4444;
    padding: 12px 16px;
    border-radius: 8px;
    margin: 12px 0;
    color: #fecaca;
}

/* Enhanced loading states */
.loading-shimmer {
    background: linear-gradient(90deg, #161a25 25%, #1f2937 50%, #161a25 75%);
    background-size: 200% 100%;
    animation: shimmer 2s infinite;
}

@keyframes shimmer {
    0% { background-position: -200% 0; }
    100% { background-position: 200% 0; }
}

.mm-header {
    background: linear-gradient(135deg, #161a25 0%, #1f2937 100%);
    padding: 20px 28px;
    font-size: 28px;
    font-weight: 800;
    color: #ffffff;
    margin-bottom: 12px;
    border-bottom: 3px solid #1f77b4;
    border-radius: 12px 12px 0 0;
    box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    position: relative;
}

.refresh-indicator {
    position: absolute;
    top: 20px;
    right: 28px;
    font-size: 12px;
    color: #9ca3af;
}

/* Enhanced legend card */
.mm-legend {
    background: linear-gradient(135deg, #101522 0%, #141829 100%);
    padding: 16px 20px;
    border-radius: 12px;
    margin-bottom: 24px;
    border-left: 4px solid #1f77b4;
    display: flex; 
    gap: 24px; 
    align-items: center; 
    flex-wrap: wrap;
    box-shadow: 0 2px 12px rgba(0,0,0,0.2);
}
.legend-dot {
    display: inline-block; 
    width: 12px; 
    height: 12px; 
    border-radius: 50%; 
    margin-right: 8px; 
    position: relative; 
    top: 1px;
    box-shadow: 0 0 8px rgba(255,255,255,0.1);
}
.legend-item {
    display: flex; 
    align-items: center; 
    gap: 8px; 
    color: #d0d6e4;
    font-weight: 500;
    font-size: 14px;
}

/* Enhanced section cards */
.mm-card {
    background: linear-gradient(135deg, #161a25 0%, #1a1e2e 100%);
    border: 1px solid #252a3a;
    padding: 28px;
    border-radius: 16px;
    margin-bottom: 28px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.4), 0 1px 3px rgba(0,0,0,0.6);
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;
}
.mm-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 30px rgba(0,0,0,0.6), 0 2px 6px rgba(0,0,0,0.8);
    border-color: #1f77b4;
}
.mm-card h2 {
    margin-top: 0;
    color: white;
    border-left: 4px solid #1f77b4;
    padding-left: 12px;
    font-weight: 700;
    font-size: 20px;
}

/* Enhanced KPI cards */
.kpi-card {
    background: linear-gradient(135deg, #0f1320 0%, #1a1e2e 100%);
    padding: 20px;
    border-radius: 12px;
    border: 1px solid #20283a;
    text-align: center;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;
    overflow: hidden;
}
.kpi-card:hover {
    box-shadow: 0 8px 25px rgba(31, 119, 180, 0.15);
    transform: translateY(-3px);
    border-color: #1f77b4;
}
.kpi-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.05), transparent);
    transition: left 0.6s;
}
.kpi-card:hover::before {
    left: 100%;
}

/* Weekly KPI accent */
.kpi-card.weekly {
    border-left: 4px solid #3b82f6;
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
}

/* Daily KPI accent */
.kpi-card.daily {
    border-left: 4px solid #a855f7;
    background: linear-gradient(135deg, #1b102a 0%, #2a1e3b 100%);
}

/* Session KPI accent */
.kpi-card.session {
    border-left: 4px solid #f59e0b;
    background: linear-gradient(135deg, #2a1e0a 0%, #3b2f12 100%);
}

/* Status indicators */
.status-indicator {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    margin-right: 8px;
    animation: pulse 2s infinite;
}

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}

/* Enhanced tables */
.regime-table {
    background: #161a25;
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 4px 16px rgba(0,0,0,0.3);
    border: 1px solid #252a3a;
}

.regime-table table {
    color: #e0e0e0 !important;
    background-color: transparent;
    border-collapse: separate;
    border-spacing: 0;
    width: 100%;
}

.regime-table thead tr {
    background: linear-gradient(135deg, #1f2937, #374151) !important;
}

.regime-table thead th {
    padding: 16px !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    letter-spacing: 0.5px !important;
    border-bottom: 2px solid #1f77b4 !important;
    color: #ffffff !important;
}

.regime-table tbody td {
    padding: 14px 16px !important;
    border-bottom: 1px solid #252a3a !important;
    transition: background-color 0.2s ease !important;
}

.regime-table tbody tr:hover {
    background-color: #1a1e2e !important;
}

.regime-table tbody tr:nth-child(even) {
    background-color: #1c202b !important;
}

/* Enhanced regime colors with glow effects */
.regime-StrongBull { 
    color: #10b981; 
    font-weight: 600; 
    text-shadow: 0 0 10px rgba(16, 185, 129, 0.3);
}
.regime-WeakBull { 
    color: #34d399; 
    text-shadow: 0 0 8px rgba(52, 211, 153, 0.2);
}
.regime-WeakBear { 
    color: #fbbf24; 
    text-shadow: 0 0 8px rgba(251, 191, 36, 0.2);
}
.regime-StrongBear { 
    color: #ef4444; 
    font-weight: 600; 
    text-shadow: 0 0 10px rgba(239, 68, 68, 0.3);
}
.regime-Neutral { 
    color: #9ca3af; 
}

/* Weekly regime colors (blue tint) */
.wregime-StrongBull { 
    color: #3b82f6; 
    font-weight: 600; 
    text-shadow: 0 0 10px rgba(59, 130, 246, 0.3);
}
.wregime-WeakBull { 
    color: #60a5fa; 
    text-shadow: 0 0 8px rgba(96, 165, 250, 0.2);
}
.wregime-WeakBear { 
    color: #fbbf24; 
    text-shadow: 0 0 8px rgba(251, 191, 36, 0.2);
}
.wregime-StrongBear { 
    color: #ef4444; 
    font-weight: 600; 
    text-shadow: 0 0 10px rgba(239, 68, 68, 0.3);
}
.wregime-Neutral { 
    color: #9ca3af; 
}

/* Data summary section */
.data-summary {
    background: linear-gradient(135deg, #111520 0%, #151922 100%);
    padding: 20px;
    border-radius: 12px;
    margin: 20px 0;
    display: flex;
    gap: 32px;
    align-items: center;
    border: 1px solid #252a3a;
    box-shadow: 0 2px 12px rgba(0,0,0,0.2);
}

.summary-stat {
    text-align: center;
    flex: 1;
}

.summary-stat .number {
    font-size: 28px;
    font-weight: 700;
    margin-bottom: 4px;
}

.summary-stat .label {
    font-size: 13px;
    color: #9ca3af;
    font-weight: 500;
    letter-spacing: 0.5px;
}

/* Filter sections */
.filter-section {
    background: linear-gradient(135deg, #111520 0%, #151922 100%);
    padding: 16px 20px;
    border-radius: 10px;
    margin-bottom: 20px;
    border-left: 3px solid #1f77b4;
    border: 1px solid #252a3a;
}

/* Keyboard shortcuts */
.shortcuts-help {
    background: #0f1320;
    padding: 12px;
    border-radius: 8px;
    font-size: 12px;
    color: #9ca3af;
    margin-top: 20px;
}

/* Better mobile responsiveness */
@media (max-width: 768px) {
    .mm-card { padding: 20px; margin-bottom: 20px; }
    .kpi-card { padding: 16px; margin-bottom: 12px; }
    .data-summary { flex-direction: column; gap: 16px; }
    .mm-legend { flex-direction: column; gap: 12px; }
}
</style>
"""
st.markdown(enhanced_css, unsafe_allow_html=True)

# ---------------- UTILITIES & HELPERS ----------------

def show_alert(message: str, alert_type: str = "info"):
    """Display styled alert messages"""
    alert_class = f"alert-{alert_type}"
    st.markdown(f'<div class="{alert_class}">{message}</div>', unsafe_allow_html=True)

def validate_data_quality(df: pd.DataFrame, name: str) -> bool:
    """Validate data quality and show warnings"""
    if df is None or df.empty:
        show_alert(f"No data available for {name}", "warning")
        return False
    elif len(df) < 30:
        show_alert(f"Limited data for {name} ({len(df)} data points). Results may be less reliable.", "warning")
        return True
    else:
        return True

def sanitize_series(obj):
    """
    Ensure Plotly gets a 1-D sequence.
    - Accepts pandas Series, Index, numpy arrays, lists.
    - Flattens any accidental 2-D shapes.
    - Drops NaNs safely.
    """
    if obj is None:
        return []
    if isinstance(obj, (pd.Series, pd.Index)):
        arr = obj.values
    elif isinstance(obj, pd.DataFrame):
        if obj.shape[1] == 1:
            arr = obj.iloc[:, 0].values
        else:
            arr = obj.values
    else:
        arr = np.asarray(obj)

    arr = np.squeeze(arr)
    if arr.ndim > 1:
        arr = arr.reshape(-1)
    if arr.size == 0:
        return []
    return arr.tolist()

def safe_fetch_with_progress(tickers: list, period: str, interval: str) -> dict:
    """Fetch data with progress indicator and error handling"""
    if not tickers:
        return {}
    progress_bar = st.progress(0.0)
    status_text = st.empty()
    ohlc_map = {}
    failed_tickers = []

    for i, ticker in enumerate(tickers):
        try:
            status_text.text(f"Fetching data for {ticker}...")
            df = fetch_data(ticker, period=period, interval=interval)
            if isinstance(df, pd.DataFrame) and not df.empty:
                ohlc_map[ticker] = df
            else:
                failed_tickers.append(ticker)
        except Exception as e:
            failed_tickers.append(f"{ticker} (Error: {str(e)[:80]})")
        progress_bar.progress((i + 1) / len(tickers))

    progress_bar.empty()
    status_text.empty()

    if failed_tickers:
        show_alert(f"Failed to fetch data for {len(failed_tickers)} tickers: {', '.join(failed_tickers[:5])}", "warning")
    else:
        show_alert(f"Successfully loaded data for all {len(tickers)} tickers", "success")

    return ohlc_map

def export_to_excel(sections: dict, filename: str = "metamacro_analysis.xlsx") -> bytes:
    """Export multiple dataframes to Excel with formatting"""
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        workbook = writer.book
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#1f77b4',
            'font_color': 'white',
            'border': 1
        })
        for sheet_name, df in sections.items():
            if df is not None and isinstance(df, pd.DataFrame) and not df.empty:
                df_clean = df.copy()
                # Strip HTML if present
                for col in df_clean.columns:
                    if df_clean[col].dtype == 'object':
                        df_clean[col] = df_clean[col].astype(str).str.replace(r'<.*?>', '', regex=True)
                safe_name = str(sheet_name)[:31] if sheet_name else "Sheet1"
                df_clean.to_excel(writer, sheet_name=safe_name, index=False)
                worksheet = writer.sheets[safe_name]
                for col_num, value in enumerate(df_clean.columns.values):
                    worksheet.write(0, col_num, value, header_format)
                for i, col in enumerate(df_clean.columns):
                    max_len = max(df_clean[col].astype(str).str.len().max(), len(col)) + 2
                    worksheet.set_column(i, i, min(max_len, 50))
    buffer.seek(0)
    return buffer.getvalue()

def enhanced_regime_card(title: str, row: dict, weekly: bool = False, daily: bool = False, session: bool = False) -> str:
    """Enhanced KPI card with trend indicators and better styling.
       Backward compatible with `weekly` flag; set `daily=True` for daily styling.
       New: set `session=True` for session styling.
    """
    if session:
        color_map = {"Strong Bull": "#f59e0b", "Weak Bull": "#fcd34d",
                     "Strong Bear": "#b91c1c", "Weak Bear": "#f87171", "Neutral": "#9ca3af"}
        border = "border-left: 4px solid #f59e0b;"
        bg = "linear-gradient(135deg, #2a1e0a 0%, #3b2f12 100%)"
        indicator_color = "#f59e0b"
        regime_text = row.get("SessionMacro", "NA")
        micro_text = row.get("SessionMicro", "NA")
        transition = row.get("SessionTransition", "None")
        extra_class = "session"
    elif daily:
        color_map = {"Strong Bull": "#a855f7", "Weak Bull": "#c084fc",
                     "Strong Bear": "#ef4444", "Weak Bear": "#fbbf24", "Neutral": "#9ca3af"}
        border = "border-left: 4px solid #a855f7;"
        bg = "linear-gradient(135deg, #1b102a 0%, #2a1e3b 100%)"
        indicator_color = "#a855f7"
        regime_text = row.get("DailyMacro", "NA")
        micro_text = row.get("DailyMicro", "NA")
        transition = row.get("DailyTransition", "None")
        extra_class = "daily"
    elif weekly:
        color_map = {"Strong Bull": "#3b82f6", "Weak Bull": "#60a5fa",
                     "Strong Bear": "#ef4444", "Weak Bear": "#fbbf24", "Neutral": "#9ca3af"}
        border = "border-left: 4px solid #3b82f6;"
        bg = "linear-gradient(135deg, #0f172a 0%, #1e293b 100%)"
        indicator_color = "#3b82f6"
        regime_text = row.get("WeeklyMacro", "NA")
        micro_text = row.get("WeeklyMicro", "NA")
        transition = row.get("WeeklyTransition", "None")
        extra_class = "weekly"
    else:
        color_map = {"Strong Bull": "#10b981", "Weak Bull": "#34d399",
                     "Strong Bear": "#ef4444", "Weak Bear": "#fbbf24", "Neutral": "#9ca3af"}
        border = "border-left: 4px solid #10b981;"
        bg = "linear-gradient(135deg, #0f1320 0%, #1a1e2e 100%)"
        indicator_color = "#10b981"
        regime_text = row.get("Macro", "NA")
        micro_text = row.get("Micro", "NA")
        transition = row.get("Transition", "None")
        extra_class = ""

    close_val = row.get("Close", float('nan'))
    close_str = f"{close_val:.2f}" if isinstance(close_val, (int, float, np.floating)) and pd.notnull(close_val) else str(close_val)
    macro_color = color_map.get(regime_text, "#9ca3af")
    trend_arrow = "↗" if "Bull" in str(regime_text) else "↘" if "Bear" in str(regime_text) else "→"

    return f"""
    <div class='kpi-card {extra_class}' style="background: {bg}; {border}">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
            <h4 style="margin: 0; color: #ffffff; font-weight: 600; font-size: 14px;">{title}</h4>
            <span class="status-indicator" style="background: {indicator_color};"></span>
        </div>
        <div style="display: flex; align-items: center; gap: 8px; margin: 12px 0;">
            <h2 style="margin: 0; color: {macro_color}; font-size: 18px;">{regime_text}</h2>
            <span style="color: {macro_color}; font-size: 20px;">{trend_arrow}</span>
        </div>
        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 12px;">
            <div>
                <p style="margin: 0; font-size: 12px; color: #9ca3af;">Micro</p>
                <p style="margin: 0; font-size: 14px; color: #e5e7eb;">{micro_text}</p>
            </div>
            <div style="text-align: right;">
                <p style="margin: 0; font-size: 12px; color: #9ca3af;">Close</p>
                <p style="margin: 0; font-size: 16px; color: #1f77b4; font-weight: 500;">{close_str}</p>
            </div>
        </div>
        {f'<div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid #374151;"><p style="margin: 0; font-size: 11px; color: #6b7280;">{transition}</p></div>' if str(transition) != "None" else ''}
    </div>
    """

def enhanced_data_summary(df: pd.DataFrame) -> str:
    """Create enhanced data summary card"""
    if df is None or df.empty:
        return ""
    total_entities = len(df)
    bull_count = len(df[df['Macro'].astype(str).str.contains('Bull', na=False)])
    bear_count = len(df[df['Macro'].astype(str).str.contains('Bear', na=False)])
    neutral_count = total_entities - bull_count - bear_count
    bull_ratio = (bull_count / total_entities * 100) if total_entities > 0 else 0
    return f"""
    <div class="data-summary">
        <div class="summary-stat">
            <div class="number" style="color: #1f77b4;">{total_entities}</div>
            <div class="label">TOTAL ENTITIES</div>
        </div>
        <div class="summary-stat">
            <div class="number" style="color: #10b981;">{bull_count}</div>
            <div class="label">BULLISH</div>
        </div>
        <div class="summary-stat">
            <div class="number" style="color: #ef4444;">{bear_count}</div>
            <div class="label">BEARISH</div>
        </div>
        <div class="summary-stat">
            <div class="number" style="color: #9ca3af;">{neutral_count}</div>
            <div class="label">NEUTRAL</div>
        </div>
        <div class="summary-stat">
            <div class="number" style="color: #fbbf24;">{bull_ratio:.1f}%</div>
            <div class="label">BULL RATIO</div>
        </div>
    </div>
    """

def enhanced_style_regime_table(df: pd.DataFrame, include_weekly: bool = True):
    """Enhanced table styling with better visual hierarchy"""
    if df is None or df.empty:
        st.markdown("""
        <div style="text-align: center; padding: 60px 40px; color: #9ca3af; background: linear-gradient(135deg, #161a25 0%, #1a1e2e 100%); border-radius: 12px; border: 1px solid #252a3a;">
            <div style="font-size: 64px; margin-bottom: 20px; opacity: 0.5;">📊</div>
            <div style="font-size: 18px; margin-bottom: 8px; color: #e5e7eb;">No data available</div>
            <div style="font-size: 14px; color: #9ca3af;">Upload a universe CSV to see regime analysis</div>
        </div>
        """, unsafe_allow_html=True)
        return

    def style_label(val, weekly=False):
        s = str(val)
        if weekly:
            cls = "Neutral"
            if "Strong Bull" in s: cls = "StrongBull"
            elif "Weak Bull" in s: cls = "WeakBull"
            elif "Weak Bear" in s: cls = "WeakBear"
            elif "Strong Bear" in s: cls = "StrongBear"
            return f"<span class='wregime-{cls}'>{s}</span>"
        else:
            cls = "Neutral"
            if "Strong Bull" in s: cls = "StrongBull"
            elif "Weak Bull" in s: cls = "WeakBull"
            elif "Weak Bear" in s: cls = "WeakBear"
            elif "Strong Bear" in s: cls = "StrongBear"
            return f"<span class='regime-{cls}'>{s}</span>"

    df_styled = df.copy()

    # Build dynamic column order: yearly left, weekly right; include transitions if present
    base_cols = ["Entity", "Close", "Macro", "Micro"]
    if "Transition" in df_styled.columns:
        base_cols.append("Transition")

    wk_cols = []
    if include_weekly:
        if "WeeklyMacro" in df_styled.columns: wk_cols.append("WeeklyMacro")
        if "WeeklyMicro" in df_styled.columns: wk_cols.append("WeeklyMicro")
        if "WeeklyTransition" in df_styled.columns: wk_cols.append("WeeklyTransition")

    daily_cols = [c for c in ["DailyMacro", "DailyMicro", "DailyTransition"] if c in df_styled.columns]

    session_cols = [c for c in ["Session", "SessionMacro", "SessionMicro", "SessionTransition"] if c in df_styled.columns]

    cols = [c for c in base_cols if c in df_styled.columns] + wk_cols + daily_cols + session_cols + \
           [c for c in df_styled.columns if c not in base_cols + wk_cols + daily_cols + session_cols]

    if not df_styled.empty:
        df_styled = df_styled[cols]

    # Apply styling to regime columns
    if "Macro" in df_styled.columns:
        df_styled["Macro"] = df_styled["Macro"].apply(lambda v: style_label(v, weekly=False))
    if "Micro" in df_styled.columns:
        df_styled["Micro"] = df_styled["Micro"].apply(lambda v: style_label(v, weekly=False))
    if include_weekly and "WeeklyMacro" in df_styled.columns:
        df_styled["WeeklyMacro"] = df_styled["WeeklyMacro"].apply(lambda v: style_label(v, weekly=True))
    if include_weekly and "WeeklyMicro" in df_styled.columns:
        df_styled["WeeklyMicro"] = df_styled["WeeklyMicro"].apply(lambda v: style_label(v, weekly=True))
    # Daily and Session labels left unstyled for contrast; can style similarly if desired.

    # Format Close values
    if "Close" in df_styled.columns:
        df_styled["Close"] = df_styled["Close"].apply(
            lambda x: f"{x:.2f}" if pd.notnull(x) and isinstance(x, (int, float, np.floating)) else str(x)
        )

    table_html = f"""
    <div style="overflow-x: auto; max-height: 500px; overflow-y: auto; width: 100%; border-radius: 12px; border: 1px solid #252a3a;">
    <style>
        .regime-table-wrapper {{
            min-width: 100%;
        }}
        .regime-table-wrapper table {{
            border-collapse: separate;
            width: max-content;   /* allow table to expand naturally */
            min-width: 100%;      /* but never shrink below container */
        }}
        .regime-table-wrapper thead th {{
            position: sticky;
            top: 0;
            z-index: 2;
            background: linear-gradient(135deg, #1f2937, #374151) !important;
            white-space: nowrap;
            padding: 8px 16px;  /* add breathing space */
        }}
        .regime-table-wrapper tbody td {{
            white-space: nowrap;
            text-overflow: ellipsis;
            overflow: hidden;
            padding: 6px 14px;  /* keep cells roomy */
        }}
    </style>
    <div class="regime-table-wrapper">
        {df_styled.to_html(escape=False, index=False)}
    </div>
    </div>
    """
    st.markdown(table_html, unsafe_allow_html=True)



def enhanced_plot_series(df: pd.DataFrame, title: str, color="#1f77b4") -> go.Figure:
    """Enhanced plotting with better styling and hover info"""
    fig = go.Figure()
    if isinstance(df, pd.DataFrame) and not df.empty and "Close" in df.columns:
        x_vals = sanitize_series(df.index)
        y_vals = sanitize_series(df["Close"])
        if len(x_vals) == len(y_vals) and len(y_vals) > 0:
            fig.add_trace(go.Scatter(
                x=x_vals,
                y=y_vals,
                mode="lines",
                line=dict(color=color, width=2.5),
                name=title,
                hovertemplate="<b>%{fullData.name}</b><br>" +
                              "Date: %{x}<br>" +
                              "Close: %{y:.2f}<br>" +
                              "<extra></extra>"
            ))
    fig.update_layout(
        title=dict(text=title, font=dict(size=18, color="#ffffff"), x=0.02),
        paper_bgcolor="#0e1117",
        plot_bgcolor="#0e1117",
        font=dict(color="#e0e0e0", family="Inter"),
        margin=dict(l=20, r=20, t=50, b=30),
        xaxis=dict(showgrid=True, gridcolor="#374151", gridwidth=0.5, showline=True, linecolor="#4b5563"),
        yaxis=dict(showgrid=True, gridcolor="#374151", gridwidth=0.5, showline=True, linecolor="#4b5563"),
        hovermode='x unified'
    )
    st.plotly_chart(fig, use_container_width=True)
    return fig

def figure_to_png_bytes(fig: go.Figure, width=1000, height=500) -> bytes:
    try:
        return fig.to_image(format="png", width=width, height=height, scale=2)
    except Exception:
        return b""

def export_pdf(sections: dict, filename: str, commentary: str = "", figures: dict = None) -> bytes:
    buff = io.BytesIO()
    doc = SimpleDocTemplate(buff, pagesize=landscape(letter))
    styles = getSampleStyleSheet()
    elements = []
    elements += [Paragraph("MetaMacro Research Report", styles["Title"])]
    elements += [Paragraph(datetime.now().strftime("%Y-%m-%d %H:%M"), styles["Normal"]), Spacer(1, 12)]
    if commentary:
        elements += [Paragraph("Market Commentary", styles["Heading2"])]
        elements += [Paragraph(commentary, styles["BodyText"]), Spacer(1, 12)]
    for name, df in sections.items():
        elements.append(Paragraph(str(name), styles["Heading2"]))
        if df is not None and isinstance(df, pd.DataFrame) and not df.empty:
            clean = df.copy()
            # Strip HTML spans
            for c in ["Macro", "Micro", "WeeklyMacro", "WeeklyMicro", "DailyMacro", "DailyMicro"]:
                if c in clean.columns:
                    clean[c] = clean[c].astype(str).str.replace(r"<.*?>", "", regex=True)
            data = [clean.columns.tolist()] + clean.values.tolist()
            table = Table(data, repeatRows=1)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1f77b4")),
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0,0), (-1,0), 8),
                ('BACKGROUND', (0,1), (-1,-1), colors.HexColor("#161a25")),
                ('TEXTCOLOR', (0,1), (-1,-1), colors.white),
                ('GRID', (0,0), (-1,-1), 0.25, colors.gray)
            ]))
            elements += [table, Spacer(1, 16)]
        else:
            elements += [Paragraph("No data", styles["Italic"]), Spacer(1, 12)]
        if figures and name in figures and figures[name]:
            img_bytes = io.BytesIO(figures[name])
            elements += [RLImage(img_bytes, width=720, height=360), Spacer(1, 16)]
    doc.build(elements)
    buff.seek(0)
    return buff.read()

# ---------------- AUTO-REFRESH FUNCTIONALITY ----------------
def check_auto_refresh():
    """Handle auto-refresh functionality"""
    if st.session_state.user_settings.get('auto_refresh', False):
        if st.session_state.last_refresh is None:
            st.session_state.last_refresh = datetime.now()
        time_since_refresh = (datetime.now() - st.session_state.last_refresh).total_seconds()
        if time_since_refresh >= 300:  # 5 minutes
            st.session_state.last_refresh = datetime.now()
            st.cache_data.clear()
            st.rerun()

# ---------------- HEADER + AUTO REFRESH ----------------
check_auto_refresh()
refresh_text = f"Last updated: {st.session_state.last_refresh.strftime('%H:%M:%S')}" if st.session_state.last_refresh else ""
st.markdown(f"""
<div class='mm-header'>
    MetaMacro Research Dashboard
    <div class='refresh-indicator'>{refresh_text}</div>
</div>
""", unsafe_allow_html=True)

enhanced_legend_html = """
<div class='mm-legend'>
  <div class='legend-item'><span class='legend-dot' style='background:#10b981;'></span>Yearly Strong Bull</div>
  <div class='legend-item'><span class='legend-dot' style='background:#34d399;'></span>Yearly Weak Bull</div>
  <div class='legend-item'><span class='legend-dot' style='background:#fbbf24;'></span>Yearly Weak Bear</div>
  <div class='legend-item'><span class='legend-dot' style='background:#ef4444;'></span>Yearly Strong Bear</div>
  <div class='legend-item'><span class='legend-dot' style='background:#9ca3af;'></span>Neutral</div>
  <div class='legend-item'><span class='legend-dot' style='background:#3b82f6;'></span>Weekly Strong Bull</div>
  <div class='legend-item'><span class='legend-dot' style='background:#60a5fa;'></span>Weekly Weak Bull</div>
  <div class='legend-item'><span class='legend-dot' style='background:#a855f7;'></span>Daily Bullish</div>
  <div class='legend-item'><span class='legend-dot' style='background:#f59e0b;'></span>Session Bullish</div>
</div>
"""
st.markdown(enhanced_legend_html, unsafe_allow_html=True)

# ---------------- ENHANCED SIDEBAR ----------------
st.sidebar.header("📊 Data Configuration")
uploaded = st.sidebar.file_uploader("Upload Universe CSV", type=["csv"])
period = st.sidebar.selectbox("Period", ["1y", "2y", "5y", "max"], index=1)
interval = st.sidebar.selectbox("Interval", ["1d", "1wk", "1mo"], index=0)

# Data management
col1_sidebar, col2_sidebar = st.sidebar.columns(2)
with col1_sidebar:
    if st.button("♻️ Refresh", help="Clear cache and reload data"):
        st.cache_data.clear()
        st.session_state.last_refresh = datetime.now()
        st.rerun()
with col2_sidebar:
    if st.button("⚡ Force Update", help="Force update all data"):
        st.cache_data.clear()
        st.session_state.data_loaded = False
        st.rerun()

# Display options
st.sidebar.header("🎛️ Display Options")
show_yearly_kpis = st.sidebar.checkbox("Show Yearly KPI row", value=True)
show_weekly_kpis = st.sidebar.checkbox("Show Weekly KPI row", value=True)
show_daily_kpis  = st.sidebar.checkbox("Show Daily KPI row", value=True)
show_session_kpis = st.sidebar.checkbox("Show Session KPI row", value=True)   # NEW
show_weekly_cols = st.sidebar.checkbox("Show Weekly columns in tables/PDFs", value=True)

# Advanced settings
st.sidebar.header("⚙️ Advanced Settings")
st.session_state.user_settings['auto_refresh'] = st.sidebar.checkbox(
    "Auto-refresh (5min)",
    value=st.session_state.user_settings.get('auto_refresh', False),
    help="Automatically refresh data every 5 minutes"
)
show_data_quality = st.sidebar.checkbox("Show data quality warnings", value=True)

# Keyboard shortcuts
st.sidebar.markdown("""
<div class="shortcuts-help">
<strong>Keyboard Shortcuts:</strong><br>
• R: Refresh data<br>
• Ctrl+R: Force reload<br>
• F: Toggle filters<br>
• E: Export current view
</div>
""", unsafe_allow_html=True)

# ====================== MARKET MONITOR (HOMEPAGE) ======================
st.header("🌍 Market Monitor")

try:
    with st.spinner('Loading market indices...'):
        custom_mkt = build_yahoo_composite(period=period, interval=interval)
        vix = fetch_data("^VIX", period=period, interval=interval)

    if show_data_quality:
        validate_data_quality(custom_mkt, "Composite Market")
        validate_data_quality(vix, "VIX")

    idx = custom_mkt.index.intersection(vix.index) if isinstance(custom_mkt, pd.DataFrame) and isinstance(vix, pd.DataFrame) else pd.Index([])
    comp_vs_vix = ohlc_divide(custom_mkt.loc[idx], vix.loc[idx]) if len(idx) > 0 else pd.DataFrame()

    # Index flows
    with st.spinner('Loading index data...'):
        index_tickers = ["^IXIC", "^GSPC", "^DJI", "^RUT"]
        index_data = safe_fetch_with_progress(index_tickers, period, interval)
        ixic = index_data.get("^IXIC", pd.DataFrame())
        gspc = index_data.get("^GSPC", pd.DataFrame())
        dji  = index_data.get("^DJI", pd.DataFrame())
        rut  = index_data.get("^RUT", pd.DataFrame())

    flows = {
        "Russell 2000 (^RUT) / Market": ohlc_divide(rut, custom_mkt),
        "Nasdaq (^IXIC) / Market": ohlc_divide(ixic, custom_mkt),
        "Dow (^DJI) / Market": ohlc_divide(dji, custom_mkt),
        "S&P 500 (^GSPC) / Market": ohlc_divide(gspc, custom_mkt),
    }

    # Regime summary table rows (Yearly + Weekly + Daily + Session)
    market_entities = {"Composite Market": custom_mkt, "Composite / VIX": comp_vs_vix, **flows}
    rows = []
    for name, df in market_entities.items():
        if isinstance(df, pd.DataFrame) and not df.empty:
            y = classify_regime(df)
            w = classify_weekly_regime(df)
            d = classify_daily_regime(df)
            s = classify_session_regimes(df)   # NEW
            rows.append(compute_latest_labels(name, y, w, d, s))
    market_table_df = pd.DataFrame(rows)
    rows_by_name = {r["Entity"]: r for r in rows}

    # KPI cards (Yearly)
    if show_yearly_kpis and not market_table_df.empty:
        st.markdown("<div class='mm-card'><h2>📊 Yearly KPIs</h2>", unsafe_allow_html=True)
        row1_cols = st.columns(2, gap="large")
        with row1_cols[0]:
            st.markdown(enhanced_regime_card("Composite Market", rows_by_name.get("Composite Market", {}), weekly=False), unsafe_allow_html=True)
        with row1_cols[1]:
            st.markdown(enhanced_regime_card("Composite / VIX", rows_by_name.get("Composite / VIX", {}), weekly=False), unsafe_allow_html=True)
        row2_cols = st.columns(4, gap="large")
        for i, name in enumerate(flows.keys()):
            with row2_cols[i]:
                st.markdown(enhanced_regime_card(name, rows_by_name.get(name, {}), weekly=False), unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # KPI cards (Weekly / blue accent)
    if show_weekly_kpis and not market_table_df.empty:
        st.markdown("<div class='mm-card'><h2>📊 Weekly KPIs</h2>", unsafe_allow_html=True)
        row1_cols_w = st.columns(2, gap="large")
        with row1_cols_w[0]:
            st.markdown(enhanced_regime_card("Composite Market (Weekly)", rows_by_name.get("Composite Market", {}), weekly=True), unsafe_allow_html=True)
        with row1_cols_w[1]:
            st.markdown(enhanced_regime_card("Composite / VIX (Weekly)", rows_by_name.get("Composite / VIX", {}), weekly=True), unsafe_allow_html=True)
        row2_cols_w = st.columns(4, gap="large")
        for i, name in enumerate(flows.keys()):
            with row2_cols_w[i]:
                st.markdown(enhanced_regime_card(f"{name} (Weekly)", rows_by_name.get(name, {}), weekly=True), unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # KPI cards (Daily / purple accent)
    if show_daily_kpis and not market_table_df.empty:
        st.markdown("<div class='mm-card'><h2>📊 Daily KPIs</h2>", unsafe_allow_html=True)
        row1_cols_d = st.columns(2, gap="large")
        with row1_cols_d[0]:
            st.markdown(enhanced_regime_card("Composite Market (Daily)", rows_by_name.get("Composite Market", {}), daily=True), unsafe_allow_html=True)
        with row1_cols_d[1]:
            st.markdown(enhanced_regime_card("Composite / VIX (Daily)", rows_by_name.get("Composite / VIX", {}), daily=True), unsafe_allow_html=True)
        row2_cols_d = st.columns(4, gap="large")
        for i, name in enumerate(flows.keys()):
            with row2_cols_d[i]:
                st.markdown(enhanced_regime_card(f"{name} (Daily)", rows_by_name.get(name, {}), daily=True), unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # KPI cards (Session / orange accent)
    if show_session_kpis and not market_table_df.empty:
        st.markdown("<div class='mm-card'><h2>📊 Session KPIs</h2>", unsafe_allow_html=True)
        row1_cols_s = st.columns(2, gap="large")
        with row1_cols_s[0]:
            st.markdown(enhanced_regime_card("Composite Market (Session)", rows_by_name.get("Composite Market", {}), session=True), unsafe_allow_html=True)
        with row1_cols_s[1]:
            st.markdown(enhanced_regime_card("Composite / VIX (Session)", rows_by_name.get("Composite / VIX", {}), session=True), unsafe_allow_html=True)
        row2_cols_s = st.columns(4, gap="large")
        for i, name in enumerate(flows.keys()):
            with row2_cols_s[i]:
                st.markdown(enhanced_regime_card(f"{name} (Session)", rows_by_name.get(name, {}), session=True), unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # Enhanced data summary
    if not market_table_df.empty:
        st.markdown(enhanced_data_summary(market_table_df), unsafe_allow_html=True)

    # Regime table + filter
    # Regime table + filter
    st.markdown("<div class='mm-card'><h2>📋 Market Regime States</h2>", unsafe_allow_html=True)

    m_filter = st.selectbox(
        "Filter Macro Regime",
        ["All", "Strong Bull", "Weak Bull", "Strong Bear", "Weak Bear", "Neutral"],
        key="market_filter"
    )
    mt_view = market_table_df if m_filter == "All" else market_table_df[market_table_df["Macro"] == m_filter]
    enhanced_style_regime_table(mt_view, include_weekly=show_weekly_cols)

    st.markdown("</div>", unsafe_allow_html=True)


    # Charts expander + Enhanced export options
    with st.expander("📈 Market Flow Charts", expanded=False):
        figs = {}
        figs["Composite Market"] = figure_to_png_bytes(enhanced_plot_series(custom_mkt, "Composite Market Index"))
        figs["Composite / VIX"]  = figure_to_png_bytes(enhanced_plot_series(comp_vs_vix, "Composite / VIX", color="#ff8800"))

        # Multi-select overlay for flows
        flow_choices = st.multiselect("Select Index Flows to overlay", list(flows.keys()), default=list(flows.keys())[:2])
        if flow_choices:
            fig = go.Figure()
            palette = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]
            for i, name in enumerate(flow_choices):
                df = flows[name]
                if isinstance(df, pd.DataFrame) and not df.empty and "Close" in df.columns:
                    x_vals = sanitize_series(df.index)
                    y_vals = sanitize_series(df["Close"])
                    if len(x_vals) == len(y_vals) and len(y_vals) > 0:
                        fig.add_trace(go.Scatter(
                            x=x_vals,
                            y=y_vals,
                            mode="lines",
                            name=name,
                            line=dict(color=palette[i % len(palette)], width=2.5),
                            hovertemplate="<b>%{fullData.name}</b><br>Date: %{x}<br>Close: %{y:.2f}<extra></extra>"
                        ))
            fig.update_layout(
                title="Index Flows vs Market",
                paper_bgcolor="#0e1117",
                plot_bgcolor="#0e1117",
                font=dict(color="#e0e0e0", family="Inter"),
                xaxis=dict(showgrid=True, gridcolor="#374151"),
                yaxis=dict(showgrid=True, gridcolor="#374151"),
                hovermode='x unified',
                margin=dict(l=20, r=20, t=50, b=30),
            )
            st.plotly_chart(fig, use_container_width=True, key="index_flows_overlay")
            figs["Index Flows Overlay"] = figure_to_png_bytes(fig)

        # Enhanced export options
        col1_exp, col2_exp = st.columns(2)
        with col1_exp:
            if st.button("📄 Export PDF", key="export_market_pdf"):
                export_cols = ["Entity", "Close", "Macro", "Micro", "Transition"]
                if show_weekly_cols:
                    for c in ["WeeklyMacro", "WeeklyMicro", "WeeklyTransition"]:
                        if c in mt_view.columns:
                            export_cols.append(c)
                for c in ["DailyMacro", "DailyMicro", "DailyTransition"]:
                    if c in mt_view.columns:
                        export_cols.append(c)
                for c in ["Session", "SessionMacro", "SessionMicro", "SessionTransition"]:
                    if c in mt_view.columns:
                        export_cols.append(c)
                mt_export = mt_view[export_cols] if not mt_view.empty else mt_view
                commentary = (
                    f"Composite yearly regime: {rows_by_name.get('Composite Market', {}).get('Macro', 'N/A')}. "
                    f"Weekly: {rows_by_name.get('Composite Market', {}).get('WeeklyMacro', 'N/A')}. "
                    f"Daily: {rows_by_name.get('Composite Market', {}).get('DailyMacro', 'N/A')}. "
                    f"Session: {rows_by_name.get('Composite Market', {}).get('SessionMacro', 'N/A')}."
                )
                pdf_bytes = export_pdf(
                    sections={"Market Regimes": mt_export},
                    filename="market_section.pdf",
                    commentary=commentary,
                    figures=figs
                )
                st.download_button("📥 Download Market PDF", data=pdf_bytes, file_name="MetaMacro_Market.pdf", mime="application/pdf")

        with col2_exp:
            if st.button("📊 Export Excel", key="export_market_excel"):
                export_cols = ["Entity", "Close", "Macro", "Micro", "Transition"]
                if show_weekly_cols:
                    for c in ["WeeklyMacro", "WeeklyMicro", "WeeklyTransition"]:
                        if c in mt_view.columns:
                            export_cols.append(c)
                for c in ["DailyMacro", "DailyMicro", "DailyTransition"]:
                    if c in mt_view.columns:
                        export_cols.append(c)
                for c in ["Session", "SessionMacro", "SessionMicro", "SessionTransition"]:
                    if c in mt_view.columns:
                        export_cols.append(c)
                mt_export = mt_view[export_cols] if not mt_view.empty else mt_view
                excel_bytes = export_to_excel({"Market_Regimes": mt_export})
                st.download_button("📥 Download Market Excel", data=excel_bytes, file_name="MetaMacro_Market.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

except Exception as e:
    show_alert(f"Error loading market data: {str(e)}", "error")
    st.stop()

# ====================== TABS ======================
tab1, tab2, tab3, tab4 = st.tabs(["Sub-Industry vs Sector", "Stock vs Sub-Industry", "Market Comparisons", "MetaMacro Research"])

if uploaded:
    try:
        with st.spinner('Loading universe data...'):
            uni = load_universe(uploaded)

        if show_data_quality:
            show_alert(f"Universe loaded: {len(uni)} entities across {uni['Sector'].nunique()} sectors", "success")

        # Optional Sector filter on sidebar
        all_sectors = ["All"] + sorted(uni["Sector"].unique().tolist())
        sector_choice = st.sidebar.selectbox("Filter by Sector", all_sectors)
        if sector_choice != "All":
            uni = uni[uni["Sector"] == sector_choice]
            if show_data_quality:
                show_alert(f"Filtered to {sector_choice}: {len(uni)} entities", "info")

        tickers = sorted(set(uni['Ticker']) | set(uni['SectorIndex']))
        ohlc_map = safe_fetch_with_progress(tickers, period, interval)

        with st.spinner('Building sub-industry indices...'):
            sub_idx = build_subindustry_indices(uni, ohlc_map)

        st.session_state.data_loaded = True

        # ---- TAB 1: Sub-Industry vs Sector ----
        with tab1:
            st.markdown("<div class='mm-card'><h2>📋 Sub-Industry vs Sector</h2>", unsafe_allow_html=True)
            all_subs1 = ["All"] + sorted(uni["SubIndustry"].unique().tolist())
            sub_choice1 = st.selectbox("Filter by Sub-Industry", all_subs1, key="sub_filter_1")
            uni_tab1 = uni if sub_choice1 == "All" else uni[uni["SubIndustry"] == sub_choice1]

            rows1 = []
            for sub, chunk in uni_tab1.groupby("SubIndustry"):
                sect = chunk["SectorIndex"].iloc[0]
                ratio = ohlc_divide(sub_idx.get(sub, pd.DataFrame()), ohlc_map.get(sect, pd.DataFrame()))
                if isinstance(ratio, pd.DataFrame) and not ratio.empty:
                    y = classify_regime(ratio)
                    w = classify_weekly_regime(ratio)
                    d = classify_daily_regime(ratio)
                    s = classify_session_regimes(ratio)
                    rows1.append(compute_latest_labels(f"{sub} / {sect}", y, w, d, s))
            df_view1 = pd.DataFrame(rows1)

            if not df_view1.empty:
                st.markdown(enhanced_data_summary(df_view1), unsafe_allow_html=True)

            f1 = st.selectbox(
            "Filter Macro Regime",
            ["All","Strong Bull","Weak Bull","Strong Bear","Weak Bear","Neutral"],
            key="filter_1"
            )
            df1v = df_view1 if f1 == "All" else df_view1[df_view1["Macro"] == f1]
            enhanced_style_regime_table(df1v, include_weekly=show_weekly_cols)


            # Multi-select overlay chart
            if not df1v.empty:
                choices1 = st.multiselect("Select entities to chart", df1v["Entity"].tolist(), key="chart_1")
                if choices1:
                    fig = go.Figure()
                    palette = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"]
                    for i, choice in enumerate(choices1):
                        sub, sect = choice.split(" / ", 1)
                        series = ohlc_divide(sub_idx.get(sub, pd.DataFrame()), ohlc_map.get(sect, pd.DataFrame()))
                        if isinstance(series, pd.DataFrame) and not series.empty and "Close" in series.columns:
                            x_vals = sanitize_series(series.index)
                            y_vals = sanitize_series(series["Close"])
                            if len(x_vals) == len(y_vals) and len(y_vals) > 0:
                                fig.add_trace(go.Scatter(
                                    x=x_vals,
                                    y=y_vals,
                                    mode="lines",
                                    name=choice,
                                    line=dict(color=palette[i % len(palette)], width=2.5)
                                ))
                    fig.update_layout(
                        title="Sub-Industry vs Sector Flows",
                        paper_bgcolor="#0e1117",
                        plot_bgcolor="#0e1117",
                        font=dict(color="#e0e0e0", family="Inter"),
                        xaxis=dict(showgrid=True, gridcolor="#374151"),
                        yaxis=dict(showgrid=True, gridcolor="#374151"),
                        hovermode='x unified',
                        margin=dict(l=20, r=20, t=50, b=30),
                    )
                    st.plotly_chart(fig, use_container_width=True, key="subindustry_sector_overlay")

            # Export options
            col1_exp1, col2_exp1 = st.columns(2)
            with col1_exp1:
                if st.button("📄 Export PDF", key="export_tab1_pdf"):
                    export_cols = ["Entity", "Close", "Macro", "Micro", "Transition"]
                    if show_weekly_cols:
                        for c in ["WeeklyMacro", "WeeklyMicro", "WeeklyTransition"]:
                            if c in df1v.columns:
                                export_cols.append(c)
                    for c in ["DailyMacro", "DailyMicro", "DailyTransition"]:
                        if c in df1v.columns:
                            export_cols.append(c)
                    for c in ["Session", "SessionMacro", "SessionMicro", "SessionTransition"]:
                        if c in df1v.columns:
                            export_cols.append(c)
                    df1_export = df1v[export_cols] if not df1v.empty else df1v
                    pdf_bytes = export_pdf({"SubIndustry_vs_Sector": df1_export},
                                           filename="subindustry_sector.pdf")
                    st.download_button("📥 Download PDF",
                                       data=pdf_bytes,
                                       file_name="MetaMacro_SubIndustry_Sector.pdf",
                                       mime="application/pdf")
            with col2_exp1:
                if st.button("📊 Export Excel", key="export_tab1_excel"):
                    export_cols = ["Entity", "Close", "Macro", "Micro", "Transition"]
                    if show_weekly_cols:
                        for c in ["WeeklyMacro", "WeeklyMicro", "WeeklyTransition"]:
                            if c in df1v.columns:
                                export_cols.append(c)
                    for c in ["DailyMacro", "DailyMicro", "DailyTransition"]:
                        if c in df1v.columns:
                            export_cols.append(c)
                    for c in ["Session", "SessionMacro", "SessionMicro", "SessionTransition"]:
                        if c in df1v.columns:
                            export_cols.append(c)
                    df1_export = df1v[export_cols] if not df1v.empty else df1v
                    excel_bytes = export_to_excel({"SubIndustry_vs_Sector": df1_export})
                    st.download_button("📥 Download Excel",
                                       data=excel_bytes,
                                       file_name="MetaMacro_SubIndustry_Sector.xlsx",
                                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        # ---- TAB 2: Stock vs Sub-Industry ----
        with tab2:
            st.markdown("<div class='mm-card'><h2>📋 Stock vs Sub-Industry</h2>", unsafe_allow_html=True)
            all_subs2 = ["All"] + sorted(uni["SubIndustry"].unique().tolist())
            sub_choice2 = st.selectbox("Filter by Sub-Industry", all_subs2, key="sub_filter_2")
            uni_tab2 = uni if sub_choice2 == "All" else uni[uni["SubIndustry"] == sub_choice2]

            rows2 = []
            for _, r in uni_tab2.iterrows():
                t, sub = r["Ticker"], r["SubIndustry"]
                lhs = ohlc_map.get(t, pd.DataFrame())
                rhs = sub_idx.get(sub, pd.DataFrame())
                ratio = ohlc_divide(lhs, rhs)
                if isinstance(ratio, pd.DataFrame) and not ratio.empty:
                    y = classify_regime(ratio)
                    w = classify_weekly_regime(ratio)
                    d = classify_daily_regime(ratio)
                    s = classify_session_regimes(ratio)
                    rows2.append(compute_latest_labels(f"{t} / {sub}", y, w, d, s))
            df_view2 = pd.DataFrame(rows2)

            if not df_view2.empty:
                st.markdown(enhanced_data_summary(df_view2), unsafe_allow_html=True)

            f2 = st.selectbox(
                "Filter Macro Regime",
                ["All", "Strong Bull", "Weak Bull", "Strong Bear", "Weak Bear", "Neutral"],
                key="filter_2"
                )
            df2v = df_view2 if f2 == "All" else df_view2[df_view2["Macro"] == f2]
            enhanced_style_regime_table(df2v, include_weekly=show_weekly_cols)


            # Multi-select overlay chart
            if not df2v.empty:
                choices2 = st.multiselect("Select stocks to chart", df2v["Entity"].tolist(), key="chart_2")
                if choices2:
                    fig = go.Figure()
                    palette = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"]
                    for i, choice in enumerate(choices2):
                        # robust split in case sub names contain slashes
                        lhs_sym, rhs_sub = choice.split(" / ", 1)
                        lhs_df = ohlc_map.get(lhs_sym, pd.DataFrame())
                        rhs_df = sub_idx.get(rhs_sub, pd.DataFrame())
                        series = ohlc_divide(lhs_df, rhs_df)
                        if isinstance(series, pd.DataFrame) and not series.empty and "Close" in series.columns:
                            x_vals = sanitize_series(series.index)
                            y_vals = sanitize_series(series["Close"])
                            if len(x_vals) == len(y_vals) and len(y_vals) > 0:
                                fig.add_trace(go.Scatter(
                                    x=x_vals,
                                    y=y_vals,
                                    mode="lines",
                                    name=choice,
                                    line=dict(color=palette[i % len(palette)], width=2.5),
                                    hovertemplate="<b>%{fullData.name}</b><br>Date: %{x}<br>Close: %{y:.2f}<extra></extra>"
                                ))
                    fig.update_layout(
                        title="Stock vs Sub-Industry Flows",
                        paper_bgcolor="#0e1117",
                        plot_bgcolor="#0e1117",
                        font=dict(color="#e0e0e0", family="Inter"),
                        xaxis=dict(showgrid=True, gridcolor="#374151"),
                        yaxis=dict(showgrid=True, gridcolor="#374151"),
                        hovermode='x unified',
                        margin=dict(l=20, r=20, t=50, b=30),
                    )
                    st.plotly_chart(fig, use_container_width=True, key="stock_subindustry_overlay")

            # Export options (include Session columns if present)
            col1f, col2f = st.columns(2)
            with col1f:
                if st.button("📄 Export PDF", key="export_2_pdf"):
                    export_cols = ["Entity", "Close", "Macro", "Micro", "Transition"]
                    if show_weekly_cols:
                        for c in ["WeeklyMacro", "WeeklyMicro", "WeeklyTransition"]:
                            if c in df2v.columns: export_cols.append(c)
                    for c in ["DailyMacro", "DailyMicro", "DailyTransition"]:
                        if c in df2v.columns: export_cols.append(c)
                    for c in ["Session", "SessionMacro", "SessionMicro", "SessionTransition"]:
                        if c in df2v.columns: export_cols.append(c)
                    df2_export = df2v[export_cols] if not df2v.empty else df2v
                    pdf_bytes = export_pdf({"Stock_vs_SubIndustry": df2_export}, "view2.pdf")
                    st.download_button(
                        "📥 Download PDF",
                        data=pdf_bytes,
                        file_name="MetaMacro_Stock_vs_SubIndustry.pdf",
                        mime="application/pdf"
                    )
            with col2f:
                if st.button("📊 Export Excel", key="export_2_excel"):
                    export_cols = ["Entity", "Close", "Macro", "Micro", "Transition"]
                    if show_weekly_cols:
                        for c in ["WeeklyMacro", "WeeklyMicro", "WeeklyTransition"]:
                            if c in df2v.columns: export_cols.append(c)
                    for c in ["DailyMacro", "DailyMicro", "DailyTransition"]:
                        if c in df2v.columns: export_cols.append(c)
                    for c in ["Session", "SessionMacro", "SessionMicro", "SessionTransition"]:
                        if c in df2v.columns: export_cols.append(c)
                    df2_export = df2v[export_cols] if not df2v.empty else df2v
                    excel_bytes = export_to_excel({"Stock_vs_SubIndustry": df2_export})
                    st.download_button(
                        "📥 Download Excel",
                        data=excel_bytes,
                        file_name="MetaMacro_Stock_vs_SubIndustry.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
            st.markdown("</div>", unsafe_allow_html=True)
        # ---- TAB 3: Market Comparisons ----
        with tab3:
            st.markdown("<div class='mm-card'><h2>📋 Market Comparisons</h2>", unsafe_allow_html=True)

            all_entities3 = sorted(ohlc_map.keys())
            lhs_choice = st.selectbox("Select first entity (LHS)", all_entities3, key="mc_lhs")
            rhs_choice = st.selectbox("Select second entity (RHS)", all_entities3, key="mc_rhs")

            ratio3 = pd.DataFrame()
            if lhs_choice and rhs_choice and lhs_choice in ohlc_map and rhs_choice in ohlc_map:
                lhs_df = ohlc_map.get(lhs_choice, pd.DataFrame())
                rhs_df = ohlc_map.get(rhs_choice, pd.DataFrame())
                ratio3 = ohlc_divide(lhs_df, rhs_df)

            rows3 = []
            if isinstance(ratio3, pd.DataFrame) and not ratio3.empty:
                y = classify_regime(ratio3)
                w = classify_weekly_regime(ratio3)
                d = classify_daily_regime(ratio3)
                s = classify_session_regimes(ratio3)
                rows3.append(compute_latest_labels(f"{lhs_choice} / {rhs_choice}", y, w, d, s))

            df_view3 = pd.DataFrame(rows3)

            if not df_view3.empty:
                st.markdown(enhanced_data_summary(df_view3), unsafe_allow_html=True)
            f3 = st.selectbox(
                "Filter Macro Regime",
                ["All", "Strong Bull", "Weak Bull", "Strong Bear", "Weak Bear", "Neutral"],
                key="filter_3"
            )
            df3v = df_view3 if f3 == "All" else df_view3[df_view3["Macro"] == f3]
            enhanced_style_regime_table(df3v, include_weekly=show_weekly_cols)

           
            # Chart
            if isinstance(ratio3, pd.DataFrame) and not ratio3.empty and "Close" in ratio3.columns:
                fig = go.Figure()
                x_vals = sanitize_series(ratio3.index)
                y_vals = sanitize_series(ratio3["Close"])
                if len(x_vals) == len(y_vals) and len(y_vals) > 0:
                    fig.add_trace(go.Scatter(
                        x=x_vals,
                        y=y_vals,
                        mode="lines",
                        name=f"{lhs_choice}/{rhs_choice}",
                        line=dict(color="#1f77b4", width=2.5),
                        hovertemplate="<b>%{fullData.name}</b><br>Date: %{x}<br>Close: %{y:.2f}<extra></extra>"
                    ))
                fig.update_layout(
                    title=f"{lhs_choice} / {rhs_choice} Flow",
                    paper_bgcolor="#0e1117",
                    plot_bgcolor="#0e1117",
                    font=dict(color="#e0e0e0", family="Inter"),
                    xaxis=dict(showgrid=True, gridcolor="#374151"),
                    yaxis=dict(showgrid=True, gridcolor="#374151"),
                    hovermode='x unified',
                    margin=dict(l=20, r=20, t=50, b=30),
                )
                st.plotly_chart(fig, use_container_width=True, key="market_comparison_chart")

            # Export
            col1g, col2g = st.columns(2)
            with col1g:
                if st.button("📄 Export PDF", key="export_3_pdf"):
                    export_cols = ["Entity", "Close", "Macro", "Micro", "Transition"]
                    if show_weekly_cols:
                        for c in ["WeeklyMacro", "WeeklyMicro", "WeeklyTransition"]:
                            if c in df3v.columns: export_cols.append(c)
                    for c in ["DailyMacro", "DailyMicro", "DailyTransition"]:
                        if c in df3v.columns: export_cols.append(c)
                    for c in ["Session", "SessionMacro", "SessionMicro", "SessionTransition"]:
                        if c in df3v.columns: export_cols.append(c)
                    df3_export = df3v[export_cols] if not df3v.empty else df3v
                    pdf_bytes = export_pdf({"Market_Comparison": df3_export}, "view3.pdf")
                    st.download_button(
                        "📥 Download PDF",
                        data=pdf_bytes,
                        file_name="MetaMacro_Market_Comparison.pdf",
                        mime="application/pdf"
                    )
            with col2g:
                if st.button("📊 Export Excel", key="export_3_excel"):
                    export_cols = ["Entity", "Close", "Macro", "Micro", "Transition"]
                    if show_weekly_cols:
                        for c in ["WeeklyMacro", "WeeklyMicro", "WeeklyTransition"]:
                            if c in df3v.columns: export_cols.append(c)
                    for c in ["DailyMacro", "DailyMicro", "DailyTransition"]:
                        if c in df3v.columns: export_cols.append(c)
                    for c in ["Session", "SessionMacro", "SessionMicro", "SessionTransition"]:
                        if c in df3v.columns: export_cols.append(c)
                    df3_export = df3v[export_cols] if not df3v.empty else df3v
                    excel_bytes = export_to_excel({"Market_Comparison": df3_export})
                    st.download_button(
                        "📥 Download Excel",
                        data=excel_bytes,
                        file_name="MetaMacro_Market_Comparison.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
            st.markdown("</div>", unsafe_allow_html=True)
        # ---- TAB 4: MetaMacro Research ----
        with tab4:
            st.markdown("<div class='mm-card'><h2>📑 MetaMacro Research Pack</h2>", unsafe_allow_html=True)

            st.write("Generate a consolidated research report across all sections with commentary and exports.")

            commentary_input = st.text_area("✍️ Add Market Commentary", placeholder="Write your research notes here...")

            # Collect sections (reuse previously computed if available)
            sections = {}
            figs = {}

            # Market table
            if 'market_table_df' in locals() and not market_table_df.empty:
                sections["Market_Regimes"] = market_table_df
                figs["Composite Market"] = figure_to_png_bytes(
                    enhanced_plot_series(custom_mkt, "Composite Market Index"))
                figs["Composite / VIX"] = figure_to_png_bytes(
                    enhanced_plot_series(comp_vs_vix, "Composite / VIX", color="#ff8800"))

            # Tab1
            if 'df_view1' in locals() and not df_view1.empty:
                sections["SubIndustry_vs_Sector"] = df_view1

            # Tab2
            if 'df_view2' in locals() and not df_view2.empty:
                sections["Stock_vs_SubIndustry"] = df_view2

            # Tab3
            if 'df_view3' in locals() and not df_view3.empty:
                sections["Market_Comparison"] = df_view3

            # Export buttons
            col1r, col2r = st.columns(2)
            with col1r:
                if st.button("📄 Export Full PDF", key="export_full_pdf"):
                    pdf_bytes = export_pdf(sections, filename="MetaMacro_Research.pdf",
                                           commentary=commentary_input, figures=figs)
                    st.download_button("📥 Download Full PDF",
                                       data=pdf_bytes,
                                       file_name="MetaMacro_Research.pdf",
                                       mime="application/pdf")
            with col2r:
                if st.button("📊 Export Full Excel", key="export_full_excel"):
                    excel_bytes = export_to_excel(sections, filename="MetaMacro_Research.xlsx")
                    st.download_button("📥 Download Full Excel",
                                       data=excel_bytes,
                                       file_name="MetaMacro_Research.xlsx",
                                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

            # Data Preview
            if sections:
                st.markdown("<div class='mm-card'><h3>📋 Included Sections Preview</h3>", unsafe_allow_html=True)
                for name, df in sections.items():
                    st.subheader(name)
                    enhanced_style_regime_table(df, include_weekly=show_weekly_cols)
    except Exception as e:
        show_alert(f"Error in universe/tabs section: {str(e)}", "error")
        st.stop()
