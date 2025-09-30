from __future__ import annotations

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
from typing import List
import random
from PIL import Image, ImageTk
import csv
from datetime import datetime
import webbrowser
import requests
import json

from .scanner import scan_directory_for_photos, group_by_question_id, group_by_form_id


def debug_print(message: str) -> None:
    """Print debug message if debug mode is enabled"""
    import os
    if os.environ.get('PHOTO_REVIEW_DEBUG') == '1':
        print(f"DEBUG: {message}")


class App(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Photo Review Utility")
        self.geometry("900x600")
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        self.dir_var = ctk.StringVar()
        self.status_var = ctk.StringVar(value="")
        self.buckets_var = ctk.StringVar(value="Real, Fake")
        self.percent_var = ctk.StringVar(value="10.0")  # Use StringVar to avoid conversion errors
        self.include_known_bad_var = ctk.BooleanVar(value=False)
        self.known_bad_dir_var = ctk.StringVar()
        self.known_bad_count_var = ctk.StringVar(value="")  # Number of bad photos to insert
        self.path_mode_var = ctk.StringVar()  # local or api - no default value
        self.reviewer_name_var = ctk.StringVar()
        
        # API-specific variables
        self.api_file_var = ctk.StringVar()
        self.date_start_var = ctk.StringVar(value="01/01/24")
        self.date_end_var = ctk.StringVar()
        self.api_limit_var = ctk.StringVar(value="20")
        
        # Set today's date as default for end date in MM/DD/YY format
        from datetime import datetime
        today = datetime.now().strftime("%m/%d/%y")
        self.date_end_var.set(today)

        self._build_path_a_controls()

        self.valid_metas: List = []
        self.invalid_paths: List = []
        self.question_options: List[str] = []
        self.session_config = None
        self.session_visits: List[dict] = []
        self.results: List[dict] = []
        self._current_index = 0
        self._last_selected_questions: List[str] = []
        self._selected_questions: List[str] = []
        
        # Load saved settings
        self._load_settings()
        
        # Initially hide API controls and show local directory controls
        self.api_controls_frame.pack_forget()
        
        # Initialize question options
        self.question_options = []

    def _build_path_a_controls(self) -> None:
        # Use a scrollable frame to contain all controls
        self.main_scroll = ctk.CTkScrollableFrame(self, height=400)
        self.main_scroll.pack(fill="both", expand=True, padx=12, pady=12)
        
        frm = self.main_scroll  # Use the scrollable frame as our main container

        # Reviewer name at the top
        reviewer_row = ctk.CTkFrame(frm)
        reviewer_row.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(reviewer_row, text="Reviewer name:").pack(side="left")
        ctk.CTkEntry(reviewer_row, textvariable=self.reviewer_name_var, width=200).pack(side="left", padx=(6, 0))

        # Data Source selector
        mode_row = ctk.CTkFrame(frm)
        mode_row.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(mode_row, text="Data Source:").pack(side="left")
        ctk.CTkRadioButton(mode_row, text="Local directory", variable=self.path_mode_var, value="local", command=self._on_data_source_change).pack(side="left", padx=(6, 0))
        ctk.CTkRadioButton(mode_row, text="CommCareHQ API", variable=self.path_mode_var, value="api", command=self._on_data_source_change).pack(side="left", padx=(6, 0))

        # Status text below data source
        self.status_label = ctk.CTkLabel(frm, text="Select a directory and click 'Check Photo Data'", text_color="gray")
        self.status_label.pack(anchor="w", pady=(0, 8))

        # Data source controls container
        self.data_source_frame = ctk.CTkFrame(frm)
        # Don't pack initially - will be shown when radio button is selected
        
        # Local directory controls
        self.local_dir_frame = ctk.CTkFrame(self.data_source_frame)
        self.local_dir_frame.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(self.local_dir_frame, text="Local directory:").pack(side="left")
        ctk.CTkEntry(self.local_dir_frame, textvariable=self.dir_var, width=400).pack(side="left", padx=6)
        ctk.CTkButton(self.local_dir_frame, text="Browse", command=self._browse_dir, width=80).pack(side="left", padx=6)
        ctk.CTkButton(self.local_dir_frame, text="Check Photo Data", command=self._get_data, width=120).pack(side="left", padx=6)

        # API controls (initially hidden)
        self.api_controls_frame = ctk.CTkFrame(self.data_source_frame)
        
        # Date range
        date_row = ctk.CTkFrame(self.api_controls_frame)
        date_row.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(date_row, text="Start Date (MM/DD/YY):").pack(side="left")
        self.start_date_entry = ctk.CTkEntry(date_row, textvariable=self.date_start_var, width=120, placeholder_text="01/01/24")
        self.start_date_entry.pack(side="left", padx=(6, 12))
        ctk.CTkLabel(date_row, text="End Date (MM/DD/YY):").pack(side="left")
        self.end_date_entry = ctk.CTkEntry(date_row, textvariable=self.date_end_var, width=120, placeholder_text="12/31/25")
        self.end_date_entry.pack(side="left", padx=(6, 0))
        
        # Number of forms to download
        limit_row = ctk.CTkFrame(self.api_controls_frame)
        limit_row.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(limit_row, text="Number of forms to download per domain:").pack(side="left")
        ctk.CTkEntry(limit_row, textvariable=self.api_limit_var, width=80).pack(side="left", padx=(6, 0))
        ctk.CTkLabel(limit_row, text="Max 1000 forms. Download from HQ exporter if you want more", text_color="gray").pack(side="left", padx=(6, 0))
        
        # domain/app pairs file
        api_file_row = ctk.CTkFrame(self.api_controls_frame)
        api_file_row.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(api_file_row, text="Domain/app pairs file:").pack(side="left")
        ctk.CTkEntry(api_file_row, textvariable=self.api_file_var, width=400).pack(side="left", padx=6)
        ctk.CTkButton(api_file_row, text="Browse", command=self._browse_api_file, width=80).pack(side="left", padx=6)
        ctk.CTkButton(api_file_row, text="Check Photo Data", command=self._get_data, width=120).pack(side="left", padx=6)

        # Two-column layout
        self.columns_frame = ctk.CTkFrame(frm)
        # Don't pack initially - will be shown when data source is selected
        
        # Left column - Photo filter
        left_column = ctk.CTkFrame(self.columns_frame)
        left_column.pack(side="left", fill="y", padx=(0, 8))
        left_column.configure(width=500)
        
        ctk.CTkLabel(left_column, text="Photo filter (multi-select):").pack(anchor="w", pady=(8, 4))
        
        # Photo filter with checkboxes
        self.photo_filter_frame = ctk.CTkScrollableFrame(left_column, height=200)
        self.photo_filter_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.question_checkboxes = {}
        
        # Right column - Other configuration
        right_column = ctk.CTkFrame(self.columns_frame)
        right_column.pack(side="right", fill="y")
        right_column.configure(width=500)
        
        # Photo buckets
        buckets_row = ctk.CTkFrame(right_column)
        buckets_row.pack(fill="x", pady=(8, 8))
        ctk.CTkLabel(buckets_row, text="List desired photo buckets (comma-separated):").pack(side="left")
        ctk.CTkEntry(buckets_row, textvariable=self.buckets_var, width=300).pack(side="left", padx=6)

        # Percent of pictures
        percent_row = ctk.CTkFrame(right_column)
        percent_row.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(percent_row, text="Percent of pictures to review:").pack(side="left")
        self.percent_entry = ctk.CTkEntry(percent_row, textvariable=self.percent_var, width=80)
        self.percent_entry.pack(side="left", padx=6)
        self.percent_entry.bind("<KeyRelease>", lambda e: self._update_percent_count())
        self.percent_count_label = ctk.CTkLabel(percent_row, text="")
        self.percent_count_label.pack(side="left", padx=(12, 0))

        # Include known bad photos checkbox
        known_bad_row = ctk.CTkFrame(right_column)
        known_bad_row.pack(fill="x", pady=(0, 8))
        ctk.CTkCheckBox(known_bad_row, text="Include known bad photos", variable=self.include_known_bad_var, command=self._toggle_known_bad_controls).pack(side="left")

        # Known bad directory (initially hidden)
        self.row7_kb = ctk.CTkFrame(right_column)
        self.row7_kb.pack(fill="x", pady=(4, 0))
        ctk.CTkLabel(self.row7_kb, text="Known bad photo directory:").pack(side="left")
        self.kb_entry = ctk.CTkEntry(self.row7_kb, textvariable=self.known_bad_dir_var, width=300)
        self.kb_entry.pack(side="left", padx=6)
        ctk.CTkButton(self.row7_kb, text="Browse", command=self._browse_known_bad_dir, width=80).pack(side="left", padx=6)
        
        # Known bad count input (initially hidden)
        self.row8_kb = ctk.CTkFrame(right_column)
        self.row8_kb.pack(fill="x", pady=(4, 0))
        ctk.CTkLabel(self.row8_kb, text="Enter number of bad photos to randomly insert:").pack(side="left")
        ctk.CTkEntry(self.row8_kb, textvariable=self.known_bad_count_var, width=60).pack(side="left", padx=6)

        # Initially hide known bad controls
        self.row7_kb.pack_forget()
        self.row8_kb.pack_forget()

        # Start Review button (separate from columns frame)
        self.start_review_frame = ctk.CTkFrame(frm)
        # Don't pack initially - will be shown when data source is selected
        ctk.CTkButton(self.start_review_frame, text="Start Review", command=self._build_set, width=120).pack(side="left")

    def _browse_dir(self) -> None:
        # Use last directory as default
        initial_dir = self.dir_var.get().strip()
        if not initial_dir:
            # Try to get parent directory from saved path
            try:
                with open("app_settings.txt", "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    for line in lines:
                        if line.startswith("last_directory:"):
                            saved_path = line.split(":", 1)[1].strip()
                            if saved_path:
                                from pathlib import Path
                                initial_dir = str(Path(saved_path).parent)
                            break
            except:
                pass
        
        path = filedialog.askdirectory(initialdir=initial_dir)
        if path:
            self.dir_var.set(path)

    def _get_data(self) -> None:
        mode = self.path_mode_var.get()
        debug_print(f"Data source mode: {mode}")
        
        if mode == "local":
            # Handle local directory
            directory = self.dir_var.get().strip()
            debug_print(f"Local directory: {directory}")
            if not directory:
                from tkinter import messagebox
                messagebox.showwarning("Missing", "Please select a directory.")
                return
            root = Path(directory)
            if not root.exists() or not root.is_dir():
                from tkinter import messagebox
                messagebox.showerror("Invalid", "Directory does not exist.")
                return

            debug_print(f"Scanning directory: {root}")
            valid, invalid = scan_directory_for_photos(root)
            self.valid_metas = valid
            self.invalid_paths = invalid
            debug_print(f"Found {len(valid)} valid photos, {len(invalid)} invalid paths")
        elif mode == "api":
            # Handle API data
            self._get_api_data()
            return

        if invalid:
            self._show_warning_status("Some files do not match required format. Please download multimedia from CommCareHQ (per instructions).")
        else:
            self._show_success_status("All files match expected naming format.")

        groups = group_by_question_id(valid)
        self.question_options = sorted(groups.keys())
        self._refresh_question_menu()

        total = len(valid)
        self._update_percent_count()

    def _show_warning_status(self, message: str) -> None:
        self.status_label.configure(text=f"⚠️ {message}", text_color="red")
        # Add clickable link for instructions
        if "(per instructions)" in message:
            # Create a clickable link
            self.status_label.bind("<Button-1>", lambda e: webbrowser.open("https://dimagi.atlassian.net/wiki/spaces/commcarepublic/pages/2143956271/Form+Data+Export#Types-of-Forms-Exports"))
            self.status_label.configure(cursor="hand2")

    def _show_success_status(self, message: str) -> None:
        # Show photo count instead of generic success message
        total = len(self.valid_metas)
        self.status_label.configure(text=f"{total} photos found", text_color="green")
        self.status_label.unbind("<Button-1>")
        self.status_label.configure(cursor="")

    def _toggle_known_bad_controls(self) -> None:
        enabled = self.include_known_bad_var.get()
        if enabled:
            self.row7_kb.pack(fill="x", pady=(4, 0))
            self.row8_kb.pack(fill="x", pady=(4, 0))
        else:
            self.row7_kb.pack_forget()
            self.row8_kb.pack_forget()

    def _browse_known_bad_dir(self) -> None:
        path = filedialog.askdirectory()
        if path:
            self.known_bad_dir_var.set(path)

    def _build_set(self) -> None:
        if not self.valid_metas:
            messagebox.showwarning("No data", "Load data first with 'Check Photo Data'.")
            return
        selected_questions = self._selected_questions
        if not selected_questions:
            messagebox.showwarning("Missing", "Select at least one question.")
            return
        buckets = [b.strip() for b in self.buckets_var.get().split(",") if b.strip()]
        if len(buckets) < 2:
            messagebox.showwarning("Buckets", "Provide at least two buckets (comma-separated).")
            return
        try:
            percent_str = self.percent_var.get().strip()
            if not percent_str:
                messagebox.showwarning("Percent", "Enter a percent value.")
                return
            percent = float(percent_str)
        except (ValueError, TypeError):
            messagebox.showwarning("Percent", "Enter a valid number for percent.")
            return
        if percent <= 0 or percent > 100:
            messagebox.showwarning("Percent", "Percent must be in (0, 100].")
            return
        include_kb = self.include_known_bad_var.get()
        kb_dir = None
        if include_kb:
            kb_dir_str = self.known_bad_dir_var.get().strip()
            kb_count_str = self.known_bad_count_var.get().strip()
            
            # Validate known bad configuration
            if not kb_dir_str or not kb_count_str:
                messagebox.showwarning("Known Bad Configuration", 
                    "Bad photo information not configured correctly. Either don't insert bad photos into the review or fill in the bad photo directory and number to insert.")
                return
            
            kb_dir = Path(kb_dir_str)
            if not kb_dir.exists() or not kb_dir.is_dir():
                messagebox.showerror("Known bad", "Select a valid known bad directory.")
                return
            
            # Validate count
            try:
                kb_count = int(kb_count_str)
                if kb_count <= 0:
                    messagebox.showwarning("Known Bad Count", "Number of bad photos must be greater than 0.")
                    return
            except ValueError:
                messagebox.showwarning("Known Bad Count", "Enter a valid number for bad photos to insert.")
                return

        # Compute filtered photos count for confirmation
        filtered = [m for m in self.valid_metas if m.question_id in selected_questions]
        target_count = max(1, int(round(len(filtered) * (percent / 100.0)))) if filtered else 0

        # Store session config
        self.session_config = {
            "question_ids": selected_questions,
            "buckets": buckets,
            "percent": percent,
            "include_known_bad": include_kb,
            "known_bad_dir": str(kb_dir) if kb_dir else None,
            "known_bad_count": self.known_bad_count_var.get().strip(),
            "target_count": target_count,
        }
        # Save settings for next time
        self._save_settings()
        
        # Build session now and proceed to review UI
        self._create_session_and_start_review()

    def _refresh_question_menu(self) -> None:
        # Clear existing checkboxes
        for widget in self.photo_filter_frame.winfo_children():
            widget.destroy()
        self.question_checkboxes.clear()
        
        # Get photo counts for each question
        groups = group_by_question_id(self.valid_metas)
        
        # Create checkboxes for each question option
        for opt in self.question_options:
            count = len(groups.get(opt, []))
            var = ctk.BooleanVar(value=True)  # Default to selected
            checkbox = ctk.CTkCheckBox(
                self.photo_filter_frame, 
                text=f"{opt} ({count} photos)",
                variable=var,
                command=self._on_question_select
            )
            checkbox.pack(anchor="w", pady=2)
            self.question_checkboxes[opt] = var
        
        # Update selection state
        self._on_question_select()

    def _on_question_select(self, event=None) -> None:
        # Get selected questions from checkboxes
        self._selected_questions = []
        for opt, var in self.question_checkboxes.items():
            if var.get():
                self._selected_questions.append(opt)
        self._update_percent_count()

    def _update_percent_count(self) -> None:
        # Compute how many photos match current question selection and percent
        try:
            percent_str = self.percent_var.get().strip()
            if not percent_str:
                percent = 0.0
            else:
                percent = float(percent_str)
        except (ValueError, TypeError):
            percent = 0.0
        selected = self._selected_questions if self._selected_questions else self.question_options
        filtered = [m for m in self.valid_metas if m.question_id in selected]
        count = int(round(len(filtered) * (percent / 100.0))) if filtered and percent > 0 else 0
        self.percent_count_label.configure(text=f"(~{count} photos)")

    # ---- Review session building and UI ----
    def _create_session_and_start_review(self) -> None:
        # Filter by selected questions
        chosen = [m for m in self.valid_metas if m.question_id in self.session_config["question_ids"]]
        if not chosen:
            messagebox.showwarning("No photos", "No photos match the selected filters.")
            return
        # Group by form_id (visit)
        visits = {}
        for m in chosen:
            visits.setdefault(m.form_id, []).append(m)
        visit_items = list(visits.items())
        random.shuffle(visit_items)
        # Determine how many photos we want, then include visits until we surpass
        target_photos = self.session_config["target_count"]
        selected_visits: List[dict] = []
        total = 0
        for form_id, metas in visit_items:
            selected_visits.append({
                "form_id": form_id,
                "user_id": metas[0].user_id,
                "photos": metas,
                "is_known_bad": False,
            })
            total += len(metas)
            if target_photos and total >= target_photos:
                break
        # Known-bad insertion with count limit and proper randomization
        if self.session_config.get("include_known_bad") and self.session_config.get("known_bad_dir"):
            try:
                kb_count = int(self.session_config.get("known_bad_count", "5"))
            except (ValueError, TypeError):
                kb_count = 5
            
            kb_dir = Path(self.session_config["known_bad_dir"])  # type: ignore[arg-type]
            kb_paths = [p for p in kb_dir.iterdir() if p.is_file()]
            random.shuffle(kb_paths)
            
            # Limit to requested count
            kb_paths = kb_paths[:kb_count]
            
            if kb_paths:
                kb_visits = [{
                    "form_id": f"KNOWN_BAD_{i}",
                    "user_id": "",
                    "photos": [type("KBMeta", (), {"filepath": p, "filename": p.name, "form_id": f"KNOWN_BAD_{i}", "user_id": "", "question_id": "known_bad", "json_block": "known_bad", "extension": p.suffix.lstrip(".")})()],
                    "is_known_bad": True,
                } for i, p in enumerate(kb_paths)]
                
                # Randomly insert known-bad visits into the main list
                all_visits = selected_visits + kb_visits
                random.shuffle(all_visits)
                selected_visits = all_visits

        if not selected_visits:
            messagebox.showwarning("No visits", "No visits were selected for review.")
            return

        self.session_visits = selected_visits
        self._current_index = 0
        self._show_review_ui()

    def _show_review_ui(self) -> None:
        # Hide all widgets in root and create review frame
        for child in list(self.children.values()):
            child.pack_forget()
        self.review_frame = ctk.CTkFrame(self)
        self.review_frame.pack(fill="both", expand=True)

        header = ctk.CTkFrame(self.review_frame)
        header.pack(fill="x", pady=(8, 8))
        self.progress_var = ctk.StringVar()
        ctk.CTkLabel(header, textvariable=self.progress_var).pack(side="left")
        ctk.CTkButton(header, text="Back to Config", command=self._back_to_config).pack(side="right")

        # Canvas for images with scrollbar - use regular tkinter for better compatibility
        body = tk.Frame(self.review_frame)
        body.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(body, background="#f3f3f3")
        vsb = tk.Scrollbar(body, orient="vertical", command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas)
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=vsb.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        # Bucket buttons
        self.bucket_frame = ctk.CTkFrame(self.review_frame)
        self.bucket_frame.pack(fill="x", pady=(8, 12))
        for b in self.session_config["buckets"]:
            ctk.CTkButton(self.bucket_frame, text=b, command=lambda v=b: self._record_and_next(v)).pack(side="left", padx=6)

        self._render_current_visit()

    def _render_current_visit(self) -> None:
        # Clear previous inner content
        for w in self.inner.winfo_children():
            w.destroy()
        # Update progress
        idx = self._current_index + 1
        total = len(self.session_visits)
        visit = self.session_visits[self._current_index]
        self.progress_var.set(f"Photo Review {idx}/{total}")
        # Render images side-by-side, resized to width ~400px, three per row
        max_width = 400
        cols = 3
        self._image_refs = []  # keep refs to avoid GC
        row = 0
        col = 0
        for i, meta in enumerate(visit["photos"]):
            path = meta.filepath
            try:
                img = Image.open(path)
                w, h = img.size
                if w > max_width:
                    ratio = max_width / float(w)
                    img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)
                tk_img = ImageTk.PhotoImage(img)
                panel = tk.Label(self.inner, image=tk_img)
                panel.grid(row=row, column=col, padx=8, pady=8, sticky="nw")
                self._image_refs.append(tk_img)
                col += 1
                if col >= cols:
                    col = 0
                    row += 1
            except Exception as e:
                err = tk.Label(self.inner, text=f"Failed to load image: {path} ({e})", fg="red")
                err.grid(row=row, column=col, padx=8, pady=8, sticky="nw")
                col += 1
                if col >= cols:
                    col = 0
                    row += 1

    def _record_and_next(self, bucket_value: str) -> None:
        visit = self.session_visits[self._current_index]
        reviewer = self.reviewer_name_var.get().strip()
        if visit.get("is_known_bad", False):
            # For known-bad photos, put filename in form_id and KNOWN_BAD_X in user_id
            photo_filename = visit["photos"][0].filename if visit["photos"] else "unknown"
            self.results.append({
                "form_id": photo_filename,
                "user_id": visit["form_id"],  # This contains KNOWN_BAD_X
                "reviewer": reviewer,
                "bucket": bucket_value,
                "is_known_bad": True,
                "date_reviewed": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })
        else:
            # For real photos, use normal format
            self.results.append({
                "form_id": visit["form_id"],
                "user_id": visit.get("user_id", ""),
                "reviewer": reviewer,
                "bucket": bucket_value,
                "is_known_bad": False,
                "date_reviewed": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })
        if self._current_index + 1 < len(self.session_visits):
            self._current_index += 1
            self._render_current_visit()
        else:
            self._on_review_complete()

    def _on_review_complete(self) -> None:
        messagebox.showinfo("Done", "Review complete. Choose where to save CSV results.")
        self._export_csvs()
        self._back_to_config()

    def _export_csvs(self) -> None:
        if not self.results:
            return
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_main = f"review_results_{timestamp}.csv"
        save_path = filedialog.asksaveasfilename(
            title="Save review CSV",
            defaultextension=".csv",
            initialfile=default_main,
            filetypes=[("CSV files", "*.csv")],
        )
        if not save_path:
            return
        # Write main results
        fields = ["form_id", "user_id", "reviewer", "bucket", "is_known_bad", "date_reviewed"]
        try:
            with open(save_path, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=fields)
                w.writeheader()
                for r in self.results:
                    w.writerow(r)
        except Exception as e:
            messagebox.showerror("Save error", f"Failed to save CSV: {e}")
            return
        # No separate known-bad CSV needed - all data is in the main CSV

    def _back_to_config(self) -> None:
        # Save current selection state
        self._last_selected_questions = self._selected_questions.copy()
        
        # Destroy review frame and rebuild config UI
        if hasattr(self, "review_frame"):
            self.review_frame.destroy()
        if hasattr(self, "main_scroll"):
            self.main_scroll.destroy()
        # rebuild controls
        self._build_path_a_controls()
        
        # Get current data source mode
        current_mode = self.path_mode_var.get()
        
        # Show the appropriate frames based on current data source
        if current_mode:
            # Show the data source frame, columns frame, and start review button
            self.data_source_frame.pack(fill="x", pady=(0, 8))
            self.columns_frame.pack(fill="x", pady=(8, 0))
            self.start_review_frame.pack(fill="x", pady=(12, 0))
            
            # Show the appropriate data source specific controls
            if current_mode == "local":
                self.local_dir_frame.pack(fill="x", pady=(0, 8))
                self.api_controls_frame.pack_forget()
                self.status_label.configure(text="Select a directory and click 'Check Photo Data'", text_color="gray")
            elif current_mode == "api":
                self.local_dir_frame.pack_forget()
                self.api_controls_frame.pack(fill="x", pady=(0, 8))
                self.status_label.configure(text="Configure API settings and click 'Check Photo Data'", text_color="gray")
        
        # Restore known bad photos checkbox state and show/hide controls accordingly
        if self.include_known_bad_var.get():
            self.row7_kb.pack(fill="x", pady=(4, 0))
            self.row8_kb.pack(fill="x", pady=(4, 0))
        else:
            self.row7_kb.pack_forget()
            self.row8_kb.pack_forget()
        
        # Re-set state and restore previous selections
        self._refresh_question_menu()
        # Restore previous selections in checkboxes
        if hasattr(self, '_last_selected_questions') and self._last_selected_questions:
            for question, var in self.question_checkboxes.items():
                var.set(question in self._last_selected_questions)
        self._on_question_select()

    def _load_settings(self) -> None:
        """Load saved settings from app_settings.txt"""
        try:
            with open("app_settings.txt", "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("reviewer_name:"):
                        name = line.split(":", 1)[1].strip()
                        if name:
                            self.reviewer_name_var.set(name)
                    elif line.startswith("last_directory:"):
                        directory = line.split(":", 1)[1].strip()
                        if directory:
                            self.dir_var.set(directory)
                    elif line.startswith("api_file:"):
                        api_file = line.split(":", 1)[1].strip()
                        if api_file:
                            self.api_file_var.set(api_file)
        except FileNotFoundError:
            pass  # No saved settings yet
        except Exception as e:
            print(f"Error loading settings: {e}")  # Debug output

    def _save_settings(self) -> None:
        """Save current settings to app_settings.txt"""
        try:
            with open("app_settings.txt", "w", encoding="utf-8") as f:
                # Save reviewer name
                reviewer_name = self.reviewer_name_var.get().strip()
                if reviewer_name:
                    f.write(f"reviewer_name:{reviewer_name}\n")
                
                # Save last directory
                last_dir = self.dir_var.get().strip()
                if last_dir:
                    f.write(f"last_directory:{last_dir}\n")
                
                # Don't save known bad count - should always start blank
                
                # Save API file path
                api_file = self.api_file_var.get().strip()
                if api_file:
                    f.write(f"api_file:{api_file}\n")
        except Exception as e:
            print(f"Error saving settings: {e}")  # Debug output

    def _on_data_source_change(self) -> None:
        """Handle data source radio button changes"""
        mode = self.path_mode_var.get()
        
        # Show the data source frame when any radio button is selected
        if mode:
            self.data_source_frame.pack(fill="x", pady=(0, 8))
            # Show the columns frame
            self.columns_frame.pack(fill="x", pady=(8, 0))
            # Show the start review button below the columns frame
            self.start_review_frame.pack(fill="x", pady=(12, 0))
        
        if mode == "local":
            self.local_dir_frame.pack(fill="x", pady=(0, 8))
            self.api_controls_frame.pack_forget()
            self.status_label.configure(text="Select a directory and click 'Check Photo Data'", text_color="gray")
        elif mode == "api":
            self.local_dir_frame.pack_forget()
            self.api_controls_frame.pack(fill="x", pady=(0, 8))
            self.status_label.configure(text="Configure API settings and click 'Check Photo Data'", text_color="gray")
            # Reset photo filter when switching to API mode
            self._reset_photo_filter()

    def _reset_photo_filter(self) -> None:
        """Reset photo filter when switching data sources"""
        # Clear existing checkboxes
        for widget in self.photo_filter_frame.winfo_children():
            widget.destroy()
        self.question_checkboxes.clear()
        
        # Clear question options and valid metas
        self.question_options = []
        self.valid_metas = []
        self.invalid_paths = []
        
        # Update status
        self.status_label.configure(text="Configure API settings and click 'Check Photo Data'", text_color="gray")

    def _browse_api_file(self) -> None:
        """Browse for API input file"""
        from tkinter import filedialog
        filename = filedialog.askopenfilename(
            title="Select API input file",
            filetypes=[("Text files", "*.txt"), ("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            self.api_file_var.set(filename)
            # Save the API file path
            self._save_settings()

    def _convert_date_format(self, date_str: str) -> str:
        """Convert MM/DD/YY to YYYY-MM-DD format"""
        try:
            parts = date_str.split('/')
            if len(parts) != 3:
                return ""
            
            month, day, year = parts
            month = int(month)
            day = int(day)
            year = int(year)
            
            # Convert 2-digit year to 4-digit
            if year < 100:
                if year < 50:  # Assume 20xx for years 00-49
                    year += 2000
                else:  # Assume 19xx for years 50-99
                    year += 1900
            
            # Validate month and day
            if not (1 <= month <= 12):
                return ""
            if not (1 <= day <= 31):
                return ""
            
            return f"{year}-{month:02d}-{day:02d}"
        except (ValueError, IndexError):
            return ""

    def _parse_domain_form_file(self, file_path: str) -> dict:
        """Parse the domain/app pairs file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Filter out comments
            lines = [line.strip() for line in content.split('\n') if line.strip() and not line.strip().startswith('#')]
            content = '\n'.join(lines)
            
            # Parse as JSON
            import json
            data = json.loads(content)
            
            domain_form_pairs = {}
            for domain, app_id in data.items():
                # Extract UUID from app_id if it's a full URL
                if app_id.startswith('http'):
                    # Extract UUID from URL like "http://openrosa.org/formdesigner/UUID"
                    app_id = app_id.split('/')[-1]
                domain_form_pairs[domain] = app_id
            
            return domain_form_pairs
        except Exception as e:
            print(f"Error parsing domain/app file: {e}")
            return {}

    def _find_env_file(self) -> str:
        """Find the .env file in Coverage directory"""
        return find_env_file()

    def _load_api_credentials(self, env_file: str) -> tuple:
        """Load API credentials from .env file"""
        try:
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('COMMCARE_USERNAME='):
                        username = line.split('=', 1)[1].strip()
                    elif line.startswith('COMMCARE_API_KEY='):
                        api_key = line.split('=', 1)[1].strip()
            
            return username, api_key
        except Exception as e:
            print(f"Error loading credentials: {e}")
            return "", ""

    def _get_forms_from_api(self, domain_form_pairs: dict, date_start: str, date_end: str, username: str, api_key: str, limit: int) -> list:
        """Get forms from CommCare List Forms API"""
        import requests
        import json
        
        all_forms = []
        
        for domain, app_id in domain_form_pairs.items():
            debug_print(f"  Processing domain: {domain}")
            debug_print(f"  Form app_id: {app_id}")
            
            try:
                # CommCare List Forms API
                url = f"https://www.commcarehq.org/a/{domain}/api/v0.5/form/"
                debug_print(f"  API URL: {url}")
                
                params = {
                    'app_id': app_id,
                    'limit': limit
                }
                
                # Only add date filters if dates are provided and not empty
                if date_start and date_start.strip():
                    params['received_on_start'] = date_start
                if date_end and date_end.strip():
                    params['received_on_end'] = date_end
                debug_print(f"  API Parameters: {params}")
                
                debug_print(f"  Making API request...")
                response = requests.get(url, auth=(username, api_key), params=params, timeout=30)
                debug_print(f"  Response status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    debug_print(f"  [OK] API call successful")
                    debug_print(f"  Response keys: {list(data.keys())}")
                    
                    if 'objects' in data:
                        forms = data['objects']
                        debug_print(f"  Found {len(forms)} forms for domain {domain}")
                        
                        # If no forms found with app_id, try without app_id parameter
                        if len(forms) == 0:
                            print(f"  No forms found with app_id '{app_id}', trying without app_id filter...")
                            params_without_app_id = {k: v for k, v in params.items() if k != 'app_id'}
                            debug_print(f"  Retry API Parameters: {params_without_app_id}")
                            
                            retry_response = requests.get(url, auth=(username, api_key), params=params_without_app_id, timeout=30)
                            if retry_response.status_code == 200:
                                retry_data = retry_response.json()
                                if 'objects' in retry_data:
                                    retry_forms = retry_data['objects']
                                    debug_print(f"  Found {len(retry_forms)} forms without app_id filter")
                                    all_forms.extend(retry_forms)
                                    
                                    # Show sample of what forms are available
                                    if retry_forms:
                                        sample_form = retry_forms[0]
                                        debug_print(f"  Sample form app_id: {sample_form.get('app_id', 'N/A')}")
                                        debug_print(f"  Sample form type: {sample_form.get('type', 'N/A')}")
                        else:
                            all_forms.extend(forms)
                        
                        # Debug: Show sample form data
                        if forms:
                            sample_form = forms[0]
                            debug_print(f"  Sample form keys: {list(sample_form.keys())}")
                            if 'attachments' in sample_form:
                                attachments = sample_form['attachments']
                                debug_print(f"  Sample form has {len(attachments)} attachments")
                                for att_name, att_info in list(attachments.items())[:3]:  # Show first 3
                                    debug_print(f"    - {att_name}: {type(att_info)}")
                    else:
                        print(f"  [ERROR] No 'objects' key in response for domain {domain}")
                        print(f"  Response data: {data}")
                else:
                    print(f"  [ERROR] API call failed with status {response.status_code}")
                    print(f"  Response: {response.text}")
                    
            except requests.exceptions.Timeout:
                print(f"  [ERROR] API request timed out for domain {domain}")
                continue
            except requests.exceptions.RequestException as e:
                print(f"  [ERROR] API request failed for domain {domain}: {e}")
                continue
            except Exception as e:
                print(f"  [ERROR] Unexpected error for domain {domain}: {e}")
                import traceback
                print(f"  Traceback: {traceback.format_exc()}")
                continue
        
        print(f"Total forms collected: {len(all_forms)}")
        return all_forms

    def _download_attachments(self, forms_data: list, limit: int, username: str, api_key: str) -> list:
        """Download attachments from forms using data from forms list API"""
        import requests
        import os
        from pathlib import Path
        
        print(f"Starting photo download process...")
        print(f"Forms to process: {len(forms_data)}")
        
        downloaded_photos = []
        # Create timestamped subdirectory for this download session
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        download_dir = Path("downloaded_photos") / f"session_{timestamp}"
        download_dir.mkdir(parents=True, exist_ok=True)
        debug_print(f"Download directory: {download_dir.absolute()}")
        
        photo_count = 0
        forms_with_attachments = 0
        total_attachments = 0
        photo_attachments = 0
        
        # Track photos per domain
        photos_per_domain = {}
        
        # Process all forms (limit was already applied per domain in API call)
        forms_to_process = forms_data
        debug_print(f"Processing {len(forms_to_process)} forms (limit applied per domain: {limit})")
        
        for i, form in enumerate(forms_to_process):
                
            debug_print(f"  Processing form {i+1}/{len(forms_data)}")
            
            # Get form metadata
            # User ID is in the form.meta section
            form_data = form.get('form', {})
            meta = form_data.get('meta', {})
            user_id = meta.get('userID', 'unknown')
            form_id = form.get('id', 'unknown')
            domain = form.get('domain', 'unknown')
            
            debug_print(f"    Form ID: {form_id}")
            debug_print(f"    User ID: {user_id}")
            debug_print(f"    Domain: {domain}")
            
            # Get attachments from the form data (already included in forms list API)
            attachments = form.get('attachments', {})
            debug_print(f"    Attachments found: {len(attachments)}")
            
            if attachments:
                forms_with_attachments += 1
                total_attachments += len(attachments)
                
                for attachment_name, attachment_info in attachments.items():
                    debug_print(f"      Processing attachment: {attachment_name}")
                    debug_print(f"      Attachment info type: {type(attachment_info)}")
                    debug_print(f"      Attachment info keys: {list(attachment_info.keys()) if isinstance(attachment_info, dict) else 'Not a dict'}")
                    
                    # Check if it's a photo file
                    if attachment_name.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp')):
                        photo_attachments += 1
                        debug_print(f"      [OK] Photo file detected: {attachment_name}")
                        
                        try:
                            # Get the download URL from attachment info
                            download_url = attachment_info.get('download_url')
                            if not download_url:
                                # Try alternative URL structure
                                download_url = attachment_info.get('url')
                            
                            debug_print(f"      Download URL: {download_url}")
                            
                            if download_url:
                                debug_print(f"      Downloading photo...")
                                # Download the photo
                                photo_response = requests.get(download_url, auth=(username, api_key), timeout=30)
                                photo_response.raise_for_status()
                                
                                # Extract question name from attachment name or form data
                                question_name = self._extract_question_name(attachment_name, form)
                                debug_print(f"      Question name: {question_name}")
                                
                                # Create filename in CommCare format with proper extension
                                # Determine file extension from original attachment name
                                file_ext = '.jpg'  # Default to .jpg
                                if attachment_name.lower().endswith('.jpeg'):
                                    file_ext = '.jpeg'
                                elif attachment_name.lower().endswith('.png'):
                                    file_ext = '.png'
                                elif attachment_name.lower().endswith('.gif'):
                                    file_ext = '.gif'
                                elif attachment_name.lower().endswith('.bmp'):
                                    file_ext = '.bmp'
                                
                                filename = f"api_photo-{question_name}-{user_id}-form_{form_id}{file_ext}"
                                file_path = download_dir / filename
                                
                                with open(file_path, 'wb') as f:
                                    f.write(photo_response.content)
                                
                                downloaded_photos.append(str(file_path))
                                photo_count += 1
                                
                                # Track photos per domain
                                if domain not in photos_per_domain:
                                    photos_per_domain[domain] = 0
                                photos_per_domain[domain] += 1
                                
                                debug_print(f"      [OK] Downloaded: {filename} ({len(photo_response.content)} bytes)")
                                
                            else:
                                print(f"      [ERROR] No download URL found for {attachment_name}")
                                
                        except requests.exceptions.Timeout:
                            print(f"      [ERROR] Download timeout for {attachment_name}")
                        except requests.exceptions.RequestException as e:
                            print(f"      [ERROR] Download failed for {attachment_name}: {e}")
                        except Exception as e:
                            print(f"      [ERROR] Error downloading {attachment_name}: {e}")
                            import traceback
                            print(f"      Traceback: {traceback.format_exc()}")
                    else:
                        debug_print(f"      [SKIP] Skipping non-photo file: {attachment_name}")
            else:
                debug_print(f"    No attachments in this form")
        
        print(f"Download summary:")
        print(f"  - Forms processed: {len(forms_to_process)} (limit {limit} per domain)")
        print(f"  - Forms with attachments: {forms_with_attachments}")
        print(f"  - Total attachments: {total_attachments}")
        print(f"  - Photo attachments: {photo_attachments}")
        print(f"  - Photos downloaded: {len(downloaded_photos)}")
        
        # Show photos per domain
        if photos_per_domain:
            print(f"  - Photos per domain:")
            for domain, count in photos_per_domain.items():
                print(f"    * {domain}: {count} photos")
        else:
            print(f"  - No photos downloaded from any domain")
        
        return downloaded_photos

    def _extract_question_name(self, attachment_name: str, form: dict) -> str:
        """Extract question name from form data by finding the key that has this attachment as its value"""
        # Try to find the question name in the form data
        form_data = form.get('form', {})
        if isinstance(form_data, dict):
            # Recursively search through nested dictionaries
            def find_question_in_data(data, path=""):
                if isinstance(data, dict):
                    for key, value in data.items():
                        current_path = f"{path}.{key}" if path else key
                        if isinstance(value, str) and value == attachment_name:
                            # Found the key that corresponds to this attachment
                            debug_print(f"      DEBUG: Found question key '{key}' for attachment '{attachment_name}' at path '{current_path}'")
                            return key
                        elif isinstance(value, str) and attachment_name in value:
                            # Partial match - the value contains the attachment name
                            debug_print(f"      DEBUG: Found partial match - key '{key}' contains attachment '{attachment_name}' at path '{current_path}'")
                            return key
                        elif isinstance(value, dict):
                            # Recursively search nested dictionaries
                            result = find_question_in_data(value, current_path)
                            if result:
                                return result
                return None
            
            # Search through the form data
            question_name = find_question_in_data(form_data)
            if question_name:
                return question_name
        
        # Fallback: use a cleaned version of the attachment name
        fallback_name = attachment_name.replace('.jpg', '').replace('.jpeg', '').replace('.png', '')
        debug_print(f"      DEBUG: Using fallback question name: {fallback_name}")
        return fallback_name

    def _process_downloaded_photos(self, downloaded_photos: list) -> None:
        """Process downloaded photos and update the GUI"""
        # Update the valid_metas with downloaded photos
        self.valid_metas = []
        for photo_path in downloaded_photos:
            # Create a PhotoMeta object for each downloaded photo
            from .filenames import PhotoMeta
            # Extract metadata from the filename
            photo_path_obj = Path(photo_path)
            filename = photo_path_obj.name
            extension = photo_path_obj.suffix.lstrip('.')
            
            # Try to parse the filename to extract metadata
            from .filenames import parse_commcare_filename
            parsed_meta = parse_commcare_filename(photo_path_obj)
            
            if parsed_meta:
                # Use parsed metadata
                meta = parsed_meta
            else:
                # Try to extract question name from filename
                # Expected format: test_photo-{question_name}-{user_id}-form_{form_uuid}.jpg
                # or: api_photo-{question_name}-{user_id}-form_{form_uuid}.jpg
                question_name = "api_photo"  # Default fallback
                if filename.startswith(('test_photo-', 'api_photo-')):
                    # Find the position of the second dash (after question_name)
                    parts = filename.split('-')
                    if len(parts) >= 3:
                        # The question name should be the second part (index 1)
                        question_name = parts[1]
                
                # Create a basic PhotoMeta with extracted question name
                meta = PhotoMeta(
                    json_block="api_download",
                    question_id=question_name,
                    user_id="unknown",
                    form_id="unknown",
                    extension=extension,
                    filename=filename,
                    filepath=photo_path_obj
                )
            self.valid_metas.append(meta)
        
        # Update the question filter
        # First populate question_options from the valid_metas
        from .scanner import group_by_question_id
        groups = group_by_question_id(self.valid_metas)
        self.question_options = sorted(groups.keys())
        self._refresh_question_menu()
        
        # Update status
        self.status_label.configure(text=f"Downloaded {len(downloaded_photos)} photos from API", text_color="green")

    def _get_api_data(self) -> None:
        """Handle API data loading with comprehensive error handling"""
        debug_print("=== Starting API Data Loading ===")
        
        # Validate API inputs
        api_file = self.api_file_var.get().strip()
        api_limit = self.api_limit_var.get().strip()
        
        print(f"API File: {api_file}")
        print(f"API Limit: {api_limit}")
        
        # Get date values from text entries and convert MM/DD/YY to YYYY-MM-DD
        date_start = self._convert_date_format(self.date_start_var.get().strip())
        date_end = self._convert_date_format(self.date_end_var.get().strip())
        
        debug_print(f"Date Start: {self.date_start_var.get().strip()} -> {date_start}")
        debug_print(f"Date End: {self.date_end_var.get().strip()} -> {date_end}")

        
        if not date_start or not date_end:
            error_msg = "Please enter valid dates in MM/DD/YY format."
            print(f"[ERROR] Date validation failed: {error_msg}")
            from tkinter import messagebox
            messagebox.showwarning("Invalid Date", error_msg)
            return
        
        if not all([api_file, api_limit]):
            error_msg = "Please fill in the domain/app file and API limit."
            print(f"[ERROR] Missing inputs: {error_msg}")
            from tkinter import messagebox
            messagebox.showwarning("Missing", error_msg)
            return
            
        try:
            limit = int(api_limit)
            if not (20 <= limit <= 1000):
                error_msg = "API limit must be between 20 and 1000."
                print(f"[ERROR] Invalid limit: {error_msg}")
                from tkinter import messagebox
                messagebox.showwarning("Invalid", error_msg)
                return
            debug_print(f"[OK] API limit validated: {limit}")
        except ValueError:
            error_msg = "API limit must be a number."
            print(f"[ERROR] Invalid limit format: {error_msg}")
            from tkinter import messagebox
            messagebox.showwarning("Invalid", error_msg)
            return
        
        try:
            debug_print("=== Parsing Domain/App Pairs ===")
            # Parse domain/app pairs file
            domain_form_pairs = self._parse_domain_form_file(api_file)
            if not domain_form_pairs:
                error_msg = "Could not parse domain/app pairs file."
                print(f"[ERROR] Parse failed: {error_msg}")
                from tkinter import messagebox
                messagebox.showerror("Error", error_msg)
                return
            debug_print(f"Parsed {len(domain_form_pairs)} domain/app pairs: {list(domain_form_pairs.keys())}")
            
            debug_print("=== Finding .env File ===")
            # Find .env file
            env_file = self._find_env_file()
            if not env_file:
                error_msg = "Could not find .env file."
                print(f"[ERROR] .env file not found: {error_msg}")
                from tkinter import messagebox
                messagebox.showerror("Error", error_msg)
                return
            debug_print(f"Found .env file: {env_file}")
            
            debug_print("=== Loading API Credentials ===")
            # Load API credentials
            api_username, api_key = self._load_api_credentials(env_file)
            if not api_username or not api_key:
                error_msg = "Could not load API credentials from .env file."
                print(f"[ERROR] Credentials not found: {error_msg}")
                from tkinter import messagebox
                messagebox.showerror("Error", error_msg)
                return
            debug_print(f"Loaded credentials: Username={api_username[:3]}..., Key={api_key[:8]}...")
            
            debug_print("=== Getting Forms from API ===")
            # Get forms from API
            forms_data = self._get_forms_from_api(domain_form_pairs, date_start, date_end, api_username, api_key, limit)
            if not forms_data:
                error_msg = "No forms found for the specified criteria."
                print(f"[ERROR] No forms found: {error_msg}")
                print("Debug info:")
                print(f"  - Date range: {date_start} to {date_end}")
                print(f"  - Domains: {list(domain_form_pairs.keys())}")
                print(f"  - Limit: {limit}")
                from tkinter import messagebox
                messagebox.showwarning("No Data", error_msg)
                return
            debug_print(f"Found {len(forms_data)} forms from API")
            
            debug_print("=== Downloading Attachments ===")
            # Download attachments
            downloaded_photos = self._download_attachments(forms_data, limit, api_username, api_key)
            if not downloaded_photos:
                error_msg = "No photos found in the downloaded forms."
                print(f"[ERROR] No photos downloaded: {error_msg}")
                print("Debug info:")
                print(f"  - Forms processed: {len(forms_data)}")
                print(f"  - Forms with attachments: {sum(1 for form in forms_data if form.get('attachments'))}")
                from tkinter import messagebox
                messagebox.showwarning("No Photos", error_msg)
                return
            debug_print(f"Downloaded {len(downloaded_photos)} photos")
            
            debug_print("=== Processing Downloaded Photos ===")
            # Process downloaded photos
            self._process_downloaded_photos(downloaded_photos)
            
            # Update status
            self.status_label.configure(text=f"Downloaded {len(downloaded_photos)} photos from API", text_color="green")
            print(f"[OK] API data loading completed successfully!")
            
        except Exception as e:
            error_msg = f"Error during API data loading: {str(e)}"
            print(f"[ERROR] Unexpected error: {error_msg}")
            print(f"Exception type: {type(e).__name__}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            
            # Check if we have any downloaded photos to work with
            if 'downloaded_photos' in locals() and downloaded_photos:
                print(f"[INFO] Found {len(downloaded_photos)} photos despite error - proceeding with review")
                from tkinter import messagebox
                result = messagebox.askyesno(
                    "API Error", 
                    f"{error_msg}\n\nHowever, {len(downloaded_photos)} photos were successfully downloaded.\n\nWould you like to proceed with the review using these photos?"
                )
                if result:
                    print("=== Processing Downloaded Photos (After Error) ===")
                    # Process downloaded photos with error handling
                    try:
                        self._process_downloaded_photos(downloaded_photos)
                        
                        # Update status
                        self.status_label.configure(text=f"Downloaded {len(downloaded_photos)} photos from API (with errors)", text_color="orange")
                        print(f"[OK] Proceeding with {len(downloaded_photos)} photos despite API error!")
                        return
                    except Exception as process_error:
                        print(f"[ERROR] Failed to process downloaded photos: {process_error}")
                        from tkinter import messagebox
                        messagebox.showerror("Processing Error", f"Failed to process downloaded photos: {process_error}")
                        return
                else:
                    return
            else:
                from tkinter import messagebox
                messagebox.showerror("API Error", error_msg)
                return


def find_env_file() -> str:
    """Find the .env file - first check current directory, then Coverage directories"""
    import os
    from pathlib import Path
    
    # First priority: Check for .env file in current photo_utility directory
    current_env = Path.cwd() / ".env"
    if current_env.exists():
        debug_print(f"  Found .env file in current directory: {current_env}")
        return str(current_env)
    
    # Second priority: Search for Coverage folder in common locations
    home_dir = Path.home()
    
    search_paths = [
        home_dir / "Documents" / "Coverage" / ".env",
        home_dir / "Coverage" / ".env",
        home_dir / "Documents" / "Coverage" / "Coverage" / ".env",  # Nested Coverage folder
        Path.cwd() / "Coverage" / ".env",  # Current working directory
    ]
    
    # Also search for any Coverage folder in Documents
    documents_dir = home_dir / "Documents"
    if documents_dir.exists():
        for item in documents_dir.iterdir():
            if item.is_dir() and item.name.lower() == "coverage":
                search_paths.append(item / ".env")
    
    # Check each potential path
    for env_path in search_paths:
        if env_path.exists():
            print(f"  Found .env file at: {env_path}")
            return str(env_path)
    
    return ""


def run_app() -> None:
    app = App()
    app.mainloop()
