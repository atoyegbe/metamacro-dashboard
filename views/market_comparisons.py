"""Market Comparisons view for MetaMacro TUI"""

from textual.widgets import Static, DataTable, Button, Select
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from typing import Dict, Any, Optional


class MarketComparisonsView(Container):
    """Market comparisons analysis view"""

    universe_data = reactive(None)
    lhs_choice = reactive("")
    rhs_choice = reactive("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.add_class("market-comparisons")

    def compose(self):
        """Compose the market comparisons view"""
        with Vertical():
            with Container(classes="card"):
                yield Static("📋 Market Comparisons", classes="card-header")
                with Container(classes="card-content"):
                    with Horizontal():
                        yield Static("Select first entity (LHS): ")
                        yield Select([("Select...", "Select...")], value="Select...", id="lhs-select")

                    with Horizontal():
                        yield Static("Select second entity (RHS): ")
                        yield Select([("Select...", "Select...")], value="Select...", id="rhs-select")

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

                    yield DataTable(id="comparison-table", classes="regime-table")

                    with Container(id="chart-section"):
                        yield Static("📈 Comparison Chart", classes="card-header")
                        yield Static("Chart will be displayed here", id="chart-display")

                    with Horizontal():
                        yield Button("📄 Export PDF", id="export-pdf")
                        yield Button("📊 Export Excel", id="export-excel")

    async def update_data(self, universe_data: Optional[Dict[str, Any]]):
        """Update the view with universe data"""
        self.universe_data = universe_data
        if universe_data:
            await self.update_entity_options()
            await self.update_comparison()

    async def update_entity_options(self):
        """Update entity selection options"""
        if not self.universe_data or "tickers" not in self.universe_data:
            return

        try:
            lhs_select = self.query_one("#lhs-select", Select)
            rhs_select = self.query_one("#rhs-select", Select)

            # Get available entities
            tickers = self.universe_data["tickers"]
            entity_options = [("Select...", "Select...")]
            for ticker in sorted(tickers):
                entity_options.append((ticker, ticker))

            lhs_select.set_options(entity_options)
            rhs_select.set_options(entity_options)

        except Exception:
            pass

    async def update_comparison(self):
        """Update the comparison analysis"""
        if not self.lhs_choice or not self.rhs_choice or self.lhs_choice == "Select..." or self.rhs_choice == "Select...":
            return

        try:
            table = self.query_one("#comparison-table", DataTable)
            table.clear(columns=True)

            # Add columns
            table.add_column("Entity")
            table.add_column("Macro")
            table.add_column("Close")

            # Add comparison data
            comparison_name = f"{self.lhs_choice} / {self.rhs_choice}"
            table.add_row(comparison_name, "Strong Bull", "1.15")

            # Update chart display
            chart_display = self.query_one("#chart-display", Static)
            chart_display.update(f"Chart for {comparison_name}")

        except Exception:
            pass

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle selection changes"""
        if event.select.id == "lhs-select":
            self.lhs_choice = event.value
            self.call_after_refresh(self.update_comparison)
        elif event.select.id == "rhs-select":
            self.rhs_choice = event.value
            self.call_after_refresh(self.update_comparison)

    def export_data(self):
        """Export current view data"""
        self.app.notify("Market comparison export functionality to be implemented")
