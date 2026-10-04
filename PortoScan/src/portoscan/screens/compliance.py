"""Show the policy / compliance findings for the current results."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, RichLog

from portoscan.compliance import Finding, summarize

_SEV_STYLE = {"high": "bold red", "medium": "yellow", "low": "dim"}


class ComplianceScreen(ModalScreen[None]):
    CSS = """
    ComplianceScreen { align: center middle; background: $background 60%; }
    #box { width: 84; height: 26; padding: 1 2; border: round $primary; background: $surface; }
    #title { text-style: bold; color: $text-primary; }
    RichLog { height: 1fr; }
    """
    BINDINGS = [("escape", "dismiss", "Close")]

    def __init__(self, findings: list[Finding],
                 title: str = "Policy check (exposed risky services)") -> None:
        super().__init__()
        self.findings = findings
        self._title = title

    def compose(self) -> ComposeResult:
        with Vertical(id="box"):
            yield Label(self._title, id="title")
            yield Label(summarize(self.findings))
            yield RichLog(id="log", markup=True, highlight=False)

    def on_mount(self) -> None:
        log = self.query_one("#log", RichLog)
        if not self.findings:
            log.write("[dim]No open ports matched the policy rules.[/]")
            return
        for finding in self.findings:
            style = _SEV_STYLE.get(finding.severity, "")
            log.write(f"[{style}]{finding.severity.upper():<6}[/] "
                      f"{finding.host}:{finding.port}  {finding.message}")

    def action_dismiss(self) -> None:
        self.dismiss(None)
