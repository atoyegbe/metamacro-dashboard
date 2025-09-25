"""
Market Monitor view for MetaMacro TUI
Shows market indices, flows, and regime analysis
"""

import pandas as pd
import plotext as plt
from typing import Dict, Any, Optional
from textual.widgets import Static, DataTable, Button, Select
from textual.containers import Container, Horizontal, Vertical, Grid
from textual.reactive import reactive
from rich.table import Table
from rich.text import Text
from rich.console import Console
from rich.panel import Panel


class MarketMonitorView(Container):
    """Market monitor view showing indices and flows"""

    market_data = reactive(None)
    universe_data = reactive(None)
    current_filter = reactive("All")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.add_class("market-monitor")

    def compose(self):
        """Compose the market monitor view"""
        with Vertical():
            # KPI Cards Section
            with Container(id="kpi-section", classes="card"):
                yield Static("📊 Market KPIs", classes="card-header")
                with Container(classes="card-content"):
                    yield Static("KPI cards will be displayed here", id="kpi-display")

            # Data Summary
            with Container(id="summary-section", classes="card"):
                yield Static("📈 Data Summary", classes="card-header")
                yield Static("Data summary will be displayed here", id="summary-display")

            # Regime Table Section
            with Container(id="regime-table-section", classes="card"):
                yield Static("📋 Market Regime States", classes="card-header")
                with Container(classes="card-content"):
                    with Horizontal():
                        yield Static("Filter Macro Regime: ")
                        yield Select([
                            ("All", "All"),
                            ("Strong Bull", "Strong Bull"),
                            ("Weak Bull", "Weak Bull"),
                            ("Strong Bear", "Strong Bear"),
                            ("Weak Bear", "Weak Bear"),
                            ("Neutral", "Neutral")
                        ], value="All", id="regime-filter")

                    yield DataTable(id="regime-table", classes="regime-table")

            # Charts Section
            with Container(id="charts-section", classes="card"):
                yield Static("📈 Market Flow Charts", classes="card-header")
                with Container(classes="card-content"):
                    yield Static("Charts will be displayed here", id="charts-display")

            # Export Section
            with Container(id="export-section", classes="card"):
                yield Static("📤 Export Options", classes="card-header")
                with Container(classes="card-content"):
                    with Horizontal():
                        yield Button("📄 Export PDF", id="export-pdf", classes="button-primary")
                        yield Button("📊 Export Excel", id="export-excel", classes="button-primary")

    async def update_data(self, market_data: Optional[Dict[str, Any]], universe_data: Optional[Dict[str, Any]] = None):
        """Update the view with new data"""
        self.market_data = market_data
        self.universe_data = universe_data

        if market_data:
            await self.update_kpi_display()
            await self.update_data_summary()
            await self.update_regime_table()
            await self.update_charts()

    async def update_kpi_display(self):
        """Update KPI display with market data"""
        if not self.market_data or "regime_table" not in self.market_data:
            return

        regime_df = self.market_data["regime_table"]
        if regime_df.empty:
            return

        try:
            kpi_display = self.query_one("#kpi-display", Static)

            # Create KPI text display
            kpi_text = Text()

            for _, row in regime_df.iterrows():
                entity = row.get("Entity", "Unknown")
                macro = row.get("Macro", "N/A")
                close = row.get("Close", 0)

                # Add entity name
                kpi_text.append(f"{entity}: ", style="bold white")

                # Add regime with color
                regime_color = self.get_regime_color(macro)
                kpi_text.append(f"{macro}", style=regime_color)

                # Add close price
                if pd.notna(close):
                    kpi_text.append(f" ({close:.2f})", style="blue")

                kpi_text.append("\n")

            kpi_display.update(kpi_text)

        except Exception as e:
            pass

    def get_regime_color(self, regime: str) -> str:
        """Get color for regime display"""
        regime_str = str(regime).lower()
        if "strong bull" in regime_str:
            return "bold green"
        elif "weak bull" in regime_str:
            return "green"
        elif "weak bear" in regime_str:
            return "yellow"
        elif "strong bear" in regime_str:
            return "bold red"
        else:
            return "white"

    async def update_data_summary(self):
        """Update data summary widget"""
        if not self.market_data or "regime_table" not in self.market_data:
            return

        try:
            summary_display = self.query_one("#summary-display", Static)
            regime_df = self.market_data["regime_table"]

            if regime_df.empty:
                summary_display.update("No data available")
                return

            # Calculate summary statistics
            total_entities = len(regime_df)
            bull_count = len(regime_df[regime_df.get('Macro', '').astype(str).str.contains('Bull', na=False)])
            bear_count = len(regime_df[regime_df.get('Macro', '').astype(str).str.contains('Bear', na=False)])
            neutral_count = total_entities - bull_count - bear_count
            bull_ratio = (bull_count / total_entities * 100) if total_entities > 0 else 0

            # Create summary text
            summary_text = Text()
            summary_text.append(f"Total Entities: ", style="white")
            summary_text.append(f"{total_entities}", style="bold blue")
            summary_text.append(" | ")

            summary_text.append(f"Bullish: ", style="white")
            summary_text.append(f"{bull_count}", style="bold green")
            summary_text.append(" | ")

            summary_text.append(f"Bearish: ", style="white")
            summary_text.append(f"{bear_count}", style="bold red")
            summary_text.append(" | ")

            summary_text.append(f"Neutral: ", style="white")
            summary_text.append(f"{neutral_count}", style="white")
            summary_text.append(" | ")

            summary_text.append(f"Bull Ratio: ", style="white")
            summary_text.append(f"{bull_ratio:.1f}%", style="bold yellow")

            summary_display.update(summary_text)

        except Exception as e:
            pass

    async def update_regime_table(self):
        """Update the regime table"""
        if not self.market_data or "regime_table" not in self.market_data:
            return

        try:
            table = self.query_one("#regime-table", DataTable)
            regime_df = self.market_data["regime_table"]

            # Clear existing data
            table.clear(columns=True)

            if regime_df.empty:
                return

            # Apply filter
            filtered_df = regime_df
            if self.current_filter != "All":
                filtered_df = regime_df[regime_df.get("Macro", "") == self.current_filter]

            if filtered_df.empty:
                return

            # Set up columns
            columns = ["Entity", "Close", "Macro", "Micro", "Transition"]

            # Add weekly columns if available
            for col in ["WeeklyMacro", "WeeklyMicro", "WeeklyTransition"]:
                if col in filtered_df.columns:
                    columns.append(col)

            # Add daily columns if available
            for col in ["DailyMacro", "DailyMicro", "DailyTransition"]:
                if col in filtered_df.columns:
                    columns.append(col)

            # Add session columns if available
            for col in ["Session", "SessionMacro", "SessionMicro", "SessionTransition"]:
                if col in filtered_df.columns:
                    columns.append(col)

            # Add columns to table
            for col in columns:
                if col in filtered_df.columns:
                    table.add_column(col, key=col)

            # Add rows
            for _, row in filtered_df.iterrows():
                row_data = []
                for col in columns:
                    if col in filtered_df.columns:
                        value = row.get(col, "")
                        if col == "Close" and pd.notna(value):
                            try:
                                row_data.append(f"{float(value):.2f}")
                            except:
                                row_data.append(str(value))
                        else:
                            row_data.append(str(value))

                if row_data:
                    table.add_row(*row_data)

        except Exception as e:
            pass

    async def update_charts(self):
        """Update chart displays"""
        if not self.market_data:
            return

        try:
            charts_display = self.query_one("#charts-display", Static)

            # Create simple text-based chart representation
            chart_text = Text()

            # Composite Market Chart
            if "composite_market" in self.market_data:
                df = self.market_data["composite_market"]
                if not df.empty and "Close" in df.columns:
                    latest_close = df["Close"].iloc[-1]
                    chart_text.append("Composite Market: ", style="bold white")
                    chart_text.append(f"{latest_close:.2f}", style="blue")
                    chart_text.append("\n")

            # VIX Chart
            if "vix" in self.market_data:
                df = self.market_data["vix"]
                if not df.empty and "Close" in df.columns:
                    latest_close = df["Close"].iloc[-1]
                    chart_text.append("VIX: ", style="bold white")
                    chart_text.append(f"{latest_close:.2f}", style="orange")
                    chart_text.append("\n")

            # Index flows
            if "flows" in self.market_data:
                flows = self.market_data["flows"]
                for name, df in flows.items():
                    if not df.empty and "Close" in df.columns:
                        latest_close = df["Close"].iloc[-1]
                        chart_text.append(f"{name}: ", style="white")
                        chart_text.append(f"{latest_close:.4f}", style="cyan")
                        chart_text.append("\n")

            charts_display.update(chart_text)

        except Exception as e:
            pass

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle filter selection change"""
        if event.select.id == "regime-filter":
            self.current_filter = event.value
            # Trigger table update
            self.call_after_refresh(self.update_regime_table)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        if event.button.id == "export-pdf":
            self.export_pdf()
        elif event.button.id == "export-excel":
            self.export_excel()

    def export_pdf(self) -> None:
        """Export market data to PDF"""
        # TODO: Implement PDF export
        self.app.notify("PDF export functionality to be implemented")

    def export_excel(self) -> None:
        """Export market data to Excel"""
        # TODO: Implement Excel export
        self.app.notify("Excel export functionality to be implemented")
