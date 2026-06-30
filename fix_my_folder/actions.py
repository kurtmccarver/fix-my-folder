from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import tarfile
import zipfile

try:
    from send2trash import send2trash
except ImportError:  # pragma: no cover - optional dependency
    send2trash = None


@dataclass(frozen=True)
class Action:
    kind: str
    source: Path
    target: Path | None
    reason: str
    category: str | None = None


@dataclass(frozen=True)
class AppliedAction:
    kind: str
    original: Path
    current: Path
    reason: str


def safe_category_name(name: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in (" ", "-", "_") else "_" for ch in name)
    cleaned = " ".join(cleaned.strip().split())
    return cleaned or "Other"


def unique_destination(path: Path) -> Path:
    if not path.exists():
        return path

    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    counter = 2
    while True:
        candidate = parent / f"{stem} ({counter}){suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def apply_actions(
    actions: list[Action],
    folder: Path,
    *,
    prefer_system_trash: bool = True,
    delete_mode: str = "review_folder",
) -> tuple[list[str], list[AppliedAction]]:
    logs: list[str] = []
    applied: list[AppliedAction] = []
    review_delete_dir = folder / "Files To Review Before Deleting"

    for action in actions:
        if not action.source.exists():
            logs.append(f"Skipped missing file: {action.source}")
            continue
        if action.source.is_symlink() or not action.source.is_file():
            logs.append(f"Skipped unsafe source: {action.source}")
            continue

        if action.kind == "extract":
            if action.target is None:
                logs.append(f"Skipped extract without target: {action.source}")
                continue
            final_target = unique_destination(action.target.resolve(strict=False))
            final_target.mkdir(parents=True, exist_ok=True)
            try:
                safe_extract_archive(action.source, final_target)
            except (OSError, ValueError, tarfile.TarError, zipfile.BadZipFile, shutil.ReadError) as exc:
                shutil.rmtree(final_target, ignore_errors=True)
                logs.append(f"Skipped extract for {action.source.name}: {exc}")
                continue
            applied.append(
                AppliedAction(
                    kind="extract",
                    original=action.source,
                    current=final_target,
                    reason=action.reason,
                )
            )
            logs.append(f"Extracted: {action.source.name} -> {final_target}")
            continue

        if action.kind == "move":
            if action.target is None:
                logs.append(f"Skipped move without target: {action.source}")
                continue
            final_target = unique_destination(action.target.resolve(strict=False))
            final_target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(action.source), str(final_target))
            applied.append(
                AppliedAction(
                    kind="move",
                    original=action.source,
                    current=final_target,
                    reason=action.reason,
                )
            )
            logs.append(f"Moved: {action.source.name} -> {final_target.parent.name}/{final_target.name}")
            continue

        if action.kind == "delete":
            if delete_mode == "permanent":
                action.source.unlink()
                logs.append(f"Permanently deleted: {action.source.name}")
            elif delete_mode == "system_trash" and prefer_system_trash and send2trash is not None:
                send2trash(str(action.source))
                logs.append(f"Sent to trash: {action.source.name}")
            else:
                review_delete_dir.mkdir(exist_ok=True)
                final_target = unique_destination(review_delete_dir / action.source.name)
                shutil.move(str(action.source), str(final_target))
                applied.append(
                    AppliedAction(
                        kind="delete",
                        original=action.source,
                        current=final_target,
                        reason=action.reason,
                    )
                )
                logs.append(f"Moved to review folder: {action.source.name}")
            continue

        logs.append(f"Unknown action ignored: {action.kind} for {action.source.name}")

    return logs, applied


def undo_actions(applied_actions: list[AppliedAction]) -> list[str]:
    logs: list[str] = []
    for action in reversed(applied_actions):
        if not action.current.exists():
            logs.append(f"Could not undo missing file: {action.current}")
            continue

        if action.kind == "extract":
            if action.current.is_dir():
                shutil.rmtree(action.current)
                logs.append(f"Removed extracted folder: {action.current}")
            else:
                logs.append(f"Could not undo extract safely: {action.current}")
            continue

        action.original.parent.mkdir(parents=True, exist_ok=True)
        restore_target = unique_destination(action.original)
        shutil.move(str(action.current), str(restore_target))
        logs.append(f"Restored: {action.current.name} -> {restore_target}")
    return logs


def safe_extract_archive(source: Path, destination: Path) -> None:
    suffixes = [suffix.lower() for suffix in source.suffixes]
    if source.suffix.lower() == ".zip":
        with zipfile.ZipFile(source) as archive:
            for member in archive.infolist():
                target = safe_extract_target(destination, member.filename)
                if member.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(member) as src, target.open("wb") as dst:
                    shutil.copyfileobj(src, dst)
        return

    if ".tar" in suffixes or source.suffix.lower() in {".tgz", ".tbz2", ".txz"}:
        with tarfile.open(source) as archive:
            for member in archive.getmembers():
                if member.issym() or member.islnk() or member.isdev():
                    raise ValueError(f"Unsafe archive member: {member.name}")
                target = safe_extract_target(destination, member.name)
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                if not member.isfile():
                    continue
                source_file = archive.extractfile(member)
                if source_file is None:
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                with source_file, target.open("wb") as dst:
                    shutil.copyfileobj(source_file, dst)
        return

    raise shutil.ReadError(f"Unsupported archive format: {source.suffix}")


def safe_extract_target(destination: Path, member_name: str) -> Path:
    target = (destination / member_name).resolve(strict=False)
    destination_resolved = destination.resolve(strict=False)
    if target == destination_resolved or destination_resolved in target.parents:
        return target
    raise ValueError(f"Unsafe archive path: {member_name}")
