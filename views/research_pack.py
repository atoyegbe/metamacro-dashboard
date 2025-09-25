"""Research Pack view for MetaMacro TUI"""

from textual.widgets import Static, TextArea, Button
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from typing import Dict, Any, Optional


class ResearchPackView(Container):
    """Research pack generation view"""

    market_data = reactive(None)
    universe_data = reactive(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.add_class("research-pack")

    def compose(self):
        """Compose the research pack view"""
        with Vertical():
            with Container(classes="card"):
                yield Static("📑 MetaMacro Research Pack", classes="card-header")
                with Container(classes="card-content"):
                    yield Static("Generate a consolidated research report across all sections with commentary and exports.")

                    yield Static("✍️ Add Market Commentary:")
                    yield TextArea(
                        text="Write your research notes here...",
                        id="commentary-input"
                    )

                    with Container(id="sections-preview"):
                        yield Static("📋 Included Sections Preview", classes="card-header")
                        yield Static("Sections will be displayed here", id="sections-display")

                    with Horizontal():
                        yield Button("📄 Export Full PDF", id="export-full-pdf", classes="button-primary")
                        yield Button("📊 Export Full Excel", id="export-full-excel", classes="button-primary")

    async def update_data(self, market_data: Optional[Dict[str, Any]], universe_data: Optional[Dict[str, Any]]):
        """Update the view with data"""
        self.market_data = market_data
        self.universe_data = universe_data
        await self.update_sections_preview()

    async def update_sections_preview(self):
        """Update the sections preview"""
        try:
            sections_display = self.query_one("#sections-display", Static)

            preview_text = ""

            if self.market_data:
                preview_text += "✓ Market Regimes\n"

            if self.universe_data:
                preview_text += "✓ Sub-Industry vs Sector\n"
                preview_text += "✓ Stock vs Sub-Industry\n"
                preview_text += "✓ Market Comparisons\n"

            if not preview_text:
                preview_text = "No data available for export"

            sections_display.update(preview_text)

        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        if event.button.id == "export-full-pdf":
            self.export_full_pdf()
        elif event.button.id == "export-full-excel":
            self.export_full_excel()

    def export_full_pdf(self):
        """Export full research pack as PDF"""
        try:
            commentary_input = self.query_one("#commentary-input", TextArea)
            commentary = commentary_input.text

            # TODO: Implement full PDF export with commentary
            self.app.notify(f"Full PDF export with commentary: {len(commentary)} characters")

        except Exception:
            self.app.notify("Full PDF export functionality to be implemented")

    def export_full_excel(self):
        """Export full research pack as Excel"""
        try:
            commentary_input = self.query_one("#commentary-input", TextArea)
            commentary = commentary_input.text

            # TODO: Implement full Excel export
            self.app.notify(f"Full Excel export with commentary: {len(commentary)} characters")

        except Exception:
            self.app.notify("Full Excel export functionality to be implemented")
