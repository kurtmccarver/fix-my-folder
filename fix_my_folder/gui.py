from __future__ import annotations

from pathlib import Path
import json
import sys
import queue
import threading
import webbrowser
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .actions import Action, AppliedAction, apply_actions, undo_actions
from .archive_tools import create_zip, default_extract_destination, extract_archive
from .content import FAQ_TEXT, ONBOARDING_STEPS, ONBOARDING_TEXT, PRIVACY_POLICY_TEXT, TERMS_TEXT
from .organizer import ScanCancelled, build_plan, build_plan_for_paths


MODE_LABELS = {
    "Organize": "Move files into category folders such as Documents, Images, Videos, Code, and Other.",
    "Cleanup": "Find empty files and duplicate copies, then suggest safe delete actions.",
    "Extract": "Find ZIP and TAR archives, then extract each one into its own folder.",
    "Remove From Folder": "Move files outside the selected folder into its parent folder.",
    "Full": "Organize files and run cleanup checks in one scan.",
}

MODE_VALUES = {
    "Organize": "organize",
    "Cleanup": "cleanup",
    "Extract": "extract",
    "Remove From Folder": "remove_from_folder",
    "Full": "full",
}
SORT_LABELS = {
    "Type": "Sort into Documents, Images, Videos, Code, and other file-type folders.",
    "File Format": "Sort by extension, such as JPG, PDF, DOCX, ZIP, or No Extension.",
    "Modified Year": "Sort by the year each file was last changed.",
    "Modified Month": "Sort by year and month, such as 2026-06.",
}
SORT_VALUES = {
    "Type": "type",
    "File Format": "extension",
    "Modified Year": "modified_year",
    "Modified Month": "modified_month",
}
DELETE_LABELS = {
    "Move To Review Folder": "Move cleanup files into a visible folder first so you can manually delete them later.",
    "Delete Permanently": "Permanently delete cleanup files. This cannot be undone by the app.",
}
DELETE_VALUES = {
    "Move To Review Folder": "review_folder",
    "Delete Permanently": "permanent",
}
SETTINGS_PATH = Path.home() / ".fix_my_folder" / "settings.json"
KOFI_URL = "https://ko-fi.com/H1D321ZGN8"


def resource_path(name: str) -> Path:
    base_path = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    direct_path = base_path / name
    if direct_path.exists():
        return direct_path
    return base_path / "assets" / name


class FolderApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Fix My Folder")
        self.geometry("1060x720")
        self.minsize(900, 600)

        self.folder = tk.StringVar()
        self.selected_files: list[Path] = []
        self.action_root: Path | None = None
        self.mode = tk.StringVar(value="Organize")
        self.organize_by = tk.StringVar(value="Type")
        self.delete_handling = tk.StringVar(value="Move To Review Folder")
        self.mode_description = tk.StringVar(value=MODE_LABELS["Organize"])
        self.sort_description = tk.StringVar(value=SORT_LABELS["Type"])
        self.delete_description = tk.StringVar(value=DELETE_LABELS["Move To Review Folder"])
        self.status = tk.StringVar(value="Choose a folder or select files to begin.")
        self.progress_text = tk.StringVar(value="Idle")
        self.progress = tk.IntVar(value=0)
        self.progress_busy = False
        self.plan: list[Action] = []
        self.undo_stack: list[AppliedAction] = []
        self.archive_sources: list[Path] = []
        self.archive_file = tk.StringVar()
        self.archive_destination = tk.StringVar()
        self.archive_output = tk.StringVar()
        self.archive_password = tk.StringVar()
        self.archive_encrypt = tk.BooleanVar(value=False)
        self.archive_status = tk.StringVar(value="Choose files, folders, or an archive.")
        self.archive_progress = tk.IntVar(value=0)
        self.archive_running = False
        self.archive_busy = False
        self.scan_cancel_event: threading.Event | None = None
        self.scan_running = False
        self.worker_queue: queue.Queue[tuple[str, object]] = queue.Queue()
        self.logo_image: tk.PhotoImage | None = None

        self._configure_style()
        self._load_branding()
        self._build_ui()
        self.after(100, self._poll_worker)
        self.after(300, self._show_onboarding_once)

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        self.configure(bg="#edf6ff")
        style.configure(".", font=("Segoe UI", 10))
        style.configure("TFrame", background="#edf6ff")
        style.configure("TLabel", background="#edf6ff", foreground="#06285f")
        style.configure("App.TFrame", background="#edf6ff")
        style.configure("Card.TFrame", background="#f7fbff", relief="flat")
        style.configure("Header.TLabel", background="#edf6ff", foreground="#06285f", font=("Segoe UI", 18, "bold"))
        style.configure("Subtle.TLabel", background="#edf6ff", foreground="#365f91")
        style.configure("CardTitle.TLabel", background="#f7fbff", foreground="#06285f", font=("Segoe UI", 11, "bold"))
        style.configure("CardText.TLabel", background="#f7fbff", foreground="#284c7c")
        style.configure("Status.TLabel", background="#edf6ff", foreground="#284c7c")
        style.configure("Link.TLabel", background="#edf6ff", foreground="#0b63ce")
        style.configure("TButton", background="#d8ecff", foreground="#06285f", bordercolor="#8fbff0", focusthickness=0, padding=(10, 6))
        style.map("TButton", background=[("active", "#c6e2ff"), ("disabled", "#e7f2ff")], foreground=[("disabled", "#7fa6d3")])
        style.configure("Accent.TButton", background="#b9dcff", foreground="#06285f", font=("Segoe UI", 10, "bold"))
        style.map("Accent.TButton", background=[("active", "#a7d2ff"), ("disabled", "#e7f2ff")])
        style.configure("TCombobox", fieldbackground="#f7fbff", background="#d8ecff", foreground="#06285f", arrowcolor="#06285f")
        style.configure("TEntry", fieldbackground="#f7fbff", foreground="#06285f", bordercolor="#8fbff0")
        style.configure("Horizontal.TProgressbar", troughcolor="#d8ecff", background="#1f7eea", bordercolor="#8fbff0", lightcolor="#1f7eea", darkcolor="#1f7eea")
        style.configure("Treeview", rowheight=28, font=("Segoe UI", 9), background="#f7fbff", fieldbackground="#f7fbff", foreground="#06285f", bordercolor="#8fbff0")
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"), background="#d8ecff", foreground="#06285f")

    def _load_branding(self) -> None:
        logo_path = resource_path("logo.png")
        if not logo_path.exists():
            return
        try:
            self.logo_image = tk.PhotoImage(file=str(logo_path)).subsample(20, 20)
            self.iconphoto(True, self.logo_image)
        except tk.TclError:
            self.logo_image = None

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=12, style="App.TFrame")
        root.pack(fill=tk.BOTH, expand=True)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(1, weight=1)

        header = ttk.Frame(root, style="App.TFrame")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        header.columnconfigure(1, weight=1)
        if self.logo_image is not None:
            ttk.Label(header, image=self.logo_image, style="Subtle.TLabel").grid(row=0, column=0, rowspan=2, sticky="w", padx=(0, 10))
        ttk.Label(header, text="Fix My Folder", style="Header.TLabel").grid(row=0, column=1, sticky="w")
        ttk.Label(
            header,
            text="Preview, organize, and clean files with local rules.",
            style="Subtle.TLabel",
        ).grid(row=1, column=1, sticky="w")

        self.tabs = ttk.Notebook(root)
        self.tabs.grid(row=1, column=0, sticky="nsew")
        organize_tab = ttk.Frame(self.tabs, padding=0, style="App.TFrame")
        archive_tab = ttk.Frame(self.tabs, padding=0, style="App.TFrame")
        self.tabs.add(organize_tab, text="Organize")
        self.tabs.add(archive_tab, text="Zip Tools")
        organize_tab.columnconfigure(0, weight=1)
        organize_tab.rowconfigure(2, weight=1)
        archive_tab.columnconfigure(0, weight=1)
        archive_tab.rowconfigure(2, weight=1)

        source_card = ttk.Frame(organize_tab, padding=12, style="Card.TFrame")
        source_card.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        source_card.columnconfigure(1, weight=1)
        ttk.Label(source_card, text="Source", style="CardTitle.TLabel").grid(row=0, column=0, sticky="w", columnspan=4)
        ttk.Label(
            source_card,
            text="Choose a folder to scan its contents, or select only the files you want to process.",
            style="CardText.TLabel",
        ).grid(row=1, column=0, sticky="w", columnspan=4, pady=(2, 10))
        ttk.Entry(source_card, textvariable=self.folder).grid(row=2, column=0, columnspan=2, sticky="ew")
        ttk.Button(source_card, text="Choose Folder", command=self._browse_folder, width=16).grid(row=2, column=2, padx=(10, 0))
        ttk.Button(source_card, text="Select Files", command=self._browse_files, width=16).grid(row=2, column=3, padx=(8, 0))

        controls = ttk.Frame(organize_tab, padding=12, style="Card.TFrame")
        controls.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        controls.columnconfigure(9, weight=1)

        ttk.Label(controls, text="Plan Settings", style="CardTitle.TLabel").grid(row=0, column=0, sticky="w", columnspan=10)
        ttk.Label(controls, text="Mode", style="CardText.TLabel").grid(row=1, column=0, padx=(0, 8), pady=(12, 0))
        self.mode_box = ttk.Combobox(
            controls,
            textvariable=self.mode,
            values=tuple(MODE_LABELS),
            state="readonly",
            width=22,
        )
        self.mode_box.grid(row=1, column=1, padx=(0, 16), pady=(12, 0))
        self.mode_box.bind("<<ComboboxSelected>>", self._mode_changed)

        ttk.Label(controls, text="Sort By", style="CardText.TLabel").grid(row=1, column=2, padx=(0, 8), pady=(12, 0))
        self.sort_box = ttk.Combobox(
            controls,
            textvariable=self.organize_by,
            values=tuple(SORT_LABELS),
            state="readonly",
            width=16,
        )
        self.sort_box.grid(row=1, column=3, padx=(0, 16), pady=(12, 0))
        self.sort_box.bind("<<ComboboxSelected>>", self._sort_changed)

        self.scan_button = ttk.Button(controls, text="Scan", command=self._scan_or_cancel, style="Accent.TButton", width=14)
        self.scan_button.grid(row=1, column=4, padx=(0, 8), pady=(12, 0))
        self.apply_button = ttk.Button(controls, text="Apply Plan", command=self._apply, width=14)
        self.apply_button.grid(row=1, column=5, padx=(0, 8), sticky="w", pady=(12, 0))
        self.undo_button = ttk.Button(controls, text="Undo", command=self._undo, state=tk.DISABLED, width=14)
        self.undo_button.grid(row=1, column=6, sticky="w", pady=(12, 0))
        ttk.Label(controls, text="Cleanup Deletes", style="CardText.TLabel").grid(row=2, column=0, padx=(0, 8), pady=(10, 0), sticky="w")
        self.delete_box = ttk.Combobox(
            controls,
            textvariable=self.delete_handling,
            values=tuple(DELETE_LABELS),
            state="readonly",
            width=24,
        )
        self.delete_box.grid(row=2, column=1, padx=(0, 16), pady=(10, 0), sticky="w")
        self.delete_box.bind("<<ComboboxSelected>>", self._delete_handling_changed)
        ttk.Label(controls, textvariable=self.mode_description, style="CardText.TLabel").grid(
            row=3,
            column=0,
            columnspan=10,
            sticky="w",
            pady=(10, 0),
        )
        ttk.Label(controls, textvariable=self.sort_description, style="CardText.TLabel").grid(
            row=4,
            column=0,
            columnspan=10,
            sticky="w",
            pady=(4, 0),
        )
        ttk.Label(controls, textvariable=self.delete_description, style="CardText.TLabel").grid(
            row=5,
            column=0,
            columnspan=10,
            sticky="w",
            pady=(4, 0),
        )

        table_frame = ttk.Frame(organize_tab, style="App.TFrame")
        table_frame.grid(row=2, column=0, sticky="nsew")
        table_frame.rowconfigure(2, weight=1)
        table_frame.columnconfigure(0, weight=1)
        top_results = ttk.Frame(table_frame)
        top_results.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        top_results.columnconfigure(0, weight=1)
        ttk.Label(top_results, text="Review Plan", style="Subtle.TLabel").grid(row=0, column=0, sticky="w")
        self.remove_button = ttk.Button(top_results, text="Remove Selected From Plan", command=self._remove_selected, width=24)
        self.remove_button.grid(row=0, column=1, sticky="e")

        progress_row = ttk.Frame(table_frame)
        progress_row.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        progress_row.columnconfigure(0, weight=1)
        ttk.Label(progress_row, textvariable=self.progress_text).grid(row=0, column=0, sticky="w", pady=(0, 4))
        self.progress_bar = ttk.Progressbar(progress_row, variable=self.progress, maximum=100)
        self.progress_bar.grid(row=1, column=0, sticky="ew")

        columns = ("action", "file", "target", "reason")
        self.table = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="extended")
        self.table.heading("action", text="Action")
        self.table.heading("file", text="File")
        self.table.heading("target", text="Target")
        self.table.heading("reason", text="Reason")
        self.table.column("action", width=90, stretch=False)
        self.table.column("file", width=260)
        self.table.column("target", width=240)
        self.table.column("reason", width=340)
        self.table.grid(row=2, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.table.yview)
        scrollbar.grid(row=2, column=1, sticky="ns")
        self.table.configure(yscrollcommand=scrollbar.set)

        footer = ttk.Frame(root, style="App.TFrame")
        footer.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        footer.columnconfigure(0, weight=1)
        ttk.Label(footer, textvariable=self.status, style="Status.TLabel").grid(row=0, column=0, sticky="w")
        faq_link = ttk.Label(footer, text="FAQ", cursor="hand2", style="Link.TLabel")
        faq_link.grid(row=0, column=1, sticky="e", padx=(12, 8))
        faq_link.bind("<Button-1>", lambda _event: self._show_faq())
        how_link = ttk.Label(footer, text="How It Works", cursor="hand2", style="Link.TLabel")
        how_link.grid(row=0, column=2, sticky="e", padx=(0, 8))
        how_link.bind("<Button-1>", lambda _event: self._show_onboarding())
        privacy_link = ttk.Label(footer, text="Privacy Policy", cursor="hand2", style="Link.TLabel")
        privacy_link.grid(row=0, column=3, sticky="e", padx=(0, 8))
        privacy_link.bind("<Button-1>", lambda _event: self._show_privacy())
        terms_link = ttk.Label(footer, text="Terms", cursor="hand2", style="Link.TLabel")
        terms_link.grid(row=0, column=4, sticky="e", padx=(0, 8))
        terms_link.bind("<Button-1>", lambda _event: self._show_terms())
        ttk.Button(
            footer,
            text="Support the Project",
            command=self._open_support,
            style="Accent.TButton",
            width=20,
        ).grid(row=0, column=5, sticky="e")

        self._build_archive_tab(archive_tab)

    def _build_archive_tab(self, parent: ttk.Frame) -> None:
        zip_card = ttk.Frame(parent, padding=12, style="Card.TFrame")
        zip_card.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        zip_card.columnconfigure(1, weight=1)
        ttk.Label(zip_card, text="Create Zip", style="CardTitle.TLabel").grid(row=0, column=0, columnspan=4, sticky="w")
        ttk.Label(
            zip_card,
            text="Select files or folders, choose where to save the ZIP, and optionally protect it with a password.",
            style="CardText.TLabel",
        ).grid(row=1, column=0, columnspan=4, sticky="w", pady=(2, 10))
        ttk.Entry(zip_card, textvariable=self.archive_output).grid(row=2, column=0, columnspan=2, sticky="ew")
        ttk.Button(zip_card, text="Add Files", command=self._archive_add_files, width=14).grid(row=2, column=2, padx=(10, 0))
        ttk.Button(zip_card, text="Add Folder", command=self._archive_add_folder, width=14).grid(row=2, column=3, padx=(8, 0))
        ttk.Button(zip_card, text="Save Zip As", command=self._archive_choose_output, width=14).grid(row=3, column=2, padx=(10, 0), pady=(8, 0))
        ttk.Button(zip_card, text="Clear Sources", command=self._archive_clear_sources, width=14).grid(row=3, column=3, padx=(8, 0), pady=(8, 0))
        ttk.Checkbutton(zip_card, text="Encrypt With Password", variable=self.archive_encrypt).grid(row=3, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(zip_card, textvariable=self.archive_password, show="*").grid(row=3, column=1, sticky="ew", pady=(8, 0), padx=(8, 0))
        self.zip_button = ttk.Button(zip_card, text="Create Zip", command=self._archive_create_zip, style="Accent.TButton", width=14)
        self.zip_button.grid(row=4, column=3, sticky="e", pady=(10, 0))

        extract_card = ttk.Frame(parent, padding=12, style="Card.TFrame")
        extract_card.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        extract_card.columnconfigure(1, weight=1)
        ttk.Label(extract_card, text="Extract Or Unzip", style="CardTitle.TLabel").grid(row=0, column=0, columnspan=4, sticky="w")
        ttk.Label(
            extract_card,
            text="Choose a ZIP or TAR archive, then extract it into a safe folder.",
            style="CardText.TLabel",
        ).grid(row=1, column=0, columnspan=4, sticky="w", pady=(2, 10))
        ttk.Label(extract_card, text="Archive", style="CardText.TLabel").grid(row=2, column=0, sticky="w", padx=(0, 8))
        ttk.Entry(extract_card, textvariable=self.archive_file).grid(row=2, column=1, sticky="ew")
        ttk.Button(extract_card, text="Choose Archive", command=self._archive_choose_file, width=16).grid(row=2, column=2, padx=(10, 0))
        ttk.Label(extract_card, text="Destination", style="CardText.TLabel").grid(row=3, column=0, sticky="w", padx=(0, 8), pady=(8, 0))
        ttk.Entry(extract_card, textvariable=self.archive_destination).grid(row=3, column=1, sticky="ew", pady=(8, 0))
        ttk.Button(extract_card, text="Choose Folder", command=self._archive_choose_destination, width=16).grid(row=3, column=2, padx=(10, 0), pady=(8, 0))
        self.extract_button = ttk.Button(extract_card, text="Extract", command=self._archive_extract, style="Accent.TButton", width=14)
        self.extract_button.grid(row=4, column=2, sticky="e", pady=(10, 0))

        archive_results = ttk.Frame(parent, style="App.TFrame")
        archive_results.grid(row=2, column=0, sticky="nsew")
        archive_results.rowconfigure(2, weight=1)
        archive_results.columnconfigure(0, weight=1)
        ttk.Label(archive_results, textvariable=self.archive_status, style="Status.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 6))
        self.archive_progress_bar = ttk.Progressbar(archive_results, variable=self.archive_progress, maximum=100)
        self.archive_progress_bar.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self.archive_list = tk.Listbox(
            archive_results,
            background="#f7fbff",
            foreground="#06285f",
            selectbackground="#b9dcff",
            selectforeground="#06285f",
        )
        self.archive_list.grid(row=2, column=0, sticky="nsew")
        list_scroll = ttk.Scrollbar(archive_results, orient=tk.VERTICAL, command=self.archive_list.yview)
        list_scroll.grid(row=2, column=1, sticky="ns")
        self.archive_list.configure(yscrollcommand=list_scroll.set)

    def _archive_add_files(self) -> None:
        selected = filedialog.askopenfilenames(title="Choose files to zip")
        if selected:
            self.archive_sources.extend(Path(path) for path in selected)
            self._render_archive_sources()

    def _archive_add_folder(self) -> None:
        selected = filedialog.askdirectory(title="Choose folder to zip")
        if selected:
            self.archive_sources.append(Path(selected))
            self._render_archive_sources()

    def _archive_clear_sources(self) -> None:
        self.archive_sources = []
        self._render_archive_sources()

    def _archive_choose_output(self) -> None:
        selected = filedialog.asksaveasfilename(
            title="Save ZIP as",
            defaultextension=".zip",
            filetypes=[("ZIP archive", "*.zip")],
        )
        if selected:
            self.archive_output.set(selected)

    def _archive_choose_file(self) -> None:
        selected = filedialog.askopenfilename(
            title="Choose archive",
            filetypes=[
                ("Supported archives", "*.zip *.tar *.tar.gz *.tgz *.tar.bz2 *.tbz2 *.tar.xz *.txz"),
                ("All files", "*.*"),
            ],
        )
        if selected:
            source = Path(selected)
            self.archive_file.set(str(source))
            self.archive_destination.set(str(default_extract_destination(source)))

    def _archive_choose_destination(self) -> None:
        selected = filedialog.askdirectory(title="Choose extraction folder")
        if selected:
            self.archive_destination.set(selected)

    def _render_archive_sources(self) -> None:
        self.archive_list.delete(0, tk.END)
        for source in self.archive_sources:
            self.archive_list.insert(tk.END, str(source))
        self.archive_status.set(f"{len(self.archive_sources)} source item(s) selected for ZIP creation.")

    def _archive_create_zip(self) -> None:
        if self.archive_running:
            return
        if not self.archive_sources:
            messagebox.showerror("No sources", "Add at least one file or folder to zip.")
            return
        if not self.archive_output.get().strip():
            self._archive_choose_output()
            if not self.archive_output.get().strip():
                return
        password = self.archive_password.get() if self.archive_encrypt.get() else ""
        if self.archive_encrypt.get() and not password:
            messagebox.showerror("Password required", "Enter a password before creating an encrypted ZIP.")
            return
        if self.archive_encrypt.get() and len(password) < 8:
            messagebox.showerror("Weak password", "Use at least 8 characters for encrypted ZIP files.")
            return

        self._start_archive_progress("Creating ZIP...")
        thread = threading.Thread(
            target=self._archive_zip_worker,
            args=(list(self.archive_sources), Path(self.archive_output.get()), password),
            daemon=True,
        )
        thread.start()

    def _archive_zip_worker(self, sources: list[Path], output: Path, password: str) -> None:
        try:
            target = create_zip(sources, output, password=password, progress_callback=self._archive_progress_callback)
            self.worker_queue.put(("archive_done", f"Created ZIP:\n{target}"))
        except Exception as exc:
            self.worker_queue.put(("archive_error", str(exc)))

    def _archive_extract(self) -> None:
        if self.archive_running:
            return
        if not self.archive_file.get().strip():
            self._archive_choose_file()
            if not self.archive_file.get().strip():
                return
        destination_text = self.archive_destination.get().strip()
        destination = Path(destination_text) if destination_text else None
        self._start_archive_progress("Extracting archive...")
        thread = threading.Thread(
            target=self._archive_extract_worker,
            args=(Path(self.archive_file.get()), destination, self.archive_password.get()),
            daemon=True,
        )
        thread.start()

    def _archive_extract_worker(self, source: Path, destination: Path | None, password: str) -> None:
        try:
            target = extract_archive(source, destination, password=password, progress_callback=self._archive_progress_callback)
            self.worker_queue.put(("archive_done", f"Extracted archive to:\n{target}"))
        except Exception as exc:
            self.worker_queue.put(("archive_error", str(exc)))

    def _archive_progress_callback(self, done: int, total: int, message: str) -> None:
        percent = int((done / max(total, 1)) * 100)
        self.worker_queue.put(("archive_progress", (max(0, min(percent, 100)), message)))

    def _start_archive_progress(self, message: str) -> None:
        self.archive_running = True
        self.archive_status.set(message)
        self.archive_progress.set(0)
        self.zip_button.configure(state=tk.DISABLED)
        self.extract_button.configure(state=tk.DISABLED)

    def _mode_changed(self, _event: tk.Event | None = None) -> None:
        self.mode_description.set(MODE_LABELS[self.mode.get()])

    def _sort_changed(self, _event: tk.Event | None = None) -> None:
        self.sort_description.set(SORT_LABELS[self.organize_by.get()])

    def _delete_handling_changed(self, _event: tk.Event | None = None) -> None:
        self.delete_description.set(DELETE_LABELS[self.delete_handling.get()])

    def _browse_folder(self) -> None:
        selected = filedialog.askdirectory()
        if selected:
            self.selected_files = []
            self.folder.set(selected)
            self.status.set("Folder selected. Starting scan...")
            self._scan()

    def _browse_files(self) -> None:
        selected = filedialog.askopenfilenames(title="Select files to organize or clean up")
        if selected:
            self.selected_files = [Path(path) for path in selected]
            self.folder.set(f"{len(self.selected_files)} selected file(s)")
            self.status.set("Files selected. Starting scan...")
            self._scan()

    def _scan_or_cancel(self) -> None:
        if self.scan_running:
            self._cancel_scan()
        else:
            self._scan()

    def _scan(self) -> None:
        if self.scan_running:
            return

        selected_files = list(self.selected_files)
        folder = Path(self.folder.get()).expanduser()
        if selected_files:
            source_payload: Path | list[Path] = selected_files
        else:
            if not folder.is_dir():
                messagebox.showerror("Source not found", "Choose an existing folder or select files.")
                return
            source_payload = folder.resolve()

        self._start_busy_progress("Preparing scan...")
        self.scan_running = True
        self.scan_cancel_event = threading.Event()
        self._set_scanning_state(True)
        thread = threading.Thread(
            target=self._scan_worker,
            args=(
                source_payload,
                MODE_VALUES[self.mode.get()],
                SORT_VALUES[self.organize_by.get()],
                self.scan_cancel_event,
            ),
            daemon=True,
        )
        thread.start()

    def _cancel_scan(self) -> None:
        if self.scan_cancel_event is not None:
            self.scan_cancel_event.set()
        self.status.set("Cancelling scan...")
        self.scan_button.configure(state=tk.DISABLED)

    def _scan_worker(
        self,
        source_payload: Path | list[Path],
        mode: str,
        organize_by: str,
        cancel_event: threading.Event,
    ) -> None:
        last_percent = {"value": -1}

        def progress_callback(done: int, total: int, message: str) -> None:
            if done < 0 or total <= 0:
                self.worker_queue.put(("progress_busy", message))
                return
            percent = int((done / max(total, 1)) * 100)
            if percent == last_percent["value"] and done < total:
                return
            last_percent["value"] = percent
            self.worker_queue.put(("progress", (max(0, min(percent, 100)), message)))

        try:
            if isinstance(source_payload, list):
                plan, action_root = build_plan_for_paths(
                    source_payload,
                    mode=mode,
                    organize_by=organize_by,
                    progress_callback=progress_callback,
                    cancel_event=cancel_event,
                )
            else:
                action_root = source_payload
                plan = build_plan(
                    source_payload,
                    mode=mode,
                    organize_by=organize_by,
                    progress_callback=progress_callback,
                    cancel_event=cancel_event,
                )
            self.worker_queue.put(("plan", (plan, action_root)))
        except ScanCancelled:
            self.worker_queue.put(("cancelled", None))
        except Exception as exc:  # pragma: no cover - GUI boundary
            self.worker_queue.put(("error", str(exc)))

    def _poll_worker(self) -> None:
        try:
            kind, payload = self.worker_queue.get_nowait()
        except queue.Empty:
            self.after(100, self._poll_worker)
            return

        if kind == "progress":
            percent, message = payload
            self._set_determinate_progress(int(percent), str(message))
            self.after(100, self._poll_worker)
            return

        if kind == "progress_busy":
            self._start_busy_progress(str(payload))
            self.after(100, self._poll_worker)
            return

        if kind == "archive_progress":
            percent, message = payload
            self.archive_progress.set(int(percent))
            self.archive_status.set(str(message))
            self.after(100, self._poll_worker)
            return

        if kind == "archive_done":
            self.archive_running = False
            self.zip_button.configure(state=tk.NORMAL)
            self.extract_button.configure(state=tk.NORMAL)
            self.archive_progress.set(100)
            self.archive_status.set(str(payload).splitlines()[0])
            messagebox.showinfo("Archive complete", str(payload))
            self.after(100, self._poll_worker)
            return

        if kind == "archive_error":
            self.archive_running = False
            self.zip_button.configure(state=tk.NORMAL)
            self.extract_button.configure(state=tk.NORMAL)
            self.archive_status.set("Archive action failed.")
            messagebox.showerror("Archive failed", str(payload))
            self.after(100, self._poll_worker)
            return

        self.scan_running = False
        self.scan_cancel_event = None
        self._set_scanning_state(False)
        if kind == "plan":
            plan, action_root = payload
            self.plan = list(plan)
            self.action_root = action_root
            self._render_plan()
            self._set_determinate_progress(100, "Scan complete.")
            self.status.set(f"Found {len(self.plan)} suggested action(s). Review before applying.")
        elif kind == "cancelled":
            self._set_determinate_progress(0, "Scan cancelled.")
            self.status.set("Scan cancelled.")
        else:
            messagebox.showerror("Scan failed", str(payload))
            self.status.set("Scan failed.")
        self.after(100, self._poll_worker)

    def _render_plan(self) -> None:
        self.table.delete(*self.table.get_children())
        for index, action in enumerate(self.plan):
            self.table.insert(
                "",
                tk.END,
                iid=str(index),
                values=(
                    action.kind,
                    str(action.source),
                    str(action.target or ""),
                    action.reason,
                ),
            )

    def _remove_selected(self) -> None:
        selected = sorted((int(item) for item in self.table.selection()), reverse=True)
        for index in selected:
            if 0 <= index < len(self.plan):
                self.plan.pop(index)
        self._render_plan()
        self.status.set(f"{len(self.plan)} action(s) remain in the plan.")

    def _apply(self) -> None:
        if not self.plan:
            messagebox.showinfo("No actions", "Scan a folder first, or keep at least one planned action.")
            return

        if not self._confirm_apply_plan():
            return

        action_root = self.action_root or Path.cwd()
        logs, applied = apply_actions(
            self.plan,
            action_root,
            prefer_system_trash=False,
            delete_mode=DELETE_VALUES[self.delete_handling.get()],
        )
        self.undo_stack = applied
        self.plan = []
        self._render_plan()
        self.status.set("Plan applied.")
        self.undo_button.configure(state=tk.NORMAL if self.undo_stack else tk.DISABLED)
        messagebox.showinfo("Done", "\n".join(logs[:25]) + ("\n..." if len(logs) > 25 else ""))

    def _undo(self) -> None:
        if not self.undo_stack:
            messagebox.showinfo("Nothing to undo", "There are no applied actions to undo.")
            return

        logs = undo_actions(self.undo_stack)
        self.undo_stack = []
        self.undo_button.configure(state=tk.DISABLED)
        self.status.set("Last applied plan undone.")
        messagebox.showinfo("Undo complete", "\n".join(logs[:25]) + ("\n..." if len(logs) > 25 else ""))

    def _set_scanning_state(self, scanning: bool) -> None:
        state = tk.DISABLED if scanning else tk.NORMAL
        self.mode_box.configure(state=tk.DISABLED if scanning else "readonly")
        self.sort_box.configure(state=tk.DISABLED if scanning else "readonly")
        self.delete_box.configure(state=tk.DISABLED if scanning else "readonly")
        self.apply_button.configure(state=state)
        self.remove_button.configure(state=state)
        self.scan_button.configure(text="Cancel" if scanning else "Scan", state=tk.NORMAL)

    def _apply_confirmation_text(self) -> str:
        delete_mode = DELETE_VALUES[self.delete_handling.get()]
        move_actions = [action for action in self.plan if action.kind == "move"]
        extract_actions = [action for action in self.plan if action.kind == "extract"]
        delete_actions = [action for action in self.plan if action.kind == "delete"]
        review_deletes = len(delete_actions) if delete_mode == "review_folder" else 0
        permanent_deletes = len(delete_actions) if delete_mode == "permanent" else 0

        lines = [
            f"You are about to apply {len(self.plan)} action(s).",
            "",
            f"Move: {len(move_actions)}",
            f"Extract: {len(extract_actions)}",
            f"Move To Review Folder: {review_deletes}",
            f"Delete Permanently: {permanent_deletes}",
        ]
        if permanent_deletes:
            lines.extend(
                [
                    "",
                    "WARNING: Permanent deletes cannot be undone by this app.",
                ]
            )

        lines.extend(["", "Details:"])
        review_root = (self.action_root or Path.cwd()) / "Files To Review Before Deleting"
        for index, action in enumerate(self.plan, start=1):
            lines.append("")
            lines.append(f"{index}. {action.kind.upper()}")
            lines.append(f"   From: {action.source}")
            if action.kind == "delete":
                if delete_mode == "permanent":
                    lines.append("   To: Permanently deleted")
                else:
                    lines.append(f"   To: {review_root / action.source.name}")
            elif action.target is not None:
                lines.append(f"   To: {action.target}")
            else:
                lines.append("   To: No target")
            lines.append(f"   Reason: {action.reason}")

        lines.extend(["", "Proceed with these exact planned actions?"])
        return "\n".join(lines)

    def _confirm_apply_plan(self) -> bool:
        window = tk.Toplevel(self)
        window.title("Confirm Apply Plan")
        window.geometry("760x560")
        window.minsize(620, 420)
        window.transient(self)
        window.grab_set()

        result = {"confirmed": False}
        frame = ttk.Frame(window, padding=16)
        frame.pack(fill=tk.BOTH, expand=True)
        frame.rowconfigure(1, weight=1)
        frame.columnconfigure(0, weight=1)

        ttk.Label(
            frame,
            text="Review exactly what will happen before continuing.",
            style="CardTitle.TLabel",
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))

        text_widget = tk.Text(frame, wrap=tk.NONE, background="#f7fbff", foreground="#06285f")
        text_widget.insert("1.0", self._apply_confirmation_text())
        text_widget.configure(state=tk.DISABLED)
        text_widget.grid(row=1, column=0, sticky="nsew")

        y_scroll = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=text_widget.yview)
        y_scroll.grid(row=1, column=1, sticky="ns")
        x_scroll = ttk.Scrollbar(frame, orient=tk.HORIZONTAL, command=text_widget.xview)
        x_scroll.grid(row=2, column=0, sticky="ew")
        text_widget.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)

        buttons = ttk.Frame(frame)
        buttons.grid(row=3, column=0, columnspan=2, sticky="e", pady=(12, 0))

        def proceed() -> None:
            result["confirmed"] = True
            window.destroy()

        ttk.Button(buttons, text="Cancel", command=window.destroy, width=12).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(buttons, text="Proceed", command=proceed, style="Accent.TButton", width=12).grid(row=0, column=1)

        window.protocol("WM_DELETE_WINDOW", window.destroy)
        self.wait_window(window)
        return result["confirmed"]

    def _start_busy_progress(self, message: str) -> None:
        self.progress_text.set(message)
        self.status.set(message)
        if not self.progress_busy:
            self.progress_busy = True
            self.progress_bar.configure(mode="indeterminate")
            self.progress_bar.start(12)

    def _set_determinate_progress(self, percent: int, message: str) -> None:
        if self.progress_busy:
            self.progress_bar.stop()
            self.progress_bar.configure(mode="determinate")
            self.progress_busy = False
        self.progress.set(max(0, min(percent, 100)))
        self.progress_text.set(f"{max(0, min(percent, 100))}% - {message}")
        self.status.set(message)

    def _show_onboarding_once(self) -> None:
        settings = self._load_settings()
        if settings.get("onboarding_seen"):
            return
        self._show_onboarding()

    def _show_onboarding(self) -> None:
        OnboardingWindow(self, ONBOARDING_STEPS, self._mark_onboarding_seen)

    def _show_privacy(self) -> None:
        self._show_text_window("Privacy Policy", PRIVACY_POLICY_TEXT)

    def _show_terms(self) -> None:
        self._show_text_window("Terms and Conditions", TERMS_TEXT)

    def _show_faq(self) -> None:
        self._show_text_window("FAQ", FAQ_TEXT)

    def _open_support(self) -> None:
        webbrowser.open(KOFI_URL)
        self.status.set("Opened Ko-fi support page in your browser.")

    def _show_text_window(self, title: str, text: str, *, mark_onboarding_seen: bool = False) -> None:
        window = tk.Toplevel(self)
        window.title(title)
        window.geometry("720x560")
        window.minsize(560, 420)
        window.transient(self)

        frame = ttk.Frame(window, padding=16)
        frame.pack(fill=tk.BOTH, expand=True)
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        text_widget = tk.Text(frame, wrap=tk.WORD, height=20, background="#f7fbff", foreground="#06285f")
        text_widget.insert("1.0", text)
        text_widget.configure(state=tk.DISABLED)
        text_widget.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=text_widget.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        text_widget.configure(yscrollcommand=scrollbar.set)

        close_button = ttk.Button(frame, text="Close", command=window.destroy)
        close_button.grid(row=1, column=0, columnspan=2, sticky="e", pady=(12, 0))

        if mark_onboarding_seen:
            settings = self._load_settings()
            settings["onboarding_seen"] = True
            self._save_settings(settings)

    def _load_settings(self) -> dict[str, object]:
        try:
            return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def _save_settings(self, settings: dict[str, object]) -> None:
        SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        SETTINGS_PATH.write_text(json.dumps(settings, indent=2), encoding="utf-8")

    def _mark_onboarding_seen(self) -> None:
        settings = self._load_settings()
        settings["onboarding_seen"] = True
        self._save_settings(settings)


