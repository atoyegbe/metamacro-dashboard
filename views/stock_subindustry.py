"""Stock vs Sub-Industry view for MetaMacro TUI"""

from textual.widgets import Static, DataTable, Button, Select
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from typing import Dict, Any, Optional


class StockSubIndustryView(Container):
    """Stock vs Sub-Industry analysis view"""

    universe_data = reactive(None)
    current_filter = reactive("All")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.add_class("stock-subindustry")

    def compose(self):
        """Compose the stock vs sub-industry view"""
        with Vertical():
            with Container(classes="card"):
                yield Static("📋 Stock vs Sub-Industry Analysis", classes="card-header")
                with Container(classes="card-content"):
                    with Horizontal():
                        yield Static("Filter by Sub-Industry: ")
                        yield Select([("All", "All")], value="All", id="sub-filter")

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

                    yield DataTable(id="stock-table", classes="regime-table")

                    with Horizontal():
                        yield Button("📄 Export PDF", id="export-pdf")
                        yield Button("📊 Export Excel", id="export-excel")

    async def update_data(self, universe_data: Optional[Dict[str, Any]]):
        """Update the view with universe data"""
        self.universe_data = universe_data
        if universe_data:
            await self.update_filters()
            await self.update_table()

    async def update_filters(self):
        """Update filter options"""
        if not self.universe_data or "universe" not in self.universe_data:
            return

        try:
            sub_filter = self.query_one("#sub-filter", Select)
            uni = self.universe_data["universe"]

            # Update sub-industry filter options
            sub_options = [("All", "All")]
            for sub in sorted(uni["SubIndustry"].unique()):
                sub_options.append((sub, sub))

            sub_filter.set_options(sub_options)
        except Exception:
            pass

    async def update_table(self):
        """Update the data table"""
        # TODO: Implement table update with regime analysis
        try:
            table = self.query_one("#stock-table", DataTable)
            table.clear(columns=True)

            # Add placeholder columns
            table.add_column("Entity")
            table.add_column("Macro")
            table.add_column("Close")

            # Add placeholder data
            table.add_row("AAPL / Technology", "Weak Bull", "0.98")

        except Exception:
            pass

    def export_data(self):
        """Export current view data"""
        self.app.notify("Stock analysis export functionality to be implemented")
