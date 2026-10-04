"""Entry point for `python -m nocturne` and for the frozen executable.

`freeze_support()` must run before anything else: without it, every
multiprocessing worker in a frozen build re-executes the whole application.
"""

from __future__ import annotations

import multiprocessing
import sys

if __name__ == "__main__":
    multiprocessing.freeze_support()
    from nocturne.cli import main

    sys.exit(main())