def main() -> None:
    app = FolderApp()
    app.mainloop()


class OnboardingWindow(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Tk,
        steps: list[tuple[str, str]],
        on_finish: callable,
    ) -> None:
        super().__init__(parent)
        self.steps = steps
        self.on_finish = on_finish
        self.index = 0

        self.title("How Fix My Folder Works")
        self.geometry("560x360")
        self.minsize(500, 320)
        self.transient(parent)
        self.grab_set()

        frame = ttk.Frame(self, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        frame.rowconfigure(1, weight=1)
        frame.columnconfigure(0, weight=1)

        self.step_label = ttk.Label(frame, text="", font=("Segoe UI", 10, "bold"))
        self.step_label.grid(row=0, column=0, sticky="w")

        self.body = tk.Text(frame, wrap=tk.WORD, height=8, relief=tk.FLAT, background="#f7fbff", foreground="#06285f")
        self.body.grid(row=1, column=0, sticky="nsew", pady=(14, 14))
        self.body.configure(state=tk.DISABLED)

        buttons = ttk.Frame(frame)
        buttons.grid(row=2, column=0, sticky="ew")
        buttons.columnconfigure(1, weight=1)
        self.back_button = ttk.Button(buttons, text="Back", command=self._back)
        self.back_button.grid(row=0, column=0)
        self.next_button = ttk.Button(buttons, text="Next", command=self._next)
        self.next_button.grid(row=0, column=2, padx=(8, 0))
        ttk.Button(buttons, text="Skip", command=self._finish).grid(row=0, column=3, padx=(8, 0))

        self.protocol("WM_DELETE_WINDOW", self._finish)
        self._render()

    def _render(self) -> None:
        title, text = self.steps[self.index]
        self.step_label.configure(text=f"{self.index + 1} of {len(self.steps)} - {title}")
        self.body.configure(state=tk.NORMAL)
        self.body.delete("1.0", tk.END)
        self.body.insert("1.0", text)
        self.body.configure(state=tk.DISABLED)
        self.back_button.configure(state=tk.NORMAL if self.index > 0 else tk.DISABLED)
        self.next_button.configure(text="Finish" if self.index == len(self.steps) - 1 else "Next")

    def _back(self) -> None:
        if self.index > 0:
            self.index -= 1
            self._render()

    def _next(self) -> None:
        if self.index >= len(self.steps) - 1:
            self._finish()
            return
        self.index += 1
        self._render()

    def _finish(self) -> None:
        self.on_finish()
        self.destroy()
