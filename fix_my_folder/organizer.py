from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import hashlib
import os
import threading
from datetime import datetime

from .actions import Action, safe_category_name
from .rules import EXTENSION_CATEGORIES, categorize_by_rules


IGNORED_DIRECTORIES = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".fix-my-folder-trash",
    "Files To Review Before Deleting",
    "node_modules",
}

PRIVATE_FILE_NAMES = {
    ".env",
    ".env.local",
    ".env.production",
    ".npmrc",
    ".pypirc",
    ".netrc",
    "id_rsa",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    "known_hosts",
}

PRIVATE_EXTENSIONS = {
    ".key",
    ".pem",
    ".p12",
    ".pfx",
    ".crt",
    ".cer",
}

WINDOWS_HIDDEN = 0x2
WINDOWS_SYSTEM = 0x4


ProgressCallback = Callable[[int, int, str], None]
ORGANIZE_SCHEMES = {
    "type",
    "extension",
    "modified_year",
    "modified_month",
}
EXTRACTABLE_SUFFIXES = {
    ".zip",
    ".tar",
    ".tgz",
    ".tbz2",
    ".txz",
}
EXTRACTABLE_COMPOUND_SUFFIXES = {
    ".tar.gz",
    ".tar.bz2",
    ".tar.xz",
}


class ScanCancelled(Exception):
    """Raised when the user cancels an in-progress scan."""


def build_plan(
    folder: Path,
    mode: str = "organize",
    organize_by: str = "type",
    progress_callback: ProgressCallback | None = None,
    cancel_event: threading.Event | None = None,
) -> list[Action]:
    files = collect_files(folder, progress_callback, cancel_event)
    return build_plan_from_files(
        files,
        target_root=folder,
        mode=mode,
        organize_by=organize_by,
        progress_callback=progress_callback,
        cancel_event=cancel_event,
    )


def build_plan_for_paths(
    paths: list[Path],
    mode: str = "organize",
    organize_by: str = "type",
    progress_callback: ProgressCallback | None = None,
    cancel_event: threading.Event | None = None,
) -> tuple[list[Action], Path]:
    files = [path.expanduser().resolve() for path in paths if is_allowed_file(path.expanduser())]
    target_root = common_parent(files)
    return (
        build_plan_from_files(
            files,
            target_root=target_root,
            mode=mode,
            organize_by=organize_by,
            progress_callback=progress_callback,
            cancel_event=cancel_event,
        ),
        target_root,
    )


def build_plan_from_files(
    files: list[Path],
    target_root: Path,
    mode: str = "organize",
    organize_by: str = "type",
    progress_callback: ProgressCallback | None = None,
    cancel_event: threading.Event | None = None,
) -> list[Action]:
    actions: list[Action] = []
    total_steps = len(files) * (2 if mode == "full" else 1)
    completed_steps = 0

    def report(message: str) -> None:
        if progress_callback is not None:
            progress_callback(completed_steps, max(total_steps, 1), message)

    def check_cancelled() -> None:
        if cancel_event is not None and cancel_event.is_set():
            raise ScanCancelled()

    report(f"Found {len(files)} file(s).")

    if mode in {"organize", "full"}:
        if organize_by == "type":
            categorized = categorize_files_fast(files, progress_callback, cancel_event, completed_steps, total_steps)
        else:
            categorized = categorize_without_ai(files)
            if progress_callback is not None:
                progress_callback(
                    completed_steps,
                    max(total_steps, 1),
                    "Using local sorting rules for this filter.",
                )
        for index, path in enumerate(files, start=1):
            check_cancelled()
            category, reason = categorized[path]
            category_name = folder_name_for_file(path, category, organize_by)
            action_reason = organize_reason_for_file(path, reason, organize_by)
            target_dir = target_root / category_name
            target = target_dir / path.name
            if path.parent != target_dir:
                actions.append(
                    Action(
                        kind="move",
                        source=path,
                        target=target,
                        reason=action_reason,
                        category=category_name,
                    )
                )
            completed_steps += 1
            if index % 100 == 0 or index == len(files):
                report(f"Prepared {index} of {len(files)} file(s).")

    if mode in {"cleanup", "full"}:
        actions.extend(cleanup_actions(files, progress_callback, cancel_event, completed_steps, total_steps))

    if mode == "extract":
        actions.extend(extract_actions(files, target_root, progress_callback, cancel_event, completed_steps, total_steps))

    if mode == "remove_from_folder":
        actions.extend(remove_from_folder_actions(files, target_root, progress_callback, cancel_event, completed_steps, total_steps))

    check_cancelled()
    final_actions = dedupe_conflicting_actions(actions)
    if progress_callback is not None:
        progress_callback(max(total_steps, 1), max(total_steps, 1), "Scan complete.")
    return final_actions


