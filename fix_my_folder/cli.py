from __future__ import annotations

import argparse
from pathlib import Path
import sys
import tkinter as tk
from tkinter import messagebox

from .actions import apply_actions
from .archive_tools import default_extract_destination, extract_archive
from .organizer import build_plan, build_plan_for_paths


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Local rule-based folder organizer.")
    parser.add_argument("paths", nargs="*", type=Path, help="Folder or file(s) to scan.")
    parser.add_argument("--mode", choices=["organize", "cleanup", "extract", "remove-from-folder", "full"], default="organize")
    parser.add_argument("--extract-archive", type=Path, help="Extract a ZIP/TAR archive from File Explorer integration.")
    parser.add_argument("--extract-to", type=Path, help="Destination folder for --extract-archive.")
    parser.add_argument(
        "--delete-mode",
        choices=["review-folder", "permanent"],
        default="review-folder",
        help="How cleanup delete actions are handled when --apply is used.",
    )
    parser.add_argument("--apply", action="store_true", help="Apply the suggested actions.")
    args = parser.parse_args(argv)

    if args.extract_archive is not None:
        return extract_archive_command(args.extract_archive, args.extract_to)

    if not args.paths:
        print("Choose one folder or one or more files.", file=sys.stderr)
        return 2

    paths = [path.expanduser().resolve() for path in args.paths]
    mode = args.mode.replace("-", "_")
    if len(paths) == 1 and paths[0].is_dir():
        action_root = paths[0]
        plan = build_plan(action_root, mode=mode)
    else:
        missing = [path for path in paths if not path.exists()]
        if missing:
            print(f"Path not found: {missing[0]}", file=sys.stderr)
            return 2
        selected = [path for path in paths if path.is_file()]
        if not selected:
            print("Choose one folder or one or more files.", file=sys.stderr)
            return 2
        plan, action_root = build_plan_for_paths(selected, mode=mode)

    if not action_root.exists():
        print(f"Source not found: {action_root}", file=sys.stderr)
        return 2

    if not plan:
        print("No actions suggested.")
        return 0

    for index, action in enumerate(plan, start=1):
        target = f" -> {action.target}" if action.target else ""
        print(f"{index}. {action.kind.upper()}: {action.source}{target}")
        print(f"   Reason: {action.reason}")

    if args.apply:
        print()
        logs, _ = apply_actions(plan, action_root, delete_mode=args.delete_mode.replace("-", "_"))
        for log in logs:
            print(log)
    else:
        print("\nDry run only. Add --apply to make changes.")

    return 0


def extract_archive_command(source: Path, destination: Path | None = None) -> int:
    try:
        target = extract_archive(source, destination or default_extract_destination(source))
    except Exception as exc:
        _shell_message("Extract failed", str(exc), error=True)
        return 1
    _shell_message("Extract complete", f"Extracted to:\n{target}")
    return 0


def _shell_message(title: str, message: str, *, error: bool = False) -> None:
    try:
        root = tk.Tk()
        root.withdraw()
        if error:
            messagebox.showerror(title, message)
        else:
            messagebox.showinfo(title, message)
        root.destroy()
    except tk.TclError:
        stream = sys.stderr if error else sys.stdout
        print(f"{title}: {message}", file=stream)


if __name__ == "__main__":
    raise SystemExit(main())
