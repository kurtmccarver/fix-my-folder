ONBOARDING_STEPS = [
    (
        "Welcome",
        "Fix My Folder helps organize and clean files while keeping you in control. "
        "It creates a reviewable plan first, then changes files only after you apply it.",
    ),
    (
        "Choose A Source",
        "Choose a whole folder or select specific files. The app skips hidden, system, "
        "symlink, and private-looking files by default.",
    ),
    (
        "Fast Local Rules",
        "The app categorizes files using file extensions and file metadata on your computer. "
        "It does not need an online account, paid service, or extra download.",
    ),
    (
        "Review Before Applying",
        "Scan builds a suggested plan. Remove anything you do not want, then click Apply Plan. "
        "You will see a confirmation with the exact planned actions before anything changes.",
    ),
    (
        "Flexible Sorting",
        "Choose whether to organize by file type, exact file format, modified year, or modified month.",
    ),
]


ONBOARDING_TEXT = """Welcome to Fix My Folder.

What it does:
- Scans a folder you choose.
- Can scan specific files you choose instead of a full folder.
- Builds a suggested plan before changing anything.
- Organizes files into categories.
- Can sort by type, file format, modified year, or modified month.
- Finds empty files and duplicate copies in Cleanup or Full mode.
- Extracts ZIP and TAR-based archive files in Extract mode.
- Creates normal ZIP files and encrypted ZIP files in Zip Tools.
- Can remove files from a folder by moving them outside into the parent folder.
- Cleanup files are moved to a visible review folder by default instead of being deleted immediately.
- Lets you remove suggestions, apply the plan, cancel scans, and undo the most recent applied plan.

How sorting works:
- The app uses local file rules based on extensions and file metadata.
- Common image, raw photo, document, video, audio, archive, code, app, and data formats are recognized.
- It skips hidden, system, symlink, and private-looking files by default.
- It does not upload files or file details.

Recommended workflow:
1. Choose a folder or select files.
2. Pick a mode.
3. Pick a sort filter if you are organizing files.
4. Review the automatically generated plan.
5. Remove anything you do not want.
6. Click Apply Plan.
7. Read the confirmation carefully, then choose Proceed or Cancel.
8. Use Undo if you need to reverse the latest applied plan.
"""

PRIVACY_POLICY_TEXT = """Privacy Policy

Fix My Folder is designed as a local-first desktop app.

Information processed:
- Folder paths you choose.
- File names, file extensions, file sizes, modified dates, and file hashes for duplicate detection.
- File contents are not uploaded by this app.
- Hidden, system, symlink, and private-looking files are skipped by default.

Local processing:
- Sorting is handled by local rules on your computer.
- The app does not call cloud services to categorize files.
- The app does not create an account, collect analytics, or sell personal information.

File changes:
- The app previews suggested changes before applying them.
- Apply Plan shows a confirmation with the exact planned actions.
- By default, cleanup delete suggestions move files into a visible Files To Review Before Deleting folder.
- You can choose permanent deletion, but permanent deletion cannot be undone by the app.
- Remove From Folder mode moves files outside the selected folder; it does not delete them.

Data storage:
- The app may store a small local setting to remember that onboarding has been shown.
- The Support the Project button opens Ko-fi in your web browser. Ko-fi is an external site with its own privacy practices.

User responsibility:
- Review the plan before applying it.
- Keep backups of important folders.

This policy is a plain-language project template and should be reviewed before commercial distribution.
"""

TERMS_TEXT = """Terms and Conditions

By using Fix My Folder, you agree to use it responsibly and review suggested file actions before applying them.

Purpose:
- Fix My Folder helps categorize, move, extract, and clean files in folders selected by the user.
- The app is a productivity tool and does not guarantee perfect categorization.

No warranty:
- The software is provided as-is.
- The developer does not guarantee that suggestions are accurate or suitable for every folder.

File safety:
- Always review the action plan before applying it.
- Keep backups of important data.
- Apply Plan shows a confirmation before file changes are made.
- Undo is provided for the most recently applied GUI plan, but it may not be able to restore files if they are moved, edited, or deleted outside the app afterward.

Liability:
- To the fullest extent allowed by law, the developer is not responsible for data loss, business interruption, or other damages caused by use of the app.
- The developer is not liable if files are missing, moved, deleted, overwritten, or otherwise changed accidentally.
- Use the app responsibly, review every plan before applying it, and keep backups of important files.

Distribution:
- If you publish or redistribute this app, review these terms and replace them with terms appropriate for your project and jurisdiction.

Source code copying:
- Unless a separate license says otherwise, this project is all rights reserved.
- Public source code can still be technically copied; the license defines what is legally allowed.
"""

FAQ_TEXT = """Frequently Asked Questions

What should I check if the app is not working?
- Restart the app first.
- Make sure the folder is not protected by Windows permissions.
- If Windows Security blocks the EXE, open Windows Security > App & browser control > Reputation-based protection, then review blocked app messages.
- If Controlled Folder Access is on, open Windows Security > Virus & threat protection > Ransomware protection, then allow FixMyFolder.exe for the installed app or fixmyfolder-portable.exe for the portable app.
- If SmartScreen asks about the app, choose More info only if you trust the copy you downloaded.

Does the app need an online service?
- No. Sorting uses local file rules on your computer.
- Cleanup, Extract, Remove From Folder, File Format sorting, and Date sorting are all local.

Why did a file go into Other?
- The app puts unknown or uncommon extensions into Other so it does not guess too aggressively.
- Use File Format sorting if you want every extension separated into its own folder.

What can extraction do?
- Extract mode finds supported archives in your selected folder or selected files.
- Zip Tools can extract a chosen archive directly.
- It supports ZIP and TAR-based archives such as TAR, TAR.GZ, TGZ, TAR.BZ2, TBZ2, TAR.XZ, and TXZ.
- RAR and 7Z are not extracted because Windows/Python do not include safe built-in support for them.

What can Zip Tools do?
- Create ZIP files from selected files or folders.
- Create encrypted ZIP files with a password.
- Extract or unzip supported archive files.
- Installed copies add Extract with Fix My Folder to the File Explorer right-click menu for ZIP files.

Can Undo reverse extraction?
- Yes. For Extract mode, Undo removes the extracted folder created by the latest applied plan.
"""
