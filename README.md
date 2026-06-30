# Fix My Folder

A local Python desktop app that scans a folder, categorizes files quickly, builds a safe action plan, and then moves, cleans, or extracts files only after you review the plan.

The app is designed to be cautious:

- Actions are previewed before anything changes.
- Apply Plan shows a detailed confirmation with Proceed and Cancel.
- Cleanup delete suggestions are moved into a visible review folder by default.
- Permanent deletion is optional and must be selected by the user.
- Sorting uses fast local rules based on file extensions and metadata.
- ZIP tools can create normal ZIPs, create password-protected ZIPs, and extract supported archives.

## Requirements

- Python 3.10+
- Optional: `send2trash` for native trash support in development

Install optional dependencies:

```powershell
pip install -r requirements.txt
```

## Run The App

```powershell
python app.py
```

The app shows scan progress while it works. You can choose a folder, select specific files, cancel an active scan, remove individual suggestions from the plan, apply the plan, and undo the most recently applied plan.

The GUI includes:

- A blue-focused minimalist layout for source, plan settings, progress, and review results.
- A first-run onboarding wizard with Back, Next, Skip, and Finish controls.
- Animated progress while the app is finding files.
- Percentage progress once the scan knows how many files it needs to process.
- Automatic scanning after you choose a folder or files.
- Sorting filters for file type, exact file format, modified year, and modified month.
- Extract mode for ZIP and TAR-based archive files.
- A separate Zip Tools tab for creating ZIP files, encrypted ZIP files, and extracting/unzipping archives.
- Remove From Folder mode for moving files outside the selected folder.
- Cleanup delete handling can be toggled between a review folder and permanent deletion.
- Footer links for FAQ, How It Works, Privacy Policy, Terms, and Ko-fi support.

Scans are optimized for speed:

- Common file types are categorized instantly by local rules.
- Raw photo formats such as CR2, CR3, NEF, ARW, RAF, ORF, RW2, DNG, and others are treated as images.
- Duplicate detection hashes only files that have matching file sizes.
- Progress updates are throttled so large folders do not overwhelm the GUI.
- Hidden, system, symlink, and private-looking files are skipped by default.

In the GUI, the modes are:

- `Organize`: move files into category folders such as Documents, Images, Videos, Code, and Other.
- `Cleanup`: find empty files and duplicate copies, then suggest safe delete actions.
- `Extract`: find ZIP and TAR archives, then extract each one into its own folder.
- `Remove From Folder`: move files outside the selected folder into its parent folder.
- `Full`: organize files and run cleanup checks in one scan.

Sorting filters:

- `Type`: sort into folders such as Images, Documents, Videos, Code, and Audio.
- `File Format`: sort into folders such as JPG, PDF, DOCX, ZIP, and No Extension.
- `Modified Year`: sort by the year each file was last changed.
- `Modified Month`: sort by year and month.

## Install On Windows

For normal users, download `FixMyFolderSetup.exe` from the GitHub release or workflow artifact. Run it once, then open Fix My Folder from the Start Menu whenever you need it. The installer can also create a desktop shortcut.

The installer adds:

- Start Menu shortcut.
- Optional desktop shortcut.
- Built-in uninstaller in Windows Apps settings.
- Right-click menu entry for ZIP files: `Extract with Fix My Folder`.
- Local copies of the README, license, privacy policy, terms, and security notes.

You can also use the portable app without installing by downloading `fixmyfolder-portable.exe` and double-clicking it. The portable app does not add File Explorer right-click actions; use the installer for that.

## Build The App

Build a double-clickable Windows app:

```powershell
.\build_exe.ps1
```

The build script generates `assets\logo.ico` from `assets\logo.png`, embeds it as the Windows app icon, bundles the logo for in-app branding, and copies the final EXE into the project root.

The visible executable will be created here:

```powershell
fixmyfolder-portable.exe
```

Build a Windows installer:

```powershell
.\build_installer.ps1
```

This creates:

```powershell
FixMyFolderSetup.exe
installer\FixMyFolderSetup.exe
```

`build_installer.ps1` requires Inno Setup 6. If it is missing, install it with:

```powershell
winget install JRSoftware.InnoSetup
```

When this project is on GitHub, the included GitHub Actions workflow can build the EXE and installer automatically. Go to the repository's **Actions** tab, run **Build Windows App**, then download either `FixMyFolder-Windows-Installer` or `FixMyFolder-Windows`.

