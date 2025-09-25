"""
Status bar component for MetaMacro TUI
Shows loading status, data information, and system status
"""

from datetime import datetime
from textual.widgets import Static
from textual.reactive import reactive
from rich.text import Text


class StatusBar(Static):
    """Status bar widget showing application status"""

    status_message = reactive("Ready")
    data_loaded = reactive(False)
    last_refresh = reactive(None)
    loading_progress = reactive(0.0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.add_class("status-bar")

    def compose(self):
        """Compose the status bar"""
        return []

    def watch_status_message(self, message: str) -> None:
        """Update when status message changes"""
        self.update_display()

    def watch_data_loaded(self, loaded: bool) -> None:
        """Update when data loading status changes"""
        self.update_display()

    def watch_last_refresh(self, timestamp) -> None:
        """Update when last refresh time changes"""
        self.update_display()

    def watch_loading_progress(self, progress: float) -> None:
        """Update when loading progress changes"""
        self.update_display()

    def update_display(self) -> None:
        """Update the status bar display"""
        # Create status text
        text = Text()

        # Status indicator
        if self.loading_progress > 0 and self.loading_progress < 1:
            # Loading state
            progress_bar = "█" * int(self.loading_progress * 20)
            empty_bar = "░" * (20 - int(self.loading_progress * 20))
            text.append("⟳ ", style="bold blue")
            text.append(f"[{progress_bar}{empty_bar}] ", style="blue")
            text.append(f"{self.loading_progress:.0%} ", style="bold blue")
        elif self.data_loaded:
            text.append("● ", style="bold green")
        else:
            text.append("○ ", style="bold yellow")

        # Status message
        text.append(self.status_message, style="white")

        # Data status
        if self.data_loaded:
            text.append(" | Data: ", style="dim")
            text.append("Loaded", style="green")
        else:
            text.append(" | Data: ", style="dim")
            text.append("Not Loaded", style="yellow")

        # Last refresh time
        if self.last_refresh:
            refresh_time = self.last_refresh.strftime("%H:%M:%S")
            text.append(f" | Last Refresh: {refresh_time}", style="dim")

        # Current time
        current_time = datetime.now().strftime("%H:%M:%S")
        text.append(f" | Time: {current_time}", style="dim")

        # Update the widget
        self.update(text)

    def set_loading(self, message: str, progress: float = 0.0) -> None:
        """Set loading state"""
        self.status_message = message
        self.loading_progress = progress

    def set_success(self, message: str) -> None:
        """Set success state"""
        self.status_message = message
        self.loading_progress = 0.0
        self.data_loaded = True
        self.last_refresh = datetime.now()

    def set_error(self, message: str) -> None:
        """Set error state"""
        self.status_message = f"Error: {message}"
        self.loading_progress = 0.0

    def set_ready(self) -> None:
        """Set ready state"""
        self.status_message = "Ready"
        self.loading_progress = 0.0
