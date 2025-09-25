from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
from typing import List

from .scanner import scan_directory_for_photos, group_by_question_id


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Photo Review Utility")
        self.geometry("800x600")

        self.dir_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Select a directory and click Get Data")
        self.question_var = tk.StringVar()

        self._build_path_a_controls()

        self.valid_metas: List = []
        self.invalid_paths: List = []
        self.question_options: List[str] = []

    def _build_path_a_controls(self) -> None:
        frm = tk.Frame(self)
        frm.pack(fill=tk.BOTH, padx=12, pady=12)

        row1 = tk.Frame(frm)
        row1.pack(fill=tk.X)
        tk.Label(row1, text="Local directory:").pack(side=tk.LEFT)
        tk.Entry(row1, textvariable=self.dir_var, width=70).pack(side=tk.LEFT, padx=6)
        tk.Button(row1, text="Browse", command=self._browse_dir).pack(side=tk.LEFT)

        row2 = tk.Frame(frm)
        row2.pack(fill=tk.X, pady=(8, 0))
        tk.Button(row2, text="Get Data", command=self._get_data).pack(side=tk.LEFT)
        tk.Label(row2, textvariable=self.status_var, fg="gray").pack(side=tk.LEFT, padx=12)

        row3 = tk.Frame(frm)
        row3.pack(fill=tk.X, pady=(12, 0))
        tk.Label(row3, text="Question filter:").pack(side=tk.LEFT)
        self.question_menu = tk.OptionMenu(row3, self.question_var, "")
        self.question_menu.pack(side=tk.LEFT, padx=6)

        self.count_label = tk.Label(frm, text="")
        self.count_label.pack(anchor="w", pady=(12, 0))

    def _browse_dir(self) -> None:
        path = filedialog.askdirectory()
        if path:
            self.dir_var.set(path)

    def _get_data(self) -> None:
        directory = self.dir_var.get().strip()
        if not directory:
            messagebox.showwarning("Missing", "Please select a directory.")
            return
        root = Path(directory)
        if not root.exists() or not root.is_dir():
            messagebox.showerror("Invalid", "Directory does not exist.")
            return

        valid, invalid = scan_directory_for_photos(root)
        self.valid_metas = valid
        self.invalid_paths = invalid

        if invalid:
            self.status_var.set(
                "Some files do not match required format. Please download multimedia from CommCareHQ per instructions."
            )
        else:
            self.status_var.set("All files match expected naming format.")

        groups = group_by_question_id(valid)
        self.question_options = sorted(groups.keys())
        self._refresh_question_menu()

        total = len(valid)
        self.count_label.config(text=f"Total valid pictures found: {total}")

    def _refresh_question_menu(self) -> None:
        menu = self.question_menu["menu"]
        menu.delete(0, "end")
        if not self.question_options:
            self.question_var.set("")
            menu.add_command(label="", command=lambda v="": self.question_var.set(v))
            return
        self.question_var.set(self.question_options[0])
        for opt in self.question_options:
            menu.add_command(label=opt, command=lambda v=opt: self.question_var.set(v))


def run_app() -> None:
    app = App()
    app.mainloop()

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
from typing import List, Optional

from .scanner import scan_directory_for_photos, group_by_question_id


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Photo Review Utility")
        self.geometry("800x600")

        self.dir_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Select a directory and click Get Data")
        self.question_var = tk.StringVar()

        self._build_path_a_controls()

        self.valid_metas = []  # type: List
        self.invalid_paths = []  # type: List
        self.question_options: List[str] = []

    def _build_path_a_controls(self) -> None:
        frm = tk.Frame(self)
        frm.pack(fill=tk.BOTH, padx=12, pady=12)

        row1 = tk.Frame(frm)
        row1.pack(fill=tk.X)
        tk.Label(row1, text="Local directory:").pack(side=tk.LEFT)
        tk.Entry(row1, textvariable=self.dir_var, width=70).pack(side=tk.LEFT, padx=6)
        tk.Button(row1, text="Browse", command=self._browse_dir).pack(side=tk.LEFT)

        row2 = tk.Frame(frm)
        row2.pack(fill=tk.X, pady=(8, 0))
        tk.Button(row2, text="Get Data", command=self._get_data).pack(side=tk.LEFT)
        tk.Label(row2, textvariable=self.status_var, fg="gray").pack(side=tk.LEFT, padx=12)

        row3 = tk.Frame(frm)
        row3.pack(fill=tk.X, pady=(12, 0))
        tk.Label(row3, text="Question filter:").pack(side=tk.LEFT)
        self.question_menu = tk.OptionMenu(row3, self.question_var, "")
        self.question_menu.pack(side=tk.LEFT, padx=6)

        self.count_label = tk.Label(frm, text="")
        self.count_label.pack(anchor="w", pady=(12, 0))

    def _browse_dir(self) -> None:
        path = filedialog.askdirectory()
        if path:
            self.dir_var.set(path)

    def _get_data(self) -> None:
        directory = self.dir_var.get().strip()
        if not directory:
            messagebox.showwarning("Missing", "Please select a directory.")
            return
        root = Path(directory)
        if not root.exists() or not root.is_dir():
            messagebox.showerror("Invalid", "Directory does not exist.")
            return

        valid, invalid = scan_directory_for_photos(root)
        self.valid_metas = valid
        self.invalid_paths = invalid

        if invalid:
            self.status_var.set(
                "Some files do not match required format. Please download multimedia from CommCareHQ per instructions."
            )
        else:
            self.status_var.set("All files match expected naming format.")

        groups = group_by_question_id(valid)
        self.question_options = sorted(groups.keys())
        self._refresh_question_menu()

        total = len(valid)
        self.count_label.config(text=f"Total valid pictures found: {total}")

    def _refresh_question_menu(self) -> None:
        menu = self.question_menu["menu"]
        menu.delete(0, "end")
        if not self.question_options:
            self.question_var.set("")
            menu.add_command(label="", command=lambda v="": self.question_var.set(v))
            return
        # default to first
        self.question_var.set(self.question_options[0])
        for opt in self.question_options:
            menu.add_command(label=opt, command=lambda v=opt: self.question_var.set(v))


def run_app() -> None:
    app = App()
    app.mainloop()