To publish a release with the EXE attached, push a version tag:

```powershell
git tag v0.1.0
git push origin v0.1.0
```

The workflow will attach both `FixMyFolderSetup.exe` and `fixmyfolder-portable.exe` to that GitHub release.

## CLI Usage

Preview a plan:

```powershell
python -m fix_my_folder "C:\Path\To\Folder" --mode organize
```

Preview selected files:

```powershell
python -m fix_my_folder "C:\Path\file1.txt" "C:\Path\photo.jpg" --mode organize
```

Apply the plan:

```powershell
python -m fix_my_folder "C:\Path\To\Folder" --mode organize --apply
```

Other modes:

```powershell
python -m fix_my_folder "C:\Path\To\Folder" --mode cleanup
python -m fix_my_folder "C:\Path\To\Folder" --mode extract
python -m fix_my_folder "C:\Path\To\Folder" --mode remove-from-folder
python -m fix_my_folder "C:\Path\To\Folder" --mode full --apply
```

Permanent cleanup deletion in the CLI must be selected explicitly:

```powershell
python -m fix_my_folder "C:\Path\To\Folder" --mode cleanup --delete-mode permanent --apply
```

## Remove From Folder

Use `Remove From Folder` mode when you want to pull files out of a folder without deleting them. For a selected folder such as:

```powershell
C:\Users\You\Downloads\OldFolder
```

planned files move to:

```powershell
C:\Users\You\Downloads
```

The app previews every move first, avoids hidden/private-looking files, and Undo can move the files back after applying the latest plan.

## Cleanup Delete Handling

Cleanup mode does not permanently delete files by default. It moves cleanup suggestions into:

```powershell
Files To Review Before Deleting
```

You can inspect that folder and manually delete the files later. In the GUI, `Cleanup Deletes` can be changed to `Delete Permanently`, but permanent deletion cannot be undone by the app.

## Extract Archives

Use `Extract` mode to find archive files inside the selected folder or selected files. The app previews each extraction first, then extracts into:

```powershell
Extracted\<ArchiveName>
```

Supported archive formats are ZIP, TAR, TAR.GZ, TGZ, TAR.BZ2, TBZ2, TAR.XZ, and TXZ. RAR and 7Z are not extracted because this app does not bundle extra archive engines for those formats.

Archive extraction is guarded against unsafe paths that try to write outside the extraction folder.

## Zip Tools

The `Zip Tools` tab can:

- Create a ZIP from selected files.
- Create a ZIP from selected folders.
- Create an encrypted ZIP when `Encrypt With Password` is enabled.
- Extract or unzip ZIP and TAR-based archives.

Installed copies also add a Windows File Explorer right-click action for `.zip` files:

```text
Extract with Fix My Folder
```

That action extracts the ZIP into a folder beside the archive and shows a completion message.

## FAQ

If the app is not working on Windows, check whether Windows Security blocked it. In Windows Security, review App & browser control, Reputation-based protection, and Controlled Folder Access under Ransomware protection. If Controlled Folder Access is enabled, allow `FixMyFolder.exe` for the installed app or `fixmyfolder-portable.exe` for the portable app, or choose a folder that Windows is not protecting.

Sorting is handled locally by file extension and metadata. If a file is uncommon or unknown, it is placed into `Other`; use `File Format` sorting if you want each extension separated into its own folder.

## Support The Project

The `Support the Project` button opens the Ko-fi page in your browser:

```text
https://ko-fi.com/H1D321ZGN8
```

## Privacy And Terms

See [docs/PRIVACY.md](docs/PRIVACY.md) and [docs/TERMS.md](docs/TERMS.md). The app also includes Privacy Policy, Terms, FAQ, and onboarding screens in the GUI.

Use the app responsibly. The developer is not liable if files are missing, moved, deleted, overwritten, or otherwise changed accidentally.

## Security And Copying

See [docs/SECURITY.md](docs/SECURITY.md). The app skips hidden/system/private-looking files by default and keeps sorting local.

This project uses an all-rights-reserved [LICENSE](LICENSE). If you publish the source code publicly on GitHub, people can still technically clone or copy it; the license gives you legal protection, not technical copy prevention. To make copying harder, keep the source private and publish only release builds.
