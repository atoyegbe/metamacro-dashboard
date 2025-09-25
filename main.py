#!/usr/bin/env python3
"""
MetaMacro TUI - Terminal User Interface for Market Analysis
Main application entry point using Textual framework
"""

import asyncio
from pathlib import Path
from typing import Optional

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, TabbedContent, TabPane, Static, Button
from textual.binding import Binding
from textual.reactive import reactive

from views.market_monitor import MarketMonitorView
from views.subindustry_sector import SubIndustrySectorView
from views.stock_subindustry import StockSubIndustryView
from views.market_comparisons import MarketComparisonsView
from views.research_pack import ResearchPackView
from components.data_loader import DataLoader
from components.status_bar import StatusBar
from utils.config import Config


class MetaMacroTUI(App):
    """MetaMacro Terminal User Interface Application"""

    CSS_PATH = "styles.css"
    TITLE = "MetaMacro Research Dashboard"
    SUB_TITLE = "Terminal Market Analysis Platform"

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh Data"),
        Binding("ctrl+r", "force_refresh", "Force Refresh"),
        Binding("h", "help", "Help"),
        Binding("1", "tab_market", "Market Monitor"),
        Binding("2", "tab_subind", "Sub-Industry"),
        Binding("3", "tab_stock", "Stock Analysis"),
        Binding("4", "tab_compare", "Comparisons"),
        Binding("5", "tab_research", "Research Pack"),
        Binding("e", "export", "Export"),
        Binding("s", "settings", "Settings"),
    ]

    # Reactive variables
    data_loaded = reactive(False)
    current_tab = reactive("market")
    status_message = reactive("Initializing...")

    def __init__(self):
        super().__init__()
        self.config = Config()
        self.data_loader = DataLoader()
        self.universe_data = None
        self.market_data = None

    def compose(self) -> ComposeResult:
        """Create the UI layout"""
        yield Header()

        with Container(id="main-container"):
            # Status bar
            yield StatusBar(id="status-bar")

            # Main content with tabs
            with TabbedContent(initial="market-monitor"):
                with TabPane("Market Monitor", id="market-monitor"):
                    yield MarketMonitorView(id="market-view")

                with TabPane("Sub-Industry vs Sector", id="subindustry-sector"):
                    yield SubIndustrySectorView(id="subind-view")

                with TabPane("Stock vs Sub-Industry", id="stock-subindustry"):
                    yield StockSubIndustryView(id="stock-view")

                with TabPane("Market Comparisons", id="market-comparisons"):
                    yield MarketComparisonsView(id="compare-view")

                with TabPane("Research Pack", id="research-pack"):
                    yield ResearchPackView(id="research-view")

        yield Footer()

    def on_mount(self) -> None:
        """Initialize the application"""
        self.title = self.TITLE
        self.sub_title = self.SUB_TITLE
        self.load_initial_data()

    async def load_initial_data(self) -> None:
        """Load initial market and universe data"""
        try:
            self.status_message = "Loading market data..."

            # Load market data first (always available)
            self.market_data = await self.data_loader.load_market_data(
                period=self.config.default_period,
                interval=self.config.default_interval
            )

            # Try to load universe data from available CSV files
            self.status_message = "Loading universe data..."
            universe_files = self.find_universe_files()

            if universe_files:
                # Use the first available universe file
                self.universe_data = await self.data_loader.load_universe_data(
                    universe_files[0],
                    period=self.config.default_period,
                    interval=self.config.default_interval
                )
                self.status_message = f"Data loaded successfully from {universe_files[0].name}"
            else:
                self.status_message = "Market data loaded. No universe CSV files found."

            self.data_loaded = True

            # Update all views with loaded data
            await self.update_all_views()

        except Exception as e:
            self.status_message = f"Error loading data: {str(e)}"
            self.notify(f"Data loading error: {str(e)}", severity="error")

    def find_universe_files(self) -> list[Path]:
        """Find available universe CSV files in the project directory"""
        project_dir = Path(__file__).parent
        csv_files = []

        # Look for common universe file patterns
        patterns = ["*.csv", "SPX500.csv", "NASDAQ100.csv", "DOW30.csv", "Russel2k.csv"]

        for pattern in patterns:
            csv_files.extend(project_dir.glob(pattern))

        # Filter out any files that might not be universe files
        universe_files = []
        for csv_file in csv_files:
            if csv_file.name.lower() not in ['requirements.txt', 'readme.md']:
                universe_files.append(csv_file)

        return sorted(universe_files)

    async def update_all_views(self) -> None:
        """Update all views with current data"""
        try:
            # Get view widgets
            market_view = self.query_one("#market-view", MarketMonitorView)
            subind_view = self.query_one("#subind-view", SubIndustrySectorView)
            stock_view = self.query_one("#stock-view", StockSubIndustryView)
            compare_view = self.query_one("#compare-view", MarketComparisonsView)
            research_view = self.query_one("#research-view", ResearchPackView)

            # Update views with data
            await market_view.update_data(self.market_data, self.universe_data)

            if self.universe_data:
                await subind_view.update_data(self.universe_data)
                await stock_view.update_data(self.universe_data)
                await compare_view.update_data(self.universe_data)
                await research_view.update_data(self.market_data, self.universe_data)

        except Exception as e:
            self.notify(f"Error updating views: {str(e)}", severity="error")

    # Action handlers
    async def action_refresh(self) -> None:
        """Refresh data"""
        self.status_message = "Refreshing data..."
        await self.load_initial_data()
        self.notify("Data refreshed successfully")

    async def action_force_refresh(self) -> None:
        """Force refresh with cache clear"""
        self.status_message = "Force refreshing data..."
        self.data_loader.clear_cache()
        await self.load_initial_data()
        self.notify("Data force refreshed successfully")

    def action_help(self) -> None:
        """Show help dialog"""
        help_text = """
MetaMacro TUI - Keyboard Shortcuts:

Navigation:
• 1-5: Switch between tabs
• Tab: Navigate between widgets
• Enter: Activate selected item

Data Operations:
• r: Refresh data
• Ctrl+r: Force refresh (clear cache)
• e: Export current view

General:
• h: Show this help
• s: Settings
• q: Quit application

Mouse support is also available for all interactions.
        """
        self.push_screen("help", help_text)

    def action_tab_market(self) -> None:
        """Switch to Market Monitor tab"""
        tabbed_content = self.query_one(TabbedContent)
        tabbed_content.active = "market-monitor"

    def action_tab_subind(self) -> None:
        """Switch to Sub-Industry tab"""
        tabbed_content = self.query_one(TabbedContent)
        tabbed_content.active = "subindustry-sector"

    def action_tab_stock(self) -> None:
        """Switch to Stock Analysis tab"""
        tabbed_content = self.query_one(TabbedContent)
        tabbed_content.active = "stock-subindustry"

    def action_tab_compare(self) -> None:
        """Switch to Comparisons tab"""
        tabbed_content = self.query_one(TabbedContent)
        tabbed_content.active = "market-comparisons"

    def action_tab_research(self) -> None:
        """Switch to Research Pack tab"""
        tabbed_content = self.query_one(TabbedContent)
        tabbed_content.active = "research-pack"

    def action_export(self) -> None:
        """Export current view"""
        # Get current active tab and trigger export
        tabbed_content = self.query_one(TabbedContent)
        current_tab = tabbed_content.active

        if current_tab == "market-monitor":
            market_view = self.query_one("#market-view", MarketMonitorView)
            market_view.export_data()
        elif current_tab == "subindustry-sector":
            subind_view = self.query_one("#subind-view", SubIndustrySectorView)
            subind_view.export_data()
        # Add other export handlers as needed

        self.notify("Export functionality triggered")

    def action_settings(self) -> None:
        """Show settings dialog"""
        self.notify("Settings dialog (to be implemented)")


def main():
    """Main entry point"""
    app = MetaMacroTUI()
    app.run()


if __name__ == "__main__":
    main()
