"""Show actively-verified findings with redacted evidence."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, RichLog

from portoscan.compliance import Finding

_SEV_STYLE = {"high": "bold red", "medium": "yellow", "low": "dim"}


class VerifyScreen(ModalScreen[None]):
    CSS = """
    VerifyScreen { align: center middle; background: $background 60%; }
    #box { width: 92; height: 28; padding: 1 2; border: round $primary; background: $surface; }
    #title { text-style: bold; color: $text-primary; }
    RichLog { height: 1fr; }
    """
    BINDINGS = [("escape", "dismiss", "Close")]

    def __init__(self, findings: list[Finding], *, saved_to: str = "") -> None:
        super().__init__()
        self.findings = findings
        self.saved_to = saved_to

    def compose(self) -> ComposeResult:
        confirmed = sum(1 for f in self.findings if f.confirmed)
        with Vertical(id="box"):
            yield Label("Active verification results", id="title")
            yield Label(f"{confirmed} confirmed of {len(self.findings)} finding(s)"
                        + (f"  ·  saved to {self.saved_to}" if self.saved_to else ""))
            yield RichLog(id="log", markup=True, highlight=False)

    def on_mount(self) -> None:
        log = self.query_one("#log", RichLog)
        if not self.findings:
            log.write("[dim]Nothing to verify, or nothing confirmed.[/]")
            return
        for finding in self.findings:
            style = _SEV_STYLE.get(finding.severity, "")
            mark = "✓" if finding.confirmed else "?"
            log.write(f"[{style}]{mark} {finding.severity.upper():<6}[/] "
                      f"{finding.host}:{finding.port}  {finding.message}")
            if finding.evidence:
                log.write(f"      [dim]{finding.evidence}[/]")

    def action_dismiss(self) -> None:
        self.dismiss(None)
