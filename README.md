# MetaMacro TUI - Terminal Market Analysis Platform

A powerful Terminal User Interface (TUI) application for market analysis, sector momentum tracking, portfolio analysis, and market regime detection. This is the TUI version of the MetaMacro Streamlit dashboard, built using Python Textual framework.

## Features

### 🌍 Market Monitor
- Real-time market indices tracking (Nasdaq, S&P 500, Dow, Russell 2000)
- Composite market analysis with VIX integration
- Multi-timeframe regime analysis (Yearly, Weekly, Daily, Session)
- Interactive KPI cards with color-coded regime indicators
- Market flow analysis and comparisons

### 📊 Sub-Industry vs Sector Analysis
- Sector momentum tracking
- Sub-industry relative strength analysis
- Regime classification across multiple timeframes
- Export capabilities for research reports

### 🏢 Stock vs Sub-Industry Analysis
- Individual stock performance vs sector benchmarks
- Relative strength indicators
- Multi-timeframe regime detection
- Portfolio optimization insights

### 📈 Market Comparisons
- Custom entity comparisons
- Ratio analysis between any two market instruments
- Interactive chart displays
- Export functionality

### 📑 Research Pack
- Consolidated research reports
- Custom commentary integration
- Multi-format exports (PDF, Excel)
- Professional report generation

## Installation

### Prerequisites
- Python 3.9 or higher
- Terminal with Unicode support (recommended: iTerm2, Windows Terminal, or modern Linux terminal)

### Quick Start

1. **Clone or navigate to the project directory:**
   ```bash
   cd /path/to/metamacro-dashboard
   ```

2. **Install TUI dependencies:**
   ```bash
   pip install -r requirements_tui.txt
   ```

3. **Run the application:**
   ```bash
   python main.py
   ```

### Alternative Installation
If you prefer to install dependencies manually:

```bash
pip install textual rich plotext pandas numpy yfinance python-dateutil pytz reportlab xlsxwriter colorama
```

## Usage

### Keyboard Shortcuts

#### Navigation
- **1-5**: Switch between tabs (Market Monitor, Sub-Industry, Stock Analysis, Comparisons, Research Pack)
- **Tab**: Navigate between widgets
- **Enter**: Activate selected item
- **Arrow Keys**: Navigate within tables and lists

#### Data Operations
- **r**: Refresh data
- **Ctrl+r**: Force refresh (clear cache)
- **e**: Export current view

#### General
- **h**: Show help dialog
- **s**: Settings (to be implemented)
- **q**: Quit application

### Data Sources

The application automatically loads CSV universe files from the project directory. Supported files:
- `SPX500.csv` - S&P 500 constituents
- `NASDAQ100.csv` - Nasdaq 100 constituents  
- `DOW30.csv` - Dow Jones 30 constituents
- `Russel2k.csv` - Russell 2000 constituents

**CSV Format Requirements:**
Your universe CSV files must contain these columns:
- `Ticker`: Stock symbol
- `Sector`: Sector classification
- `SubIndustry`: Sub-industry classification
- `SectorIndex`: Corresponding sector index symbol

## Architecture

### Project Structure
```
metamacro-dashboard/
├── main.py                 # Application entry point
├── styles.css              # TUI styling
├── requirements_tui.txt     # TUI dependencies
├── views/                   # Application views
│   ├── market_monitor.py    # Market monitoring view
│   ├── subindustry_sector.py # Sub-industry analysis
│   ├── stock_subindustry.py # Stock analysis
│   ├── market_comparisons.py # Comparison tools
│   └── research_pack.py     # Research report generation
├── components/              # Reusable UI components
│   ├── data_loader.py       # Data loading and caching
│   └── status_bar.py        # Status display
├── utils/                   # Utilities
│   └── config.py            # Configuration management
└── sector_flow_model.py     # Core analysis engine (unchanged)
```

## Regime Classification

The application uses a sophisticated regime classification system:

### Yearly Regimes
- **Strong Bull**: Price above mid-range and above high
- **Weak Bull**: Price above mid-range but below high
- **Strong Bear**: Price below mid-range and below low
- **Weak Bear**: Price below mid-range but above low
- **Neutral**: Price at mid-range

### Weekly/Daily/Session Regimes
Similar classification applied to different timeframes for comprehensive market analysis.

## Troubleshooting

### Common Issues

1. **Module not found errors:**
   ```bash
   pip install -r requirements_tui.txt
   ```

2. **Data loading failures:**
   - Check internet connection
   - Verify CSV file format
   - Use force refresh (Ctrl+r)

3. **Display issues:**
   - Ensure terminal supports Unicode
   - Try resizing terminal window
   - Check terminal color support

## Running the Application

Simply run:
```bash
python main.py
```

The application will:
1. Load market data automatically
2. Scan for CSV universe files in the project directory
3. Display the Market Monitor tab by default
4. Allow navigation between different analysis views

Enjoy your terminal-based market analysis platform!
