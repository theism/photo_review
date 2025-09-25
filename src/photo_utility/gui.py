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

from .scanner import scan_directory_for_photos, group_by_question_id, group_by_form_id


class App(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Photo Review Utility")
        self.geometry("800x600")
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        self.dir_var = ctk.StringVar()
        self.status_var = ctk.StringVar(value="")
        self.buckets_var = ctk.StringVar(value="Real, Fake")
        self.percent_var = ctk.StringVar(value="10.0")  # Use StringVar to avoid conversion errors
        self.include_known_bad_var = ctk.BooleanVar(value=False)
        self.known_bad_dir_var = ctk.StringVar()
        self.known_bad_count_var = ctk.StringVar(value="5")  # Number of bad photos to insert
        self.path_mode_var = ctk.StringVar(value="local")  # local or api
        self.reviewer_name_var = ctk.StringVar()

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

        # Path selector (placeholder for Path B)
        mode_row = ctk.CTkFrame(frm)
        mode_row.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(mode_row, text="Data Source:").pack(side="left")
        ctk.CTkRadioButton(mode_row, text="Local directory", variable=self.path_mode_var, value="local").pack(side="left", padx=(6, 0))
        ctk.CTkRadioButton(mode_row, text="CommCare API (coming soon)", variable=self.path_mode_var, value="api").pack(side="left", padx=(6, 0))

        # Status text below data source
        self.status_label = ctk.CTkLabel(frm, text="Select a directory and click 'Check Photo Data'", text_color="gray")
        self.status_label.pack(anchor="w", pady=(0, 8))

        row1 = ctk.CTkFrame(frm)
        row1.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(row1, text="Local directory:").pack(side="left")
        ctk.CTkEntry(row1, textvariable=self.dir_var, width=400).pack(side="left", padx=6)
        ctk.CTkButton(row1, text="Browse", command=self._browse_dir, width=80).pack(side="left", padx=6)

        row2 = ctk.CTkFrame(frm)
        row2.pack(fill="x", pady=(0, 8))
        ctk.CTkButton(row2, text="Check Photo Data", command=self._get_data, width=120).pack(side="left")

        row3 = ctk.CTkFrame(frm)
        row3.pack(fill="x", pady=(0, 0))
        ctk.CTkLabel(row3, text="Photo filter (multi-select):").pack(anchor="w", pady=(8, 4))
        
        # Use a regular Tkinter Listbox with CustomTkinter styling
        import tkinter as tk
        listbox_frame = ctk.CTkFrame(row3)
        listbox_frame.pack(fill="x", padx=8, pady=(0, 8))
        
        self.question_listbox = tk.Listbox(listbox_frame, height=4, selectmode=tk.MULTIPLE, font=("Arial", 12))
        self.question_listbox.pack(fill="x", padx=4, pady=4)
        self.question_listbox.bind("<<ListboxSelect>>", self._on_question_select)
        self.question_checkboxes = {}  # Keep for compatibility but won't be used

        row4 = ctk.CTkFrame(frm)
        row4.pack(fill="x", pady=(0, 0))
        ctk.CTkLabel(row4, text="List desired photo buckets (comma-separated):").pack(side="left")
        ctk.CTkEntry(row4, textvariable=self.buckets_var, width=300).pack(side="left", padx=6)

        row5 = ctk.CTkFrame(frm)
        row5.pack(fill="x", pady=(8, 0))
        ctk.CTkLabel(row5, text="Percent of pictures to review:").pack(side="left")
        self.percent_entry = ctk.CTkEntry(row5, textvariable=self.percent_var, width=80)
        self.percent_entry.pack(side="left", padx=6)
        self.percent_entry.bind("<KeyRelease>", lambda e: self._update_percent_count())
        self.percent_count_label = ctk.CTkLabel(row5, text="")
        self.percent_count_label.pack(side="left", padx=(12, 0))

        row6 = ctk.CTkFrame(frm)
        row6.pack(fill="x", pady=(8, 0))
        ctk.CTkCheckBox(row6, text="Include known bad photos", variable=self.include_known_bad_var, command=self._toggle_known_bad_controls).pack(side="left")

        self.row7_kb = ctk.CTkFrame(frm)
        self.row7_kb.pack(fill="x", pady=(4, 0))
        ctk.CTkLabel(self.row7_kb, text="Known bad photo directory:").pack(side="left")
        self.kb_entry = ctk.CTkEntry(self.row7_kb, textvariable=self.known_bad_dir_var, width=300)
        self.kb_entry.pack(side="left", padx=6)
        ctk.CTkButton(self.row7_kb, text="Browse", command=self._browse_known_bad_dir, width=80).pack(side="left", padx=6)
        
        # Known bad count input
        self.row8_kb = ctk.CTkFrame(frm)
        self.row8_kb.pack(fill="x", pady=(4, 0))
        ctk.CTkLabel(self.row8_kb, text="Enter number of bad photos to randomly insert:").pack(side="left")
        ctk.CTkEntry(self.row8_kb, textvariable=self.known_bad_count_var, width=60).pack(side="left", padx=6)

        # Removed the ratio control per request

        row9 = ctk.CTkFrame(frm)
        row9.pack(fill="x", pady=(12, 0))
        ctk.CTkButton(row9, text="Start Review", command=self._build_set, width=120).pack(side="left")

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
            self.row7_kb.forget()
            self.row8_kb.forget()

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
            kb_dir = Path(self.known_bad_dir_var.get().strip())
            if not kb_dir or not kb_dir.exists() or not kb_dir.is_dir():
                messagebox.showerror("Known bad", "Select a valid known bad directory.")
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
        # Clear existing items
        self.question_listbox.delete(0, "end")
        
        # Get photo counts for each question
        groups = group_by_question_id(self.valid_metas)
        
        # Add items to listbox with photo counts
        for opt in self.question_options:
            count = len(groups.get(opt, []))
            self.question_listbox.insert("end", f"{opt} ({count} photos)")
        
        # Select all items by default
        if self.question_options:
            for i in range(len(self.question_options)):
                self.question_listbox.selection_set(i)
        
        # Update selection state
        self._on_question_select()

    def _on_question_select(self, event=None) -> None:
        # Get selected indices from listbox
        selected_indices = self.question_listbox.curselection()
        self._selected_questions = []
        
        for idx in selected_indices:
            if idx < len(self.question_options):
                self._selected_questions.append(self.question_options[idx])
        
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
        # Re-set state and restore previous selections
        self._refresh_question_menu()
        # Restore previous selections in listbox
        if hasattr(self, '_last_selected_questions') and self._last_selected_questions:
            for i, question in enumerate(self.question_options):
                if question in self._last_selected_questions:
                    self.question_listbox.selection_set(i)
                else:
                    self.question_listbox.selection_clear(i)
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
                            print(f"Loaded reviewer name: {name}")  # Debug output
                    elif line.startswith("last_directory:"):
                        directory = line.split(":", 1)[1].strip()
                        if directory:
                            self.dir_var.set(directory)
                    elif line.startswith("known_bad_count:"):
                        count = line.split(":", 1)[1].strip()
                        if count:
                            self.known_bad_count_var.set(count)
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
                    print(f"Saved reviewer name: {reviewer_name}")  # Debug output
                
                # Save last directory
                last_dir = self.dir_var.get().strip()
                if last_dir:
                    f.write(f"last_directory:{last_dir}\n")
                    print(f"Saved last directory: {last_dir}")  # Debug output
                
                # Save known bad count
                kb_count = self.known_bad_count_var.get().strip()
                if kb_count:
                    f.write(f"known_bad_count:{kb_count}\n")
                    print(f"Saved known bad count: {kb_count}")  # Debug output
        except Exception as e:
            print(f"Error saving settings: {e}")  # Debug output


def run_app() -> None:
    app = App()
    app.mainloop()
