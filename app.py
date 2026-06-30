from __future__ import annotations

import sys

from fix_my_folder.cli import main as cli_main
from fix_my_folder.gui import main as gui_main


if __name__ == "__main__":
    if len(sys.argv) > 1:
        raise SystemExit(cli_main(sys.argv[1:]))
    gui_main()
