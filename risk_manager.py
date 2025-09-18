# enhanced_risk_manager.py  (Upgraded — persistence, portfolio/growth plan, VaR budget, stress table)
import io
import sqlite3
from datetime import datetime, timedelta, date
import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf
import plotly.express as px
import plotly.graph_objects as go
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import getSampleStyleSheet
import warnings
warnings.filterwarnings('ignore')

# ---------------------------
# App Config & Styling
# ---------------------------
st.set_page_config(
    page_title="Equities Risk Manager Pro",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1f4e79 0%, #2d5aa0 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .risk-alert {
        background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin: 1rem 0;
    }
    .success-alert {
        background: linear-gradient(135deg, #26de81 0%, #20bf6b 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin: 1rem 0;
    }
    .stTab [data-baseweb="tab-list"] { gap: 8px; }
    .stTab [data-baseweb="tab"] { background-color: #f0f2f6; border-radius: 8px; padding: 10px 20px; }
    .position-card { background: white; padding: 1rem; border-radius: 10px; border-left: 4px solid #1f77b4; margin: .5rem 0; box-shadow: 0 2px 4px rgba(0,0,0,.1); }
    .kpi-line { display:flex; gap:16px; }
    .kpi { flex:1; }
</style>
""", unsafe_allow_html=True)

# ---------------------------
# Persistence (SQLite)
# ---------------------------
DB_PATH = "positions.db"

def sql_connect():
    return sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)

def init_db():
    with sql_connect() as con:
        cur = con.cursor()
        # positions table (symbol is not unique because you may have multiple entries)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            open_date TEXT,
            closed_date TEXT,
            model TEXT,
            trade_status TEXT,
            symbol TEXT,
            name TEXT,
            sector TEXT,
            industry TEXT,
            direction TEXT,
            position_size REAL,
            entry_price REAL,
            current_price REAL,
            stop_loss REAL,
            target_price REAL,
            invested_amount REAL,
            unrealized_pnl REAL,
            pnl_pct REAL,
            beta REAL,
            volatility REAL,
            var REAL,
            high_52 REAL,
            low_52 REAL,
            dist_52h REAL,
            dist_52l REAL,
            market_cap REAL,
            pe_ratio REAL,
            dividend_yield REAL,
            risk_level TEXT,
            notes TEXT,
            index_benchmark TEXT
        )""")
        # single-row portfolio settings
        cur.execute("""
        CREATE TABLE IF NOT EXISTS portfolio_settings (
            id INTEGER PRIMARY KEY CHECK (id=1),
            monday_balance REAL,
            high_watermark REAL,
            current_balance REAL,
            max_dd_tolerance_pct REAL,
            weekly_net_profit REAL,
            recovery_factor_pct REAL,
            recovery_requirement_pct REAL
        )""")
        # single-row growth plan
        cur.execute("""
        CREATE TABLE IF NOT EXISTS growth_plan (
            id INTEGER PRIMARY KEY CHECK (id=1),
            max_monthly_loss_pct REAL,
            max_weekly_loss_pct REAL,
            hard_stop_trade_pct REAL,
            trades_per_week REAL,
            max_trades_per_week REAL,
            avg_rr REAL,
            win_rate_pct REAL,
            loss_rate_pct REAL
        )""")
        con.commit()

def load_positions_from_db() -> pd.DataFrame:
    with sql_connect() as con:
        df = pd.read_sql_query("SELECT * FROM positions ORDER BY id ASC", con)
    return df

def insert_position(row: dict):
    with sql_connect() as con:
        cur = con.cursor()
        cur.execute("""
        INSERT INTO positions (
            open_date, closed_date, model, trade_status, symbol, name, sector, industry,
            direction, position_size, entry_price, current_price, stop_loss, target_price,
            invested_amount, unrealized_pnl, pnl_pct, beta, volatility, var,
            high_52, low_52, dist_52h, dist_52l, market_cap, pe_ratio, dividend_yield,
            risk_level, notes, index_benchmark
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            row.get("Open Date"), row.get("Closed Date"), row.get("Model"), row.get("Trade Status"),
            row.get("Underlying Security"), row.get("Security Name"), row.get("Sector"), row.get("Industry"),
            row.get("Direction"), row.get("Position Size"), row.get("Entry Price"), row.get("Current Price"),
            row.get("Stop Loss") if row.get("Stop Loss") not in (None, "") else None,
            row.get("Target Price") if row.get("Target Price") not in (None, "") else None,
            safe_to_float(row.get("Invested Amount")),
            safe_to_float(row.get("Unrealized PnL")),
            safe_to_float_pct(row.get("PnL %")),
            safe_to_float(row.get("Beta")),
            safe_to_float_pct(row.get("Volatility (%)")),
            safe_to_float(row.get("VaR")),
            safe_to_float(row.get("52W High")),
            safe_to_float(row.get("52W Low")),
            safe_to_float_pct(row.get("Distance from 52W High (%)")),
            safe_to_float_pct(row.get("Distance from 52W Low (%)")),
            safe_to_float(row.get("Market Cap")),
            safe_to_float(row.get("P/E Ratio")),
            safe_to_float_pct(row.get("Dividend Yield (%)")),
            row.get("Risk Level"), row.get("Notes"),
            row.get("Index")
        ))
        con.commit()

def delete_positions_by_ids(ids: list[int]):
    if not ids: return
    with sql_connect() as con:
        cur = con.cursor()
        qmarks = ",".join(["?"] * len(ids))
        cur.execute(f"DELETE FROM positions WHERE id IN ({qmarks})", ids)
        con.commit()

def close_positions_by_ids(ids: list[int]):
    if not ids: return
    today = date.today().isoformat()
    with sql_connect() as con:
        cur = con.cursor()
        qmarks = ",".join(["?"] * len(ids))
        cur.execute(f"UPDATE positions SET trade_status='Closed', closed_date=? WHERE id IN ({qmarks})", (today, *ids))
        con.commit()

def update_position_by_id(
    row_id: int,
    position_size: float,
    entry_price: float,
    stop_loss: float | None,
    target_price: float | None,
    trade_status: str,
    direction: str,
    notes: str | None
):
    """Update an existing position in the DB by ID."""
    with sql_connect() as con:
        cur = con.cursor()
        cur.execute("""
            UPDATE positions
            SET position_size=?,
                entry_price=?,
                stop_loss=?,
                target_price=?,
                trade_status=?,
                direction=?,
                notes=?
            WHERE id=?
        """, (position_size, entry_price, stop_loss, target_price, trade_status, direction, notes, row_id))
        con.commit()




def load_portfolio_settings() -> dict:
    with sql_connect() as con:
        cur = con.cursor()
        row = cur.execute("SELECT * FROM portfolio_settings WHERE id=1").fetchone()
        if not row:
            cur.execute("""
                INSERT INTO portfolio_settings 
                (id, monday_balance, high_watermark, current_balance, max_dd_tolerance_pct, weekly_net_profit, recovery_factor_pct, recovery_requirement_pct)
                VALUES (1, 231640.00, 347558.08, 243479.92, 10.0, 11839.92, 11.38, 42.75)
            """)
            con.commit()
            row = cur.execute("SELECT * FROM portfolio_settings WHERE id=1").fetchone()
    keys = ["id","monday_balance","high_watermark","current_balance","max_dd_tolerance_pct","weekly_net_profit","recovery_factor_pct","recovery_requirement_pct"]
    return dict(zip(keys,row))

def save_portfolio_settings(d: dict):
    with sql_connect() as con:
        cur = con.cursor()
        cur.execute("""
        UPDATE portfolio_settings
        SET monday_balance=?, high_watermark=?, current_balance=?, max_dd_tolerance_pct=?, 
            weekly_net_profit=?, recovery_factor_pct=?, recovery_requirement_pct=?
        WHERE id=1
        """, (
            d["monday_balance"], d["high_watermark"], d["current_balance"], d["max_dd_tolerance_pct"],
            d["weekly_net_profit"], d["recovery_factor_pct"], d["recovery_requirement_pct"]
        ))
        con.commit()

def load_growth_plan() -> dict:
    with sql_connect() as con:
        cur = con.cursor()
        row = cur.execute("SELECT * FROM growth_plan WHERE id=1").fetchone()
        if not row:
            cur.execute("""
                INSERT INTO growth_plan
                (id, max_monthly_loss_pct, max_weekly_loss_pct, hard_stop_trade_pct, trades_per_week, max_trades_per_week, avg_rr, win_rate_pct, loss_rate_pct)
                VALUES (1, 7.0, 3.0, 1.0, 3.0, 5.0, 2.5, 60.0, 40.0)
            """)
            con.commit()
            row = cur.execute("SELECT * FROM growth_plan WHERE id=1").fetchone()
    keys = ["id","max_monthly_loss_pct","max_weekly_loss_pct","hard_stop_trade_pct","trades_per_week","max_trades_per_week","avg_rr","win_rate_pct","loss_rate_pct"]
    return dict(zip(keys,row))

def save_growth_plan(d: dict):
    with sql_connect() as con:
        cur = con.cursor()
        cur.execute("""
        UPDATE growth_plan
        SET max_monthly_loss_pct=?, max_weekly_loss_pct=?, hard_stop_trade_pct=?, trades_per_week=?, 
            max_trades_per_week=?, avg_rr=?, win_rate_pct=?, loss_rate_pct=?
        WHERE id=1
        """, (
            d["max_monthly_loss_pct"], d["max_weekly_loss_pct"], d["hard_stop_trade_pct"], d["trades_per_week"],
            d["max_trades_per_week"], d["avg_rr"], d["win_rate_pct"], d["loss_rate_pct"]
        ))
        con.commit()

# ---------------------------
# Helpers / Formatters
# ---------------------------
def format_currency(val):
    try:
        if isinstance(val, str):
            val = float(val.replace('$','').replace(',',''))
        return f"${val:,.2f}"
    except Exception:
        return val

def format_pct(val):
    try:
        return f"{float(val):.2f}%"
    except Exception:
        return val

def safe_to_float(x):
    try:
        if x is None or x == "":
            return None
        if isinstance(x, str):
            x = x.replace("$","").replace(",","")
        return float(x)
    except:
        return None

def safe_to_float_pct(x):
    try:
        if x is None or x == "":
            return None
        if isinstance(x, str):
            x = x.replace("%","").replace(",","")
        return float(x)
    except:
        return None

@st.cache_data(ttl=300)
def fetch_enhanced_data(ticker: str):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1y")
        info = stock.info
        if hist.empty:
            return None
        current_price = hist["Close"].iloc[-1]
        returns = hist["Close"].pct_change().dropna()
        volatility = returns.tail(30).std() * np.sqrt(252) * 100  # %
        week_52_high = hist["High"].max()
        week_52_low = hist["Low"].min()
        return {
            'price': float(current_price),
            'beta': info.get('beta', np.nan),
            'name': info.get('longName', ticker),
            'sector': info.get('sector', 'N/A'),
            'industry': info.get('industry', 'N/A'),
            'volatility': float(volatility) if pd.notna(volatility) else np.nan,
            'week_52_high': float(week_52_high),
            'week_52_low': float(week_52_low),
            'market_cap': info.get('marketCap', np.nan),
            'pe_ratio': info.get('trailingPE', np.nan),
            'dividend_yield': (info.get('dividendYield', 0) or 0) * 100
        }
    except Exception as e:
        st.error(f"Error fetching data for {ticker}: {str(e)}")
        return None

def calculate_var(position_size, entry_price, volatility_pct, confidence=0.05, holding_period=1):
    if volatility_pct is None or np.isnan(volatility_pct) or volatility_pct == 0:
        return -(position_size * entry_price * 0.02)  # fallback 2%
    daily_vol = (volatility_pct / 100.0) / np.sqrt(252)
    z = 1.645 if confidence == 0.05 else 2.33
    var = position_size * entry_price * z * daily_vol * np.sqrt(holding_period)
    return -float(var)

def calculate_portfolio_metrics(positions_df: pd.DataFrame):
    if positions_df.empty:
        return {
            'total_invested':0,'total_pnl':0,'total_var':0,
            'portfolio_return':0,'var_as_pct':0,
            'win_rate':0,'total_positions':0,'profitable_positions':0
        }
    def parse_currency(s): return pd.to_numeric(s.astype(str).str.replace(r'[\$,]','',regex=True), errors='coerce')
    pnl_values = parse_currency(positions_df['Unrealized PnL'])
    var_values = parse_currency(positions_df['VaR'])
    invested_values = parse_currency(positions_df['Invested Amount'])
    total_invested = invested_values.sum(skipna=True)
    total_pnl = pnl_values.sum(skipna=True)
    total_var = var_values.sum(skipna=True)
    portfolio_return = (total_pnl/total_invested*100) if total_invested>0 else 0
    var_as_pct = (abs(total_var)/total_invested*100) if total_invested>0 else 0
    profitable_positions = (pnl_values > 0).sum()
    total_positions = pnl_values.notna().sum()
    win_rate = (profitable_positions/total_positions*100) if total_positions>0 else 0
    return {
        'total_invested': float(total_invested),
        'total_pnl': float(total_pnl),
        'total_var': float(total_var),
        'portfolio_return': float(portfolio_return),
        'var_as_pct': float(var_as_pct),
        'win_rate': float(win_rate),
        'total_positions': int(total_positions),
        'profitable_positions': int(profitable_positions)
    }

# ---------------------------
# Stress Testing (Your exact table)
# ---------------------------
STRESS_TABLE = [
    ("Daily Noise", +0.008), ("Daily Noise", -0.008),
    ("Daily Noise", +0.016), ("Daily Noise", -0.016),
    ("Risk Off Shock", +0.020), ("Risk Off Shock", -0.020),
    ("Risk Off Shock", +0.029), ("Risk Off Shock", -0.029),
    ("High Vol Shock", +0.035), ("High Vol Shock", -0.035),
    ("High Vol Shock", +0.042), ("High Vol Shock", -0.042),
    ("Black Swan", +0.045), ("Black Swan", -0.045),
    ("Black Swan", +0.050), ("Black Swan", -0.050),
]

def run_stress_test(positions_df: pd.DataFrame):
    if positions_df.empty: return pd.DataFrame()
    out = []
    for _, pos in positions_df.iterrows():
        cp = safe_to_float(pos.get("Current Price"))
        ep = safe_to_float(pos.get("Entry Price"))
        size = safe_to_float(pos.get("Position Size"))
        direction = pos.get("Direction","Long")
        if any(v is None or np.isnan(v) for v in [cp,ep,size]): 
            continue
        base_pnl = safe_to_float(pos.get("Unrealized PnL"))
        for label, shock in STRESS_TABLE:
            shocked_price = cp * (1 + shock)
            if direction == "Long":
                stressed = (shocked_price - ep) * size
            else:
                stressed = (ep - shocked_price) * size
            out.append({
                "Position ID": int(pos["id"]) if "id" in pos else None,
                "Symbol": pos["Underlying Security"] if "Underlying Security" in pos else pos.get("symbol",""),
                "Scenario": f"{label} ({'+' if shock>0 else ''}{shock*100:.2f}%)",
                "Current PnL": format_currency(base_pnl),
                "Stressed PnL": format_currency(stressed),
                "Delta PnL": format_currency(stressed - (base_pnl or 0)),
                "Sector": pos.get("Sector","")
            })
    return pd.DataFrame(out)

# ---------------------------
# Session State Boot
# ---------------------------
init_db()
if "positions" not in st.session_state:
    # load from DB, format back to UI schema
    db_pos = load_positions_from_db()
    if not db_pos.empty:
        ui_df = pd.DataFrame({
            "id": db_pos["id"],
            "Open Date": db_pos["open_date"],
            "Closed Date": db_pos["closed_date"],
            "Model": db_pos["model"],
            "Trade Status": db_pos["trade_status"],
            "Underlying Security": db_pos["symbol"],
            "Security Name": db_pos["name"],
            "Sector": db_pos["sector"],
            "Industry": db_pos["industry"],
            "Direction": db_pos["direction"],
            "Position Size": db_pos["position_size"],
            "Entry Price": db_pos["entry_price"],
            "Current Price": db_pos["current_price"],
            "Stop Loss": db_pos["stop_loss"],
            "Target Price": db_pos["target_price"],
            "Invested Amount": db_pos["invested_amount"].apply(format_currency),
            "Unrealized PnL": db_pos["unrealized_pnl"].apply(format_currency),
            "PnL %": db_pos["pnl_pct"].apply(lambda x: format_pct(x) if x is not None else ""),
            "Beta": db_pos["beta"],
            "Volatility (%)": db_pos["volatility"].apply(lambda x: format_pct(x) if x is not None else ""),
            "VaR": db_pos["var"].apply(format_currency),
            "52W High": db_pos["high_52"].apply(format_currency),
            "52W Low": db_pos["low_52"].apply(format_currency),
            "Distance from 52W High (%)": db_pos["dist_52h"].apply(lambda x: format_pct(x) if x is not None else ""),
            "Distance from 52W Low (%)": db_pos["dist_52l"].apply(lambda x: format_pct(x) if x is not None else ""),
            "Market Cap": db_pos["market_cap"],
            "P/E Ratio": db_pos["pe_ratio"],
            "Dividend Yield (%)": db_pos["dividend_yield"].apply(lambda x: format_pct(x) if x is not None else ""),
            "Risk Level": db_pos["risk_level"],
            "Notes": db_pos["notes"],
            "Index": db_pos["index_benchmark"],
        })
        st.session_state.positions = ui_df
    else:
        st.session_state.positions = pd.DataFrame()

if "alerts" not in st.session_state:
    st.session_state.alerts = []

PORTFOLIO = load_portfolio_settings()
GROWTH = load_growth_plan()

# ---------------------------
# Header
# ---------------------------
st.markdown("""
<div class="main-header">
    <h1>📊 Equities Risk Manager Pro</h1>
    <p>Advanced Portfolio Risk Management & Analytics Platform</p>
</div>
""", unsafe_allow_html=True)

# ---------------------------
# Sidebar (KPI + Filters + VaR Budget)
# ---------------------------
with st.sidebar:
    st.header("🚀 Quick Actions")

    # Portfolio VaR budget from growth plan + portfolio settings
    monday_balance = float(PORTFOLIO["monday_balance"] or 0)
    weekly_budget = monday_balance * (float(GROWTH["max_weekly_loss_pct"] or 0)/100.0)
    # current total VaR (absolute)
    if not st.session_state.positions.empty:
        total_var = pd.to_numeric(st.session_state.positions["VaR"].astype(str).str.replace(r'[\$,]','',regex=True), errors='coerce').sum()
    else:
        total_var = 0.0
    utilized = (abs(total_var)/weekly_budget*100) if weekly_budget>0 else 0
    available = weekly_budget - abs(total_var)

    st.subheader("📉 VaR Budget")
    c1, c2 = st.columns(2)
    with c1: st.metric("Weekly Budget", format_currency(weekly_budget))
    with c2: st.metric("Current VaR", format_currency(total_var), f"{utilized:.1f}% used")
    st.metric("Available", format_currency(available))

    # Portfolio summary
    if not st.session_state.positions.empty:
        metrics = calculate_portfolio_metrics(st.session_state.positions)
        st.markdown("### Portfolio Overview")
        c1,c2 = st.columns(2)
        with c1:
            st.metric("Total P&L", format_currency(metrics['total_pnl']), f"{metrics['portfolio_return']:.1f}%")
        with c2:
            st.metric("Total VaR", format_currency(metrics['total_var']), f"{metrics['var_as_pct']:.1f}% of capital")
        st.metric("Win Rate", f"{metrics['win_rate']:.1f}%", f"{int(metrics['profitable_positions'])}/{int(metrics['total_positions'])}")
    else:
        st.info("No positions yet.")

    # Filters
    if not st.session_state.positions.empty:
        st.header("🔍 Quick Filters")
        sectors = st.session_state.positions['Sector'].dropna().unique().tolist()
        directions = st.session_state.positions['Direction'].dropna().unique().tolist()
        selected_sectors = st.multiselect("Filter by Sector", sectors, default=sectors)
        selected_directions = st.multiselect("Filter by Direction", directions, default=directions)

# ---------------------------
# Tabs
# ---------------------------
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📝 Position Management",
    "📊 Portfolio Analytics",
    "🔥 Stress Testing",
    "⚡ Real-time Monitoring",
    "📄 Reports",
    "⚙️ Portfolio Settings"
])

# ---------------------------
# Tab 1: Position Management
# ---------------------------
with tab1:
    col1, col2 = st.columns([2,1])
    with col1:
        st.subheader("Add New Position")
        with st.form("new_position", clear_on_submit=True):
            ca, cb, cc = st.columns(3)
            with ca:
                open_date = st.date_input("Open Date", value=datetime.now().date())
                closed_date = st.date_input("Closed Date", value=None)
                model = st.selectbox("Trading Model", ["Axiom","Pivot","Vector"])
            with cb:
                underlying = st.text_input("Ticker Symbol", placeholder="e.g., AAPL").upper()
                direction = st.selectbox("Direction", ["Long","Short"])
                trade_status = st.selectbox("Status", ["Open","Closed"])
            with cc:
                position_size = st.number_input("Shares/Contracts", min_value=0.0, step=1.0)
                entry_price = st.number_input("Entry Price ($)", min_value=0.0, step=0.01)
                stop_loss = st.number_input("Stop Loss ($)", min_value=0.0, step=0.01, value=0.0)

            with st.expander("🔧 Advanced Options"):
                a1, a2 = st.columns(2)
                with a1:
                    index_choice = st.selectbox("Benchmark Index", ["^GSPC","^IXIC","^RUT","^DJI"],
                                                format_func=lambda x: {"^GSPC":"S&P 500","^IXIC":"NASDAQ","^RUT":"Russell 2000","^DJI":"Dow Jones"}[x])
                    target_price = st.number_input("Target Price ($)", min_value=0.0, step=0.01, value=0.0)
                with a2:
                    risk_level = st.selectbox("Risk Level", ["Low","Medium","High"])
                    notes = st.text_area("Notes", placeholder="Additional notes...")

            submitted = st.form_submit_button("➕ Add Position", type="primary")

            if submitted and underlying and position_size > 0 and entry_price > 0:
                with st.spinner(f"Fetching data for {underlying}..."):
                    data = fetch_enhanced_data(underlying)
                if data:
                    invested = position_size * entry_price
                    cp = data['price']
                    if direction == "Long":
                        pnl = (cp - entry_price) * position_size
                    else:
                        pnl = (entry_price - cp) * position_size
                    var_val = calculate_var(position_size, entry_price, data['volatility'])
                    pnl_pct = (pnl / invested * 100) if invested > 0 else 0
                    dist_52h = ((cp - data['week_52_high'])/data['week_52_high']*100) if data['week_52_high'] else 0
                    dist_52l = ((cp - data['week_52_low'])/data['week_52_low']*100) if data['week_52_low'] else 0

                    new_row = {
                        "Open Date": open_date.isoformat() if isinstance(open_date, date) else open_date,
                        "Closed Date": closed_date.isoformat() if isinstance(closed_date, date) else None,
                        "Model": model,
                        "Trade Status": trade_status,
                        "Underlying Security": underlying,
                        "Security Name": data['name'],
                        "Sector": data['sector'],
                        "Industry": data['industry'],
                        "Direction": direction,
                        "Position Size": float(position_size),
                        "Entry Price": float(entry_price),
                        "Current Price": float(cp),
                        "Stop Loss": float(stop_loss) if stop_loss>0 else None,
                        "Target Price": float(target_price) if target_price>0 else None,
                        "Invested Amount": format_currency(invested),
                        "Unrealized PnL": format_currency(pnl),
                        "PnL %": format_pct(pnl_pct),
                        "Beta": data['beta'],
                        "Volatility (%)": format_pct(data['volatility']),
                        "VaR": format_currency(var_val),
                        "52W High": format_currency(data['week_52_high']),
                        "52W Low": format_currency(data['week_52_low']),
                        "Distance from 52W High (%)": format_pct(dist_52h),
                        "Distance from 52W Low (%)": format_pct(dist_52l),
                        "Market Cap": data['market_cap'],
                        "P/E Ratio": data['pe_ratio'],
                        "Dividend Yield (%)": format_pct(data['dividend_yield']),
                        "Risk Level": risk_level,
                        "Notes": notes,
                        "Index": index_choice,
                    }
                    # Persist to DB
                    insert_position(new_row)
                    # Update session
                    db_pos = load_positions_from_db()
                    st.session_state.positions = pd.DataFrame({
                        "id": db_pos["id"],
                        "Open Date": db_pos["open_date"],
                        "Closed Date": db_pos["closed_date"],
                        "Model": db_pos["model"],
                        "Trade Status": db_pos["trade_status"],
                        "Underlying Security": db_pos["symbol"],
                        "Security Name": db_pos["name"],
                        "Sector": db_pos["sector"],
                        "Industry": db_pos["industry"],
                        "Direction": db_pos["direction"],
                        "Position Size": db_pos["position_size"],
                        "Entry Price": db_pos["entry_price"],
                        "Current Price": db_pos["current_price"],
                        "Stop Loss": db_pos["stop_loss"],
                        "Target Price": db_pos["target_price"],
                        "Invested Amount": db_pos["invested_amount"].apply(format_currency),
                        "Unrealized PnL": db_pos["unrealized_pnl"].apply(format_currency),
                        "PnL %": db_pos["pnl_pct"].apply(lambda x: format_pct(x) if x is not None else ""),
                        "Beta": db_pos["beta"],
                        "Volatility (%)": db_pos["volatility"].apply(lambda x: format_pct(x) if x is not None else ""),
                        "VaR": db_pos["var"].apply(format_currency),
                        "52W High": db_pos["high_52"].apply(format_currency),
                        "52W Low": db_pos["low_52"].apply(format_currency),
                        "Distance from 52W High (%)": db_pos["dist_52h"].apply(lambda x: format_pct(x) if x is not None else ""),
                        "Distance from 52W Low (%)": db_pos["dist_52l"].apply(lambda x: format_pct(x) if x is not None else ""),
                        "Market Cap": db_pos["market_cap"],
                        "P/E Ratio": db_pos["pe_ratio"],
                        "Dividend Yield (%)": db_pos["dividend_yield"].apply(lambda x: format_pct(x) if x is not None else ""),
                        "Risk Level": db_pos["risk_level"],
                        "Notes": db_pos["notes"],
                        "Index": db_pos["index_benchmark"],
                    })
                    if var_val < -5000:
                        st.session_state.alerts.append(f"High risk position added: {underlying} (VaR: {format_currency(var_val)})")
                    st.success(f"✅ Successfully added {underlying}!")
                    st.rerun()
                else:
                    st.error("❌ Could not fetch data for this ticker. Please verify the symbol.")

    with col2:
        st.subheader("📊 Position Summary")
        if not st.session_state.positions.empty:
            open_positions = st.session_state.positions[st.session_state.positions['Trade Status']=='Open']
            st.metric("Open Positions", len(open_positions))
            if len(open_positions)>0:
                m = calculate_portfolio_metrics(open_positions)
                st.metric("Total Invested", format_currency(m['total_invested']))
                st.metric("Total P&L", format_currency(m['total_pnl']), f"{m['portfolio_return']:.1f}%")
                pnl_vals = pd.to_numeric(open_positions['Unrealized PnL'].astype(str).str.replace(r'[\$,]','',regex=True), errors='coerce')
                if pnl_vals.notna().any():
                    best_idx = pnl_vals.idxmax()
                    worst_idx = pnl_vals.idxmin()
                    st.markdown("**🏆 Best Performer**")
                    st.write(f"{open_positions.loc[best_idx,'Underlying Security']}: {open_positions.loc[best_idx,'Unrealized PnL']}")
                    st.markdown("**📉 Worst Performer**")
                    st.write(f"{open_positions.loc[worst_idx,'Underlying Security']}: {open_positions.loc[worst_idx,'Unrealized PnL']}")
        else:
            st.info("No positions yet. Add your first position to get started!")

# ---------------------------
# Tab 2: Portfolio Analytics
# ---------------------------
with tab2:
    if st.session_state.positions.empty:
        st.info("Add some positions to see portfolio analytics.")
    else:
        filtered = st.session_state.positions.copy()
        if 'selected_sectors' in locals() and selected_sectors:
            filtered = filtered[filtered['Sector'].isin(selected_sectors)]
        if 'selected_directions' in locals() and selected_directions:
            filtered = filtered[filtered['Direction'].isin(selected_directions)]

        # KPIs
        c1,c2,c3,c4 = st.columns(4)
        metrics = calculate_portfolio_metrics(filtered)
        with c1:
            st.markdown(f"<div class='metric-container kpi'><h3>{format_currency(metrics['total_invested'])}</h3><p>Total Invested</p></div>", unsafe_allow_html=True)
        with c2:
            pnl_color = "success-alert" if metrics['total_pnl'] >= 0 else "risk-alert"
            st.markdown(f"<div class='{pnl_color} kpi'><h3>{format_currency(metrics['total_pnl'])}</h3><p>Total P&L ({metrics['portfolio_return']:+.1f}%)</p></div>", unsafe_allow_html=True)
        with c3:
            st.markdown(f"<div class='metric-container kpi'><h3>{format_currency(metrics['total_var'])}</h3><p>Total VaR</p></div>", unsafe_allow_html=True)
        with c4:
            st.markdown(f"<div class='metric-container kpi'><h3>{metrics['win_rate']:.1f}%</h3><p>Win Rate</p></div>", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            pnl_rows = []
            for _, r in filtered.iterrows():
                pnl_val = pd.to_numeric(str(r['Unrealized PnL']).replace('$','').replace(',',''), errors='coerce')
                if pd.notna(pnl_val):
                    pnl_rows.append({'Position': r['Underlying Security'], 'PnL': pnl_val})
            if pnl_rows:
                pnl_df = pd.DataFrame(pnl_rows).sort_values('PnL')
                fig = px.bar(pnl_df, x='PnL', y='Position', orientation='h',
                             title='P&L by Position', color='PnL',
                             color_continuous_scale=['red','yellow','green'])
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True, key="pnl_bar")

        with c2:
            sector_risk = []
            for sector in filtered['Sector'].dropna().unique():
                sub = filtered[filtered['Sector']==sector]
                val = 0
                for _, r in sub.iterrows():
                    v = pd.to_numeric(str(r['VaR']).replace('$','').replace(',',''), errors='coerce')
                    if pd.notna(v): val += abs(v)
                sector_risk.append({'Sector': sector, 'VaR': val})
            if sector_risk:
                risk_df = pd.DataFrame(sector_risk)
                fig = px.pie(risk_df, names='Sector', values='VaR',
                             title='Risk Concentration by Sector',
                             color_discrete_sequence=px.colors.qualitative.Set3)
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True, key="sector_pie")

        # Grid
        st.subheader("📋 Detailed Positions")
        gb = GridOptionsBuilder.from_dataframe(filtered)
        gb.configure_pagination(paginationPageSize=20)
        gb.configure_side_bar()
        gb.configure_selection('multiple', use_checkbox=True)
        gb.configure_column("id", headerName="ID", width=80)
        gb.configure_default_column(resizable=True, sortable=True, filter=True)

        # If you still want numeric sorting on money/percent fields
        if "Unrealized PnL" in filtered.columns:
            gb.configure_column("Unrealized PnL", type=["numericColumn"], valueFormatter="value")

        if "VaR" in filtered.columns:
            gb.configure_column("VaR", type=["numericColumn"], valueFormatter="value")

        if "PnL %" in filtered.columns:
            gb.configure_column("PnL %", type=["numericColumn"], valueFormatter="value + '%'")


        grid = AgGrid(
            filtered,
            gridOptions=gb.build(),
            update_mode=GridUpdateMode.SELECTION_CHANGED,
            theme="streamlit",
            height=520,
            fit_columns_on_grid_load=False,
            allow_unsafe_jscode=True
        )
        selected = grid.get("selected_rows", [])

        if isinstance(selected, list):  # AgGrid usually returns list of dicts
            selected_ids = [int(r["id"]) for r in selected] if selected else []
        elif isinstance(selected, pd.DataFrame):  # Just in case it's a DataFrame
            selected_ids = selected["id"].astype(int).tolist() if not selected.empty else []
        else:
            selected_ids = []


if selected_ids:
    st.subheader(f"🔧 Bulk Actions ({len(selected_ids)} selected)")
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        if st.button("📊 Analyze Selected"):
            sdf = pd.DataFrame(selected)  # from grid_response
            sm = calculate_portfolio_metrics(sdf)
            st.write("**Selected Metrics:**")
            st.write(f"Total P&L: {format_currency(sm['total_pnl'])}")
            st.write(f"Total VaR: {format_currency(sm['total_var'])}")
            st.write(f"Win Rate: {sm['win_rate']:.1f}%")

    with c2:
        if st.button("❌ Close Selected"):
            close_positions_by_ids(selected_ids)
            st.success(f"Closed {len(selected_ids)} positions.")
            st.rerun()

    with c3:
        if st.button("🗑️ Delete Selected"):
            delete_positions_by_ids(selected_ids)
            st.success(f"Deleted {len(selected_ids)} positions.")
            st.rerun()

    with c4:
        if len(selected_ids) == 1:  # only allow editing one at a time
            pos_id = int(selected_ids[0])
            pos_row = st.session_state.positions[
                st.session_state.positions["id"] == pos_id
            ].iloc[0]

            with st.form("edit_position"):
                st.write(f"✏️ Editing Position ID: {pos_id}")

                col1e, col2e = st.columns(2)
                with col1e:
                    position_size = st.number_input(
                        "Position Size", value=float(pos_row["Position Size"])
                    )
                    entry_price = st.number_input(
                        "Entry Price", value=float(pos_row["Entry Price"])
                    )
                    stop_loss = st.number_input(
                        "Stop Loss", value=float(pos_row["Stop Loss"]) if pos_row["Stop Loss"] else 0.0
                    )
                with col2e:
                    target_price = st.number_input(
                        "Target Price", value=float(pos_row["Target Price"]) if pos_row["Target Price"] else 0.0
                    )
                    trade_status = st.selectbox(
                        "Trade Status", ["Open", "Closed"],
                        index=0 if pos_row["Trade Status"] == "Open" else 1
                    )
                    direction = st.selectbox(
                        "Direction", ["Long", "Short"],
                        index=0 if pos_row["Direction"] == "Long" else 1
                    )

                notes = st.text_area("Notes", value=str(pos_row["Notes"] or ""))

                submitted = st.form_submit_button("💾 Save Changes")
                if submitted:
                    update_position_by_id(
                        pos_id,
                        position_size,
                        entry_price,
                        stop_loss if stop_loss > 0 else None,
                        target_price if target_price > 0 else None,
                        trade_status,
                        direction,
                        notes
                    )
                    st.success("✅ Position updated successfully!")
                    st.rerun()



# ---------------------------
# Tab 3: Stress Testing
# ---------------------------
with tab3:
    st.subheader("🔥 Portfolio Stress Testing")
    if st.session_state.positions.empty:
        st.info("Add positions to run stress tests.")
    else:
        if st.button("🧪 Run Stress Tests", type="primary"):
            with st.spinner("Running stress tests..."):
                st.session_state.stress_results = run_stress_test(st.session_state.positions)

        if 'stress_results' in st.session_state and not st.session_state.stress_results.empty:
            st.markdown("**Stress Test Results:**")
            # Aggregate by scenario
            agg = []
            for sc in st.session_state.stress_results['Scenario'].unique():
                sub = st.session_state.stress_results[st.session_state.stress_results['Scenario']==sc]
                total = 0.0
                for v in sub['Stressed PnL']:
                    try: total += float(str(v).replace('$','').replace(',',''))
                    except: pass
                agg.append({"Scenario": sc, "Total Impact": total})
            if agg:
                s = pd.DataFrame(agg).sort_values("Total Impact")
                fig = px.bar(s, x="Scenario", y="Total Impact",
                             title="Portfolio Stress Test Results",
                             color="Total Impact",
                             color_continuous_scale=['darkred','red','orange','yellow','lightgreen'])
                fig.update_layout(xaxis_tickangle=-45, height=420)
                st.plotly_chart(fig, use_container_width=True, key="stress_bar")
            st.dataframe(st.session_state.stress_results, use_container_width=True)

# ---------------------------
# Tab 4: Real-time Monitoring
# ---------------------------
with tab4:
    st.subheader("⚡ Real-time Portfolio Monitoring")
    if st.session_state.positions.empty:
        st.info("Add positions to enable real-time monitoring.")
    else:
        auto_refresh = st.checkbox("🔄 Auto-refresh (30s)", value=False)
        if auto_refresh:
            import time
            time.sleep(30)
            st.rerun()

        c1,c2 = st.columns([2,1])
        with c1:
            st.markdown("**📈 Position Performance Heatmap**")
            heat = []
            for _, p in st.session_state.positions.iterrows():
                if p.get("Trade Status")=="Open":
                    pct = safe_to_float_pct(p.get("PnL %"))
                    if pct is not None:
                        heat.append({"Symbol": p["Underlying Security"], "Sector": p.get("Sector",""), "PnL %": pct})
            if heat:
                hdf = pd.DataFrame(heat)
                fig = px.treemap(hdf, path=['Sector','Symbol'], values=[1]*len(hdf),
                                 color='PnL %', color_continuous_scale='RdYlGn',
                                 title='Portfolio Heatmap (by P&L %)', color_continuous_midpoint=0)
                fig.update_layout(height=500)
                st.plotly_chart(fig, use_container_width=True, key="heatmap")

        with c2:
            st.markdown("**🚨 Active Alerts**")
            alerts = []
            for _, p in st.session_state.positions.iterrows():
                if p.get("Trade Status")=="Open":
                    cp = safe_to_float(p.get("Current Price"))
                    sl = safe_to_float(p.get("Stop Loss"))
                    if sl is not None and cp is not None:
                        if (p.get("Direction")=="Long" and cp<=sl) or (p.get("Direction")=="Short" and cp>=sl):
                            alerts.append(f"🛑 {p['Underlying Security']}: Stop loss triggered!")
                    vol = safe_to_float_pct(p.get("Volatility (%)"))
                    if vol is not None and vol>50: alerts.append(f"📈 {p['Underlying Security']}: High volatility ({vol:.1f}%)")
                    pnl = safe_to_float(p.get("Unrealized PnL"))
                    if pnl is not None and pnl<-5000: alerts.append(f"📉 {p['Underlying Security']}: Large loss ({format_currency(pnl)})")
            if alerts:
                for a in alerts: st.warning(a)
            else:
                st.success("✅ No active alerts")

        st.markdown("---")
        st.subheader("📊 Market Sentiment Dashboard")
        cc1, cc2, cc3 = st.columns(3)
        with cc1:
            vols = []
            for _, p in st.session_state.positions.iterrows():
                v = safe_to_float_pct(p.get("Volatility (%)"))
                if v is not None: vols.append(v)
            if vols:
                avg_vol = float(np.mean(vols))
                st.metric("Portfolio Volatility", f"{avg_vol:.1f}%")
                st.write(f"Market Fear Index: {'🟢' if avg_vol<20 else '🟡' if avg_vol<40 else '🔴'}")
        with cc2:
            betas, weights = [], []
            for _, p in st.session_state.positions.iterrows():
                b = safe_to_float(p.get("Beta"))
                inv = safe_to_float(p.get("Invested Amount"))
                if b is not None and inv is not None:
                    betas.append(b); weights.append(inv)
            if betas and weights:
                wbeta = float(np.average(betas, weights=weights))
                st.metric("Portfolio Beta", f"{wbeta:.2f}")
                st.write("Style: " + ("Defensive" if wbeta<0.8 else "Market-like" if wbeta<1.2 else "Aggressive"))
        with cc3:
            if not st.session_state.positions.empty:
                counts = st.session_state.positions['Sector'].value_counts()
                if not counts.empty:
                    max_conc = counts.iloc[0]/len(st.session_state.positions)*100
                    st.metric("Max Sector Concentration", f"{max_conc:.1f}%")
                    st.write(f"Diversification: {'🟢' if max_conc<30 else '🟡' if max_conc<50 else '🔴'}")

# ---------------------------
# Tab 5: Reports
# ---------------------------
def export_pdf(sections: dict, filename: str, commentary: str = "") -> bytes:
    buff = io.BytesIO()
    doc = SimpleDocTemplate(buff, pagesize=landscape(letter))
    styles = getSampleStyleSheet()
    elems = [Paragraph("Equities Risk Manager Report", styles["Title"]),
             Paragraph(datetime.now().strftime("%Y-%m-%d %H:%M"), styles["Normal"]), Spacer(1,12)]
    if commentary:
        elems += [Paragraph("Commentary", styles["Heading2"]),
                  Paragraph(commentary, styles["BodyText"]), Spacer(1,12)]
    for name, df in sections.items():
        elems.append(Paragraph(str(name), styles["Heading2"]))
        if isinstance(df, pd.DataFrame) and not df.empty:
            clean = df.copy()
            for c in clean.columns:
                clean[c] = clean[c].astype(str)
            data = [clean.columns.tolist()] + clean.values.tolist()
            tbl = Table(data, repeatRows=1)
            tbl.setStyle(TableStyle([
                ('BACKGROUND',(0,0),(-1,0), colors.HexColor("#1f77b4")),
                ('TEXTCOLOR',(0,0),(-1,0), colors.white),
                ('ALIGN',(0,0),(-1,-1),'CENTER'),
                ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),
                ('BOTTOMPADDING',(0,0),(-1,0),8),
                ('GRID',(0,0),(-1,-1),0.25, colors.gray),
            ]))
            elems += [tbl, Spacer(1,16)]
        else:
            elems += [Paragraph("No data", styles["Italic"]), Spacer(1,12)]
    doc.build(elems)
    buff.seek(0)
    return buff.read()

with tab5:
    st.subheader("📄 Advanced Reporting")
    if st.session_state.positions.empty:
        st.info("Add positions to generate reports.")
    else:
        c1,c2 = st.columns([2,1])
        with c1:
            report_type = st.selectbox("Report Type", ["Executive Summary","Detailed Risk Analysis","Performance Report","Regulatory Report"])
            include_stress = st.checkbox("Include Stress Test Results", value=False)
            ca, cb = st.columns(2)
            with ca:
                start_date = st.date_input("Report Start Date", value=datetime.now().date()-timedelta(days=30))
            with cb:
                end_date = st.date_input("Report End Date", value=datetime.now().date())
            commentary = st.text_area("Market Commentary", placeholder="Add your market observations...", height=100)
        with c2:
            metrics = calculate_portfolio_metrics(st.session_state.positions)
            st.metric("Positions", len(st.session_state.positions))
            st.metric("Total P&L", format_currency(metrics['total_pnl']))
            st.metric("Win Rate", f"{metrics['win_rate']:.1f}%")
            if st.button("📄 Generate PDF Report", type="primary"):
                sections = {"Positions": st.session_state.positions}
                if include_stress and 'stress_results' in st.session_state:
                    sections["Stress Tests"] = st.session_state.stress_results
                pdf_bytes = export_pdf(sections, "risk_report.pdf", commentary)
                st.success("✅ PDF report generated!")
                st.download_button("📥 Download PDF Report", data=pdf_bytes,
                                   file_name=f"Risk_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                                   mime="application/pdf")
            if st.button("📊 Export to Excel"):
                excel_buffer = io.BytesIO()
                with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                    st.session_state.positions.to_excel(writer, sheet_name='Positions', index=False)
                    m = calculate_portfolio_metrics(st.session_state.positions)
                    summary = pd.DataFrame([
                        ['Total Invested', format_currency(m['total_invested'])],
                        ['Total P&L', format_currency(m['total_pnl'])],
                        ['Portfolio Return %', f"{m['portfolio_return']:.2f}%"],
                        ['Total VaR', format_currency(m['total_var'])],
                        ['Win Rate %', f"{m['win_rate']:.2f}%"],
                        ['Total Positions', int(m['total_positions'])],
                        ['Profitable Positions', int(m['profitable_positions'])],
                    ], columns=['Metric','Value'])
                    summary.to_excel(writer, sheet_name='Summary', index=False)
                    if 'stress_results' in st.session_state:
                        st.session_state.stress_results.to_excel(writer, sheet_name='Stress Tests', index=False)
                excel_buffer.seek(0)
                st.success("✅ Excel report generated!")
                st.download_button("📥 Download Excel Report",
                                   data=excel_buffer.getvalue(),
                                   file_name=f"Risk_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        st.markdown("---")
        st.subheader("📋 Report Preview")
        if report_type == "Executive Summary":
            st.markdown(f"""
            ## Executive Summary - Portfolio Risk Report  
            **Report Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
            - **Total Positions:** {len(st.session_state.positions)}
            - **Total Investment:** {format_currency(metrics['total_invested'])}
            - **Unrealized P&L:** {format_currency(metrics['total_pnl'])} ({metrics['portfolio_return']:+.2f}%)
            - **Value at Risk:** {format_currency(metrics['total_var'])}
            - **Win Rate:** {metrics['win_rate']:.1f}%
            """)

# ---------------------------
# Tab 6: Portfolio Settings (Portfolio Data + Growth Plan)
# ---------------------------
with tab6:
    st.subheader("⚙️ Portfolio Settings")
    left, right = st.columns(2)

    with left:
        st.markdown("### 📁 Portfolio Data")
        monday_balance = st.number_input("Portfolio Size (Monday)", value=float(PORTFOLIO["monday_balance"] or 0.0), step=100.0)
        high_watermark = st.number_input("High Watermark", value=float(PORTFOLIO["high_watermark"] or 0.0), step=100.0)
        current_balance = st.number_input("Current Balance", value=float(PORTFOLIO["current_balance"] or 0.0), step=100.0)
        max_dd_tolerance = st.number_input("Max Drawdown Tolerance (%)", value=float(PORTFOLIO["max_dd_tolerance_pct"] or 0.0), step=0.1)
        weekly_net_profit = st.number_input("Weekly Net Profit", value=float(PORTFOLIO["weekly_net_profit"] or 0.0), step=100.0)
        recovery_factor = st.number_input("Recovery Factor (%)", value=float(PORTFOLIO["recovery_factor_pct"] or 0.0), step=0.1)
        recovery_requirement = st.number_input("Recovery Requirement (%)", value=float(PORTFOLIO["recovery_requirement_pct"] or 0.0), step=0.1)

        # Derived current drawdown
        current_dd = ((current_balance - high_watermark) / high_watermark * 100) if high_watermark else 0.0

        st.markdown("<div class='kpi-line'>", unsafe_allow_html=True)
        st.markdown(f"<div class='metric-container kpi'><h3>{format_pct(current_dd)}</h3><p>Current Drawdown</p></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='metric-container kpi'><h3>{format_currency(weekly_net_profit)}</h3><p>Weekly Net Profit</p></div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        if st.button("💾 Save Portfolio Settings"):
            PORTFOLIO.update({
                "monday_balance": monday_balance,
                "high_watermark": high_watermark,
                "current_balance": current_balance,
                "max_dd_tolerance_pct": max_dd_tolerance,
                "weekly_net_profit": weekly_net_profit,
                "recovery_factor_pct": recovery_factor,
                "recovery_requirement_pct": recovery_requirement
            })
            save_portfolio_settings(PORTFOLIO)
            st.success("Saved portfolio settings.")

    with right:
        st.markdown("### 🚀 Growth Plan (Equities/FX Parameters)")
        max_monthly_loss_pct = st.number_input("Max Monthly Loss (%)", value=float(GROWTH["max_monthly_loss_pct"] or 0.0), step=0.1)
        max_weekly_loss_pct = st.number_input("Max Weekly Loss (%)", value=float(GROWTH["max_weekly_loss_pct"] or 0.0), step=0.1)
        hard_stop_trade_pct = st.number_input("Hard Stop on Single Trade Max (%)", value=float(GROWTH["hard_stop_trade_pct"] or 0.0), step=0.1)
        trades_per_week = st.number_input("No. of Trades per Week", value=float(GROWTH["trades_per_week"] or 0.0), step=1.0)
        max_trades_per_week = st.number_input("Max No. of Trades per Week", value=float(GROWTH["max_trades_per_week"] or 0.0), step=1.0)
        avg_rr = st.number_input("Average RR per Trade", value=float(GROWTH["avg_rr"] or 0.0), step=0.1)
        win_rate_pct = st.number_input("Win Rate (%)", value=float(GROWTH["win_rate_pct"] or 0.0), step=0.1)
        loss_rate_pct = st.number_input("Loss Rate (%)", value=float(GROWTH["loss_rate_pct"] or 0.0), step=0.1)

        # Derived weekly plan numbers
        weekly_loss_amount = monday_balance * (max_weekly_loss_pct/100.0)
        # Assume min trades = trades_per_week, expected winners = win_rate * trades, losers = loss_rate * trades
        min_trades = trades_per_week
        expected_wins = int(round(min_trades * (win_rate_pct/100.0)))
        expected_losses = int(round(min_trades * (loss_rate_pct/100.0)))
        # risk per trade by hard stop (% of Monday balance)
        risk_per_trade = monday_balance * (hard_stop_trade_pct/100.0)
        expected_weekly_gain = expected_wins * (risk_per_trade * avg_rr)
        expected_weekly_loss = expected_losses * (risk_per_trade)
        net_weekly_pnl = expected_weekly_gain - expected_weekly_loss
        net_monthly_pnl = net_weekly_pnl * 4.0

        # Display
        st.markdown("<div class='kpi-line'>", unsafe_allow_html=True)
        st.markdown(f"<div class='metric-container kpi'><h3>{format_currency(weekly_loss_amount)}</h3><p>Max Weekly Loss (Budget)</p></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='metric-container kpi'><h3>{format_currency(net_weekly_pnl)}</h3><p>Net Weekly PnL</p></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='metric-container kpi'><h3>{format_currency(net_monthly_pnl)}</h3><p>Net Monthly PnL</p></div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        if st.button("💾 Save Growth Plan"):
            GROWTH.update({
                "max_monthly_loss_pct": max_monthly_loss_pct,
                "max_weekly_loss_pct": max_weekly_loss_pct,
                "hard_stop_trade_pct": hard_stop_trade_pct,
                "trades_per_week": trades_per_week,
                "max_trades_per_week": max_trades_per_week,
                "avg_rr": avg_rr,
                "win_rate_pct": win_rate_pct,
                "loss_rate_pct": loss_rate_pct
            })
            save_growth_plan(GROWTH)
            st.success("Saved growth plan.")

# ---------------------------
# Footer
# ---------------------------
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 1rem;'>
    <p>📊 Equities Risk Manager Pro v2.1 — Persistence + Growth Plan + VaR Budget</p>
</div>
""", unsafe_allow_html=True)