def categorize_files_fast(
    files: list[Path],
    progress_callback: ProgressCallback | None,
    cancel_event: threading.Event | None,
    completed_offset: int,
    total_steps: int,
) -> dict[Path, tuple[str, str]]:
    results: dict[Path, tuple[str, str]] = {}

    for index, path in enumerate(files, start=1):
        if cancel_event is not None and cancel_event.is_set():
            raise ScanCancelled()
        results[path] = categorize_by_rules(path)
        if progress_callback is not None and index % 100 == 0:
            progress_callback(
                completed_offset,
                max(total_steps, 1),
                f"Prepared {index} file(s) with local rules...",
            )

    if progress_callback is not None:
        progress_callback(
            completed_offset,
            max(total_steps, 1),
            "Using local file-type rules.",
        )
    return results


def categorize_without_ai(files: list[Path]) -> dict[Path, tuple[str, str]]:
    return {path: categorize_by_rules(path) for path in files}


def folder_name_for_file(path: Path, category: str, organize_by: str) -> str:
    scheme = organize_by if organize_by in ORGANIZE_SCHEMES else "type"
    if scheme == "extension":
        suffix = path.suffix.lower().lstrip(".")
        return safe_category_name(suffix.upper() if suffix else "No Extension")
    if scheme == "modified_year":
        return safe_category_name(str(file_modified_time(path).year))
    if scheme == "modified_month":
        modified = file_modified_time(path)
        return safe_category_name(f"{modified.year}-{modified.month:02d}")
    return safe_category_name(category)


def organize_reason_for_file(path: Path, category_reason: str, organize_by: str) -> str:
    scheme = organize_by if organize_by in ORGANIZE_SCHEMES else "type"
    if scheme == "extension":
        return f"Sorted by file format '{path.suffix.lower() or 'none'}'."
    if scheme == "modified_year":
        return f"Sorted by modified year {file_modified_time(path).year}."
    if scheme == "modified_month":
        modified = file_modified_time(path)
        return f"Sorted by modified month {modified.year}-{modified.month:02d}."
    return category_reason


def file_modified_time(path: Path) -> datetime:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime)
    except OSError:
        return datetime.fromtimestamp(0)


def scan_files(folder: Path):
    for path in folder.rglob("*"):
        relative_parts = path.relative_to(folder).parts
        if any(part in IGNORED_DIRECTORIES for part in relative_parts):
            continue
        if not is_allowed_file(path):
            continue
        yield path


def extract_actions(
    files: list[Path],
    target_root: Path,
    progress_callback: ProgressCallback | None = None,
    cancel_event: threading.Event | None = None,
    completed_offset: int = 0,
    total_steps: int | None = None,
) -> list[Action]:
    actions: list[Action] = []
    total = total_steps or max(len(files), 1)
    extract_root = target_root / "Extracted"

    for index, path in enumerate(files, start=1):
        if cancel_event is not None and cancel_event.is_set():
            raise ScanCancelled()
        if not is_extractable_archive(path):
            continue
        target = extract_root / safe_category_name(archive_folder_name(path))
        actions.append(
            Action(
                kind="extract",
                source=path,
                target=target,
                reason="Supported archive found. Extract into a separate folder.",
                category="Extracted",
            )
        )
        if progress_callback is not None and (index % 50 == 0 or index == len(files)):
            progress_callback(completed_offset + index, total, f"Prepared archive extraction for {path.name}.")

    return actions


def remove_from_folder_actions(
    files: list[Path],
    target_root: Path,
    progress_callback: ProgressCallback | None = None,
    cancel_event: threading.Event | None = None,
    completed_offset: int = 0,
    total_steps: int | None = None,
) -> list[Action]:
    actions: list[Action] = []
    total = total_steps or max(len(files), 1)
    folder_target = target_root.parent if target_root.parent != target_root else None

    for index, path in enumerate(files, start=1):
        if cancel_event is not None and cancel_event.is_set():
            raise ScanCancelled()
        destination_parent = folder_target if path.is_relative_to(target_root) else path.parent.parent
        if destination_parent is None or destination_parent == path.parent:
            continue
        actions.append(
            Action(
                kind="move",
                source=path,
                target=destination_parent / path.name,
                reason="Remove from folder by moving it one level outside.",
                category="Removed From Folder",
            )
        )
        if progress_callback is not None and (index % 100 == 0 or index == len(files)):
            progress_callback(completed_offset + index, total, f"Prepared {index} file(s) to remove from folder.")

    return actions


def is_extractable_archive(path: Path) -> bool:
    suffix = path.suffix.lower()
    compound = "".join(path.suffixes[-2:]).lower()
    return suffix in EXTRACTABLE_SUFFIXES or compound in EXTRACTABLE_COMPOUND_SUFFIXES


