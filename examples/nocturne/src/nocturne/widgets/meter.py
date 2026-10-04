"""A custom widget built with the line API (``render_line`` -> ``Strip``)."""

from __future__ import annotations

import math

from rich.segment import Segment
from textual.geometry import Size
from textual.reactive import reactive
from textual.strip import Strip
from textual.widget import Widget

BLOCKS = " ▏▎▍▌▋▊▉█"
WAVE = "▁▂▃▄▅▆▇█"


def smooth_bar(fraction: float, width: int) -> str:
    """A horizontal bar with 1/8-of-a-cell precision."""
    fraction = max(0.0, min(1.0, fraction))
    total_eighths = round(fraction * width * 8)
    full, remainder = divmod(total_eighths, 8)
    return ("█" * full + (BLOCKS[remainder] if remainder else "")).ljust(width)


def wave(width: int, phase: float) -> str:
    return "".join(
        WAVE[int((math.sin((x / 4) + phase) + 1) / 2 * (len(WAVE) - 1))]
        for x in range(width)
    )


class WaveMeter(Widget, can_focus=True):
    """Two rows: a sub-cell bar and an animated wave."""

    DEFAULT_CSS = """
    WaveMeter {
        height: 2;
        width: 1fr;
        background: $surface;
        color: $primary;
        &:focus { background: $surface-lighten-1; }
    }
    """
    COMPONENT_CLASSES = {"wavemeter--bar", "wavemeter--wave"}

    value: reactive[float] = reactive(0.0)
    phase: reactive[float] = reactive(0.0)

    def __init__(self, *, fps: float = 20.0, **kwargs: object) -> None:
        super().__init__(**kwargs)  # type: ignore[arg-type]
        self._fps = fps

    def on_mount(self) -> None:
        # The widget owns its own timer, so removing the widget stops it. An
        # App-level interval that reaches into the DOM will eventually fire
        # after the widget is gone and raise NoMatches.
        self.set_interval(1 / self._fps, self._advance)

    def _advance(self) -> None:
        self.phase += 0.25

    def watch_value(self) -> None:
        self.refresh()

    def watch_phase(self) -> None:
        self.refresh()

    def get_content_height(self, container: Size, viewport: Size, width: int) -> int:
        return 2

    def get_content_width(self, container: Size, viewport: Size) -> int:
        return container.width

    def render_line(self, y: int) -> Strip:
        width = self.content_size.width
        if width <= 0:
            return Strip.blank(0)
        if y == 0:
            style = self.get_component_rich_style("wavemeter--bar")
            return Strip([Segment(smooth_bar(self.value, width), style)], width)
        style = self.get_component_rich_style("wavemeter--wave")
        return Strip([Segment(wave(width, self.phase), style)], width)
