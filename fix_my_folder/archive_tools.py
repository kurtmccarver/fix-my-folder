from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import shutil
import tarfile
import zipfile

from .actions import safe_extract_archive, safe_category_name, unique_destination
from .organizer import is_private_path

try:
    import pyzipper
except ImportError:  # pragma: no cover - optional at runtime outside packaged app
    pyzipper = None


ArchiveProgress = Callable[[int, int, str], None]


def is_supported_archive(path: Path) -> bool:
    suffix = path.suffix.lower()
    suffixes = "".join(path.suffixes[-2:]).lower()
    return suffix == ".zip" or suffix in {".tar", ".tgz", ".tbz2", ".txz"} or suffixes in {
        ".tar.gz",
        ".tar.bz2",
        ".tar.xz",
    }


def default_extract_destination(source: Path) -> Path:
    return source.parent / safe_category_name(_archive_stem(source))


def extract_archive(
    source: Path,
    destination: Path | None = None,
    *,
    password: str = "",
    progress_callback: ArchiveProgress | None = None,
) -> Path:
    source = source.expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Archive not found: {source}")
    if not is_supported_archive(source):
        raise shutil.ReadError(f"Unsupported archive format: {source.suffix}")

    target_root = unique_destination((destination or default_extract_destination(source)).resolve(strict=False))
    target_root.mkdir(parents=True, exist_ok=True)

    try:
        if source.suffix.lower() == ".zip" and password:
            _extract_password_zip(source, target_root, password, progress_callback)
        else:
            if progress_callback is not None:
                progress_callback(0, 1, f"Extracting {source.name}...")
            safe_extract_archive(source, target_root)
            if progress_callback is not None:
                progress_callback(1, 1, f"Extracted {source.name}.")
    except Exception:
        shutil.rmtree(target_root, ignore_errors=True)
        raise

    return target_root


def create_zip(
    sources: list[Path],
    output: Path,
    *,
    password: str = "",
    progress_callback: ArchiveProgress | None = None,
) -> Path:
    resolved_sources = [path.expanduser().resolve() for path in sources]
    output = output.expanduser().resolve()
    if output.suffix.lower() != ".zip":
        output = output.with_suffix(".zip")
    output.parent.mkdir(parents=True, exist_ok=True)
    output = unique_destination(output)
    files = _collect_zip_files(resolved_sources, exclude=output)
    if not files:
        raise ValueError("Choose at least one file or a folder containing files.")

    if password:
        if pyzipper is None:
            raise RuntimeError("Encrypted ZIP support is not available in this build.")
        with pyzipper.AESZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, encryption=pyzipper.WZ_AES) as archive:
            archive.setpassword(password.encode("utf-8"))
            _write_zip_members(archive, files, progress_callback)
    else:
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            _write_zip_members(archive, files, progress_callback)

    return output


def _extract_password_zip(
    source: Path,
    destination: Path,
    password: str,
    progress_callback: ArchiveProgress | None,
) -> None:
    password_bytes = password.encode("utf-8")
    archive_class = pyzipper.AESZipFile if pyzipper is not None else zipfile.ZipFile
    with archive_class(source) as archive:
        archive.setpassword(password_bytes)
        members = archive.infolist()
        total = max(len(members), 1)
        for index, member in enumerate(members, start=1):
            from .actions import safe_extract_target

            target = safe_extract_target(destination, member.filename)
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(member, pwd=password_bytes) as src, target.open("wb") as dst:
                    shutil.copyfileobj(src, dst)
            if progress_callback is not None:
                progress_callback(index, total, f"Extracted {index} of {total} item(s).")


def _collect_zip_files(sources: list[Path], *, exclude: Path) -> list[tuple[Path, str]]:
    members: list[tuple[Path, str]] = []
    for source in sources:
        if source.is_symlink() or not source.exists() or is_private_path(source):
            continue
        if source.is_file():
            if source != exclude:
                members.append((source, source.name))
            continue
        if source.is_dir():
            base_name = safe_category_name(source.name)
            for path in source.rglob("*"):
                if path == exclude or path.is_symlink() or not path.is_file() or is_private_path(path):
                    continue
                arcname = str(Path(base_name) / path.relative_to(source))
                members.append((path, arcname))
    return members


def _write_zip_members(archive, files: list[tuple[Path, str]], progress_callback: ArchiveProgress | None) -> None:
    total = max(len(files), 1)
    for index, (path, arcname) in enumerate(files, start=1):
        archive.write(path, arcname)
        if progress_callback is not None:
            progress_callback(index, total, f"Added {index} of {total} file(s).")


def _archive_stem(path: Path) -> str:
    name = path.name
    for suffix in (".tar.gz", ".tar.bz2", ".tar.xz"):
        if name.lower().endswith(suffix):
            return name[: -len(suffix)]
    return path.stem
