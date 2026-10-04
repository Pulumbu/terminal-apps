"""A line-API meter (handbook section 18.3): a sub-cell progress bar."""

from __future__ import annotations

from rich.segment import Segment
from textual.geometry import Size
from textual.reactive import reactive
from textual.strip import Strip
from textual.widget import Widget

_BLOCKS = " ▏▎▍▌▋▊▉█"


def _bar(fraction: float, width: int) -> str:
    fraction = max(0.0, min(1.0, fraction))
    eighths = round(fraction * width * 8)
    full, rem = divmod(eighths, 8)
    return ("█" * full + (_BLOCKS[rem] if rem else "")).ljust(width)


class ScanMeter(Widget):
    DEFAULT_CSS = """
    ScanMeter { height: 1; width: 1fr; color: $primary; background: $surface; }
    """
    COMPONENT_CLASSES = {"scanmeter--bar"}
    fraction: reactive[float] = reactive(0.0)

    def watch_fraction(self) -> None:
        self.refresh()

    def get_content_height(self, container: Size, viewport: Size, width: int) -> int:
        return 1

    def render_line(self, y: int) -> Strip:
        width = self.content_size.width
        if width <= 0:
            return Strip.blank(0)
        style = self.get_component_rich_style("scanmeter--bar")
        return Strip([Segment(_bar(self.fraction, width), style)], width)
