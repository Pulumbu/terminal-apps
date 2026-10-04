from __future__ import annotations

import multiprocessing
import sys

if __name__ == "__main__":
    multiprocessing.freeze_support()
    from portoscan.cli import main

    sys.exit(main())