def archive_folder_name(path: Path) -> str:
    name = path.name
    for extension in sorted(EXTRACTABLE_COMPOUND_SUFFIXES, key=len, reverse=True):
        if name.lower().endswith(extension):
            return name[: -len(extension)]
    if path.suffix.lower() in EXTRACTABLE_SUFFIXES:
        return path.stem
    return path.stem


def collect_files(
    folder: Path,
    progress_callback: ProgressCallback | None = None,
    cancel_event: threading.Event | None = None,
) -> list[Path]:
    files: list[Path] = []
    if progress_callback is not None:
        progress_callback(-1, 0, "Finding files...")

    for path in scan_files(folder):
        if cancel_event is not None and cancel_event.is_set():
            raise ScanCancelled()
        files.append(path)
        if progress_callback is not None and len(files) % 100 == 0:
            progress_callback(-1, 0, f"Found {len(files)} file(s)...")

    if progress_callback is not None:
        progress_callback(0, max(len(files), 1), f"Found {len(files)} file(s).")
    return files


def is_allowed_file(path: Path) -> bool:
    return is_allowed_item(path, allow_dirs=False)


def is_allowed_item(path: Path, *, allow_dirs: bool) -> bool:
    try:
        if path.is_symlink():
            return False
        if allow_dirs:
            if not (path.is_file() or path.is_dir()):
                return False
        elif not path.is_file():
            return False
        if is_private_path(path):
            return False
    except OSError:
        return False
    return True


def is_private_path(path: Path) -> bool:
    name = path.name.lower()
    if name.startswith(".") or name in PRIVATE_FILE_NAMES or path.suffix.lower() in PRIVATE_EXTENSIONS:
        return True

    for part in path.parts:
        lowered = part.lower()
        if lowered.startswith(".") and lowered not in {".", ".."}:
            return True

    attributes = getattr(path.stat(), "st_file_attributes", 0)
    return bool(attributes & (WINDOWS_HIDDEN | WINDOWS_SYSTEM))


def common_parent(files: list[Path]) -> Path:
    if not files:
        return Path.cwd()

    parents = [str(path.parent) for path in files]
    try:
        return Path(os.path.commonpath(parents))
    except ValueError:
        return files[0].parent


def cleanup_actions(
    files: list[Path],
    progress_callback: ProgressCallback | None = None,
    cancel_event: threading.Event | None = None,
    completed_offset: int = 0,
    total_steps: int | None = None,
) -> list[Action]:
    actions: list[Action] = []
    size_groups: dict[int, list[Path]] = defaultdict(list)
    hash_groups: dict[str, list[Path]] = defaultdict(list)
    total = total_steps or max(len(files), 1)

    for index, path in enumerate(files, start=1):
        if cancel_event is not None and cancel_event.is_set():
            raise ScanCancelled()
        if progress_callback is not None and (index % 50 == 1 or index == len(files)):
            progress_callback(completed_offset + index - 1, total, f"Checking cleanup for {path.name}...")
        try:
            if path.stat().st_size == 0:
                actions.append(
                    Action(
                        kind="delete",
                        source=path,
                        target=None,
                        reason="Empty file.",
                    )
                )
                continue
            size_groups[path.stat().st_size].append(path)
        except OSError:
            continue
        if progress_callback is not None and (index % 50 == 0 or index == len(files)):
            progress_callback(completed_offset + index, total, f"Checked {path.name}.")

    candidates = [path for matches in size_groups.values() if len(matches) > 1 for path in matches]
    if candidates and progress_callback is not None:
        progress_callback(completed_offset, total, f"Hashing {len(candidates)} possible duplicate file(s)...")

    workers = min(8, max(1, (os.cpu_count() or 2)))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_map = {executor.submit(file_hash, path): path for path in candidates}
        for done_count, future in enumerate(as_completed(future_map), start=1):
            if cancel_event is not None and cancel_event.is_set():
                raise ScanCancelled()
            path = future_map[future]
            try:
                hash_groups[future.result()].append(path)
            except OSError:
                continue
            if progress_callback is not None and done_count % 10 == 0:
                progress_callback(
                    completed_offset,
                    total,
                    f"Hashed {done_count} of {len(candidates)} possible duplicate file(s)...",
                )

    for matches in hash_groups.values():
        if len(matches) < 2:
            continue
        keeper = sorted(matches, key=lambda item: (len(item.parts), str(item).lower()))[0]
        for duplicate in matches:
            if duplicate == keeper:
                continue
            actions.append(
                Action(
                    kind="delete",
                    source=duplicate,
                    target=None,
                    reason=f"Duplicate of {keeper.name}.",
                )
            )

    return actions


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def dedupe_conflicting_actions(actions: list[Action]) -> list[Action]:
    by_source: dict[Path, Action] = {}
    for action in actions:
        existing = by_source.get(action.source)
        if existing is None or action.kind == "delete":
            by_source[action.source] = action
    return list(by_source.values())
