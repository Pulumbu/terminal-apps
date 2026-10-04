"""An always-visible banner stating what will be scanned and the rate preset."""

from __future__ import annotations

from textual.widgets import Static

from portoscan.authorization import ScopeReport


class ScopeBanner(Static):
    DEFAULT_CSS = """
    ScopeBanner {
        dock: top;
        height: 1;
        padding: 0 1;
        background: $panel;
        color: $text-muted;
    }
    ScopeBanner.-public { background: $warning 25%; color: $text-warning; }
    """

    def show(self, report: ScopeReport, ports: int, preset: str) -> None:
        if report.total == 0:
            self.remove_class("-public")
            self.update("No targets selected")
            return
        parts = [f"{report.total} hosts x {ports} ports", f"{preset} preset"]
        if report.all_local:
            parts.append("private/loopback - authorized")
            self.remove_class("-public")
        else:
            bits = []
            if report.public:
                bits.append(f"{report.public} public")
            if report.hostnames:
                bits.append(f"{report.hostnames} hostname(s)")
            parts.append("includes " + ", ".join(bits) + " - ensure you are authorized")
            self.add_class("-public")
        self.update("  |  ".join(parts))
