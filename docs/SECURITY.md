# Security

Fix My Folder is designed as a local-first desktop app.

## Local Processing

- Sorting is handled locally with extension and metadata rules.
- File contents are not sent to remote services by this app.
- Duplicate detection hashes files locally and only when files have matching sizes.

## Private File Protection

By default, the scanner skips:

- Hidden files and hidden folders.
- Windows system files.
- Symlinks.
- Common secret files such as `.env`, `.npmrc`, `.pypirc`, SSH keys, and certificate/key files.
- Internal/review folders such as `Files To Review Before Deleting`.

These files are intentionally excluded from scan plans.

## Safer File Operations

- The app previews actions before applying them.
- Apply Plan shows a detailed Proceed or Cancel confirmation.
- Archive extraction rejects unsafe archive paths that try to write outside the extraction folder.
- Encrypted ZIP creation requires a password of at least 8 characters in the GUI.
- Cleanup delete suggestions move files to a visible review folder by default.
- Permanent deletion is available only when the user selects it.
- Apply-time checks skip symlinks and unsafe non-file sources.
- External commands are called with argument lists instead of shell-built command strings.

## Distribution Note

If this repository is public, people can technically clone or copy the code. The `LICENSE` file states that copying, redistribution, and derivative works are not allowed without permission, but legal terms cannot technically prevent copying. For stronger control, publish only compiled releases and keep the source repository private.

## Reporting Security Issues

Do not open a public issue for sensitive vulnerabilities. Contact the maintainer privately.
