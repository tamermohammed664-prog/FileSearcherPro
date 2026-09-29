import os
import csv
import queue
import threading
import shutil
from io import BytesIO
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image, ImageSequence
import PyPDF2

class FileSearcherPro:
    def __init__(self, root):
        self.root = root
        self.root.title("File Searcher Pro")
        self.root.geometry("650x680")
        self.root.minsize(620, 680)
        if isinstance(self.root, ctk.CTk):
            self.root.configure(fg_color="#0d1117")
        else:
            self.root.configure(bg="#0d1117")

        # Variables
        self.names_list_path = tk.StringVar()
        self.search_path = tk.StringVar()
        self.dest_path = tk.StringVar()

        self.organize_customer = tk.BooleanVar()
        self.move_files = tk.BooleanVar()
        self.exact_match = tk.BooleanVar()
        self.search_subfolders = tk.BooleanVar(value=True)
        self.case_sensitive = tk.BooleanVar()
        self.merge_pdf = tk.BooleanVar()  # الميزة الجديدة 1
        self.export_found_paths = tk.BooleanVar()
        
        self.extensions = tk.StringVar(value=".jpg, .jpeg, .pdf, .tif, .tiff, .png")
        self.event_queue = queue.Queue()
        self.cancel_event = threading.Event()
        self.worker_thread = None
        self.path_controls = []
        self.found_source_paths = []
        self.log_messages = []

        self.configure_styles()
        self.build_gui()

    def configure_styles(self):
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.colors = {
            "background": "#0d1117",
            "surface": "#1c2333",
            "surface_alt": "#252f43",
            "input": "#111827",
            "border": "#303b50",
            "text": "#e1e7ef",
            "muted": "#9aa7b8",
            "accent": "#2563eb",
            "accent_hover": "#3b82f6",
            "start": "#10b981",
            "start_hover": "#059669",
            "cancel": "#ef4444",
            "cancel_hover": "#dc2626",
            "success": "#34d399",
            "warning": "#fbbf24",
            "error": "#fb7185",
        }
        self.font_title = ctk.CTkFont(family="TkDefaultFont", size=22, weight="bold")
        self.font_section = ctk.CTkFont(family="TkDefaultFont", size=10, weight="bold")
        self.font_body = ctk.CTkFont(family="TkDefaultFont", size=12)
        self.font_small = ctk.CTkFont(family="TkDefaultFont", size=10)
        self.progress_mode = "determinate"

    def build_gui(self):
        self.main_frame = ctk.CTkFrame(self.root, fg_color="transparent", corner_radius=0)
        self.main_frame.pack(fill="both", expand=True, padx=18, pady=10)

        header = ctk.CTkFrame(self.main_frame, fg_color="transparent", corner_radius=0)
        header.pack(fill="x", pady=(0, 8))
        title_block = ctk.CTkFrame(header, fg_color="transparent", corner_radius=0)
        title_block.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(title_block, text="File Searcher Pro", text_color=self.colors["text"], font=self.font_title).pack(anchor="w")
        ctk.CTkLabel(title_block, text="Search, organize, and merge files in one pass", text_color=self.colors["muted"], font=self.font_small).pack(anchor="w", pady=(3, 0))
        self.create_temo_badge(header)

        _, _, locations_body = self.create_section(self.main_frame, "01   Locations")
        self.path_parent = locations_body
        self.create_path_row(self.names_list_path, "Names list", self.browse_names_list)
        self.create_path_row(self.search_path, "Search in", self.browse_search_path)
        self.create_path_row(self.dest_path, "Save to", self.browse_dest_path)

        _, _, options_body = self.create_section(self.main_frame, "02   Search options")
        self.options_frame = ctk.CTkFrame(options_body, fg_color="transparent", corner_radius=0)
        self.options_frame.pack(fill="x")
        for column in range(2):
            self.options_frame.grid_columnconfigure(column, weight=1)

        checkbox_style = {
            "checkbox_width": 19,
            "checkbox_height": 19,
            "corner_radius": 5,
            "border_width": 2,
            "fg_color": self.colors["accent"],
            "hover_color": self.colors["accent_hover"],
            "border_color": self.colors["border"],
            "checkmark_color": "#ffffff",
            "text_color": self.colors["text"],
            "text_color_disabled": self.colors["muted"],
            "font": self.font_body,
        }
        self.organize_checkbox = ctk.CTkCheckBox(self.options_frame, text="Organize in customer folders", variable=self.organize_customer, **checkbox_style)
        self.organize_checkbox.grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        self.move_checkbox = ctk.CTkCheckBox(self.options_frame, text="Move files instead of copying", variable=self.move_files, **checkbox_style)
        self.move_checkbox.grid(row=0, column=1, sticky="w", pady=4)
        self.exact_checkbox = ctk.CTkCheckBox(self.options_frame, text="Exact filename match", variable=self.exact_match, **checkbox_style)
        self.exact_checkbox.grid(row=1, column=0, sticky="w", padx=(0, 8), pady=4)
        self.subfolders_checkbox = ctk.CTkCheckBox(self.options_frame, text="Search subfolders", variable=self.search_subfolders, **checkbox_style)
        self.subfolders_checkbox.grid(row=1, column=1, sticky="w", pady=4)
        self.merge_checkbox = ctk.CTkCheckBox(
            self.options_frame,
            text="Merge line items into one PDF per line",
            variable=self.merge_pdf,
            **checkbox_style,
        )
        self.merge_checkbox.grid(row=2, column=0, columnspan=2, sticky="w", pady=4)
        self.export_paths_checkbox = ctk.CTkCheckBox(
            self.options_frame,
            text="Export found source paths after search",
            variable=self.export_found_paths,
            **checkbox_style,
        )
        self.export_paths_checkbox.grid(row=3, column=0, columnspan=2, sticky="w", pady=4)
        self.options_frame.grid_columnconfigure(0, weight=1)
        self.options_frame.grid_columnconfigure(1, weight=1)
        self.merge_pdf.trace_add("write", self.update_mode_controls)

        _, _, extensions_body = self.create_section(self.main_frame, "03   File types")
        self.extensions_frame = ctk.CTkFrame(extensions_body, fg_color="transparent", corner_radius=0)
        self.extensions_frame.pack(fill="x")
        ctk.CTkLabel(self.extensions_frame, text="Extensions", text_color=self.colors["muted"], font=self.font_small).pack(side="left", padx=(0, 12))
        self.extensions_entry = ctk.CTkEntry(
            self.extensions_frame,
            textvariable=self.extensions,
            width=230,
            height=38,
            corner_radius=9,
            border_width=1,
            fg_color=self.colors["input"],
            border_color=self.colors["border"],
            text_color=self.colors["text"],
            font=self.font_body,
        )
        self.extensions_entry.pack(side="left")
        self.case_checkbox = ctk.CTkCheckBox(self.extensions_frame, text="Case sensitive", variable=self.case_sensitive, **checkbox_style)
        self.case_checkbox.pack(side="left", padx=(14, 0))

        action_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent", corner_radius=0)
        action_frame.pack(fill="x", pady=(1, 0))
        action_frame.grid_columnconfigure(0, weight=7, uniform="actions")
        action_frame.grid_columnconfigure(1, weight=3, uniform="actions")
        self.start_button = ctk.CTkButton(
            action_frame,
            text="START SEARCH",
            height=40,
            corner_radius=10,
            fg_color=self.colors["start"],
            hover_color=self.colors["start_hover"],
            text_color="#ffffff",
            font=ctk.CTkFont(family="TkDefaultFont", size=12, weight="bold"),
            command=self.start_process,
        )
        self.start_button.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self.cancel_button = ctk.CTkButton(
            action_frame,
            text="CANCEL",
            height=40,
            corner_radius=10,
            fg_color=self.colors["cancel"],
            hover_color=self.colors["cancel_hover"],
            text_color="#ffffff",
            text_color_disabled=self.colors["muted"],
            font=ctk.CTkFont(family="TkDefaultFont", size=11, weight="bold"),
            command=self.cancel_process,
            state=tk.DISABLED,
        )
        self.cancel_button.grid(row=0, column=1, sticky="ew", padx=(5, 0))
        self.progress = ctk.CTkProgressBar(
            self.main_frame,
            height=9,
            corner_radius=6,
            mode="determinate",
            fg_color=self.colors["surface_alt"],
            progress_color=self.colors["accent"],
        )
        self.progress.pack(fill="x", pady=(8, 0))
        self.progress.set(0)
        self.update_mode_controls()

    def create_temo_badge(self, parent):
        badge = ctk.CTkFrame(parent, fg_color="transparent", corner_radius=0)
        badge.pack(side="right", anchor="center", padx=(12, 0), pady=2)
        self.temo_badge = badge

        project_dir = os.path.dirname(os.path.abspath(__file__))
        logo_paths = ("log.jpeg", "logo.png")
        self.temo_logo_image = None
        for filename in logo_paths:
            image_path = os.path.join(project_dir, filename)
            if not os.path.isfile(image_path):
                continue
            try:
                with Image.open(image_path) as source_image:
                    image = source_image.convert("RGBA")
                resampling = getattr(Image, "Resampling", Image).LANCZOS
                image.thumbnail((140, 38), resampling)
                self.temo_logo_image = ctk.CTkImage(
                    light_image=image,
                    dark_image=image,
                    size=image.size,
                )
                self.temo_logo_label = ctk.CTkLabel(badge, text="", image=self.temo_logo_image)
                self.temo_logo_label.pack()
                return
            except (OSError, ValueError):
                continue

        brand_copy = ctk.CTkFrame(badge, fg_color="transparent", corner_radius=0)
        brand_copy.pack(anchor="e")
        self.temo_title_label = ctk.CTkLabel(
            brand_copy,
            text="TEMO",
            text_color="#ffffff",
            font=ctk.CTkFont(family="TkDefaultFont", size=14, weight="bold"),
            anchor="e",
        )
        self.temo_title_label.pack(anchor="e")
        self.temo_tagline_label = ctk.CTkLabel(
            brand_copy,
            text="Technology That Helps You",
            text_color="#9ca3af",
            font=ctk.CTkFont(family="TkDefaultFont", size=10),
            anchor="e",
        )
        self.temo_tagline_label.pack(anchor="e", pady=(0, 1))
    def create_section(self, parent, title, expand=False):
        card = ctk.CTkFrame(
            parent,
            fg_color=self.colors["surface"],
            corner_radius=14,
            border_width=1,
            border_color=self.colors["border"],
        )
        card.pack(fill="both" if expand else "x", expand=expand, pady=(0, 12))
        header = ctk.CTkFrame(card, fg_color="transparent", corner_radius=0)
        header.pack(fill="x", padx=16, pady=(12, 7))
        ctk.CTkLabel(header, text=title.upper(), text_color=self.colors["muted"], font=self.font_section).pack(side="left")
        body = ctk.CTkFrame(card, fg_color="transparent", corner_radius=0)
        body.pack(fill="both" if expand else "x", expand=expand, padx=16, pady=(0, 14))
        return card, header, body

    def create_path_row(self, var, btn_text, cmd):
        frame = ctk.CTkFrame(self.path_parent, fg_color="transparent", corner_radius=0)
        frame.pack(fill="x", pady=4)
        ctk.CTkLabel(frame, text=btn_text, text_color=self.colors["muted"], font=self.font_small, width=88, anchor="w").pack(side="left", anchor="w")
        entry = ctk.CTkEntry(
            frame,
            textvariable=var,
            width=330,
            height=38,
            corner_radius=9,
            border_width=1,
            fg_color=self.colors["input"],
            border_color=self.colors["border"],
            text_color=self.colors["text"],
            placeholder_text=f"Select {btn_text.lower()}...",
            font=self.font_body,
        )
        button = ctk.CTkButton(
            frame,
            text="Browse",
            width=82,
            height=38,
            corner_radius=9,
            fg_color=self.colors["accent"],
            hover_color=self.colors["accent_hover"],
            text_color="#ffffff",
            font=self.font_small,
            command=cmd,
        )
        button.pack(side="right")
        entry.pack(side="left", fill="x", expand=True, padx=(0, 7))
        self.path_controls.extend((entry, button))

    def browse_names_list(self):
        filename = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")])
        if filename: self.names_list_path.set(filename)

    def browse_search_path(self):
        folder = filedialog.askdirectory()
        if folder: self.search_path.set(folder)

    def browse_dest_path(self):
        folder = filedialog.askdirectory()
        if folder: self.dest_path.set(folder)

    def log(self, text):
        self.last_log_message = str(text)

    def clear_log(self):
        self.last_log_message = ""

    def update_mode_controls(self, *_args):
        state = tk.DISABLED if self.merge_pdf.get() else tk.NORMAL
        self.organize_checkbox.configure(state=state)
        self.move_checkbox.configure(state=state)

    def _set_input_controls_enabled(self, enabled):
        state = tk.NORMAL if enabled else tk.DISABLED
        for control in self.path_controls:
            control.configure(state=state)
        for frame in (self.options_frame, self.extensions_frame):
            for control in frame.winfo_children():
                if isinstance(control, (ctk.CTkCheckBox, ctk.CTkEntry)):
                    control.configure(state=state)
        if enabled:
            self.update_mode_controls()

    def cancel_process(self):
        if self.worker_thread and self.worker_thread.is_alive():
            self.cancel_event.set()
            self.cancel_button.configure(state=tk.DISABLED)
            self.set_status("Status: Cancelling...", self.colors["warning"])

    def set_status(self, text, color=None):
        if color is None:
            if text.startswith("Status: Failed"):
                color = self.colors["error"]
            elif text.startswith("Status: Cancel"):
                color = self.colors["warning"]
            elif text.startswith("Status: Completed") and not text.endswith("(0 errors)"):
                color = self.colors["warning"]
            elif text.startswith("Status: Completed") or text == "Status: Ready":
                color = self.colors["success"]
            else:
                color = self.colors["accent_hover"]
        self.current_status = text

    def start_process(self):
        if self.worker_thread and self.worker_thread.is_alive():
            return

        names_file = self.names_list_path.get()
        search_dir = self.search_path.get()
        dest_dir = self.dest_path.get()

        if not names_file or not search_dir or not dest_dir:
            messagebox.showerror("Error", "Please fill all required paths!")
            return

        if not os.path.isfile(names_file):
            messagebox.showerror("Error", "The names list file does not exist.")
            return
        if not os.path.isdir(search_dir):
            messagebox.showerror("Error", "The search path does not exist or is not a folder.")
            return

        self.clear_log()
        self.log(">>> Starting Search...")
        options = {
            "valid_exts": {extension.strip().lower() for extension in self.extensions.get().split(",") if extension.strip()},
            "case_sensitive": self.case_sensitive.get(),
            "exact_match": self.exact_match.get(),
            "search_subfolders": self.search_subfolders.get(),
            "merge_pdf": self.merge_pdf.get(),
            "organize_customer": self.organize_customer.get(),
            "move_files": self.move_files.get(),
            "export_found_paths": self.export_found_paths.get(),
        }
        self.cancel_event.clear()
        self.found_source_paths = []
        self.set_status("Status: Starting...")
        self._set_input_controls_enabled(False)
        self.start_button.configure(state=tk.DISABLED)
        self.cancel_button.configure(state=tk.NORMAL)
        self.progress.stop()
        self.progress.configure(mode="determinate")
        self.progress_mode = "determinate"
        self.progress.set(0)
        self.worker_thread = threading.Thread(
            target=self._process_files,
            args=(names_file, search_dir, dest_dir, options),
            daemon=True,
        )
        self.worker_thread.start()
        self.root.after(100, self._poll_worker)

    def _process_files(self, names_file, search_dir, dest_dir, options):
        emit_log = lambda text: self.event_queue.put(("log", text))
        errors = 0
        found_count = 0
        missing_count = 0
        counted_paths = set()
        not_found_lines = []
        found_source_paths = []
        found_path_keys = set()
        reserved_destinations = set()
        handled_moves = set()

        try:
            valid_exts = options["valid_exts"]
            with open(names_file, "r", encoding="utf-8") as names_handle:
                lines = []
                for source_line in names_handle:
                    source_line = source_line.rstrip("\r\n")
                    if source_line.strip():
                        lines.append(source_line)

            os.makedirs(dest_dir, exist_ok=True)

            emit_log("Indexing files in search path...")
            self.event_queue.put(("indeterminate", "Indexing files..."))
            file_map = {}
            def on_walk_error(error):
                nonlocal errors
                errors += 1
                emit_log(f"[ERROR] Could not read folder {error.filename}: {error}")

            for root_dir, _, files in os.walk(search_dir, onerror=on_walk_error):
                if self.cancel_event.is_set():
                    break
                for filename in files:
                    extension = os.path.splitext(filename)[1].lower()
                    if extension not in valid_exts:
                        continue
                    key = filename if options["case_sensitive"] else filename.lower()
                    file_map.setdefault(key, []).append(os.path.join(root_dir, filename))
                if not options["search_subfolders"]:
                    break

            indexed_count = sum(len(paths) for paths in file_map.values())
            emit_log(f"Indexed {indexed_count} matching files.")
            total_lines = len(lines)
            self.event_queue.put(("progress", (0, max(total_lines, 1), "Starting...")))

            for idx, line in enumerate(lines):
                if self.cancel_event.is_set():
                    break

                fields = [field.strip() for field in next(csv.reader([line])) if field.strip()]
                client_name = None
                if options["organize_customer"]:
                    numeric_fields = [field for field in fields if field.isdigit()]
                    client_fields = [field for field in fields if not field.isdigit()]
                    client_name = " ".join(client_fields).strip() or (fields[0] if fields else None)
                    items = numeric_fields or fields
                else:
                    items = fields
                matched_files = []
                line_has_missing_item = False
                for item in items:
                    if self.cancel_event.is_set():
                        break
                    target_item = item if options["case_sensitive"] else item.lower()
                    found_paths = []
                    for file_key, paths in file_map.items():
                        if self.cancel_event.is_set():
                            break
                        filename_stem = os.path.splitext(file_key)[0]
                        is_match = filename_stem == target_item if options["exact_match"] else target_item in file_key
                        if is_match:
                            found_paths.extend(paths)

                    if found_paths:
                        for found_path in found_paths:
                            matched_files.append((item, found_path))
                            found_key = os.path.normcase(os.path.abspath(found_path))
                            if found_key not in counted_paths:
                                counted_paths.add(found_key)
                                found_count += 1
                            emit_log(f"[FOUND] {item} -> {found_path}")
                    else:
                        line_has_missing_item = True
                        missing_count += 1
                        emit_log(f"[NOT FOUND] {line}")

                if line_has_missing_item:
                    not_found_lines.append(line)

                if self.cancel_event.is_set():
                    break

                if options["merge_pdf"] and matched_files:
                    safe_item = self._safe_component(items[0] if items else "items")
                    pdf_path = self._unique_destination(
                        os.path.join(dest_dir, f"{safe_item}.pdf"),
                        reserved_destinations,
                    )
                    try:
                        self.create_pdf_from_files([path for _, path in matched_files], pdf_path)
                        for _, source_path in matched_files:
                            source_key = os.path.normcase(os.path.abspath(source_path))
                            if source_key not in found_path_keys:
                                found_path_keys.add(source_key)
                                found_source_paths.append(source_path)
                        emit_log(f"[CREATED] {pdf_path}")
                    except Exception as error:
                        errors += 1
                        emit_log(f"[ERROR] Could not create {pdf_path}: {error}")

                elif not options["merge_pdf"]:
                    for item, source_path in matched_files:
                        source_key = os.path.normcase(os.path.abspath(source_path))
                        if options["move_files"] and source_key in handled_moves:
                            emit_log(f"[SKIPPED] Already moved: {source_path}")
                            continue

                        folder_name = self._safe_component(client_name or item)
                        target_folder = os.path.join(dest_dir, folder_name) if options["organize_customer"] else dest_dir
                        destination_path = os.path.join(target_folder, os.path.basename(source_path))
                        if os.path.normcase(os.path.abspath(source_path)) == os.path.normcase(os.path.abspath(destination_path)):
                            emit_log(f"[SKIPPED] Already at destination: {source_path}")
                            if options["move_files"]:
                                handled_moves.add(source_key)
                            continue
                        destination_path = self._unique_destination(destination_path, reserved_destinations)

                        try:
                            os.makedirs(target_folder, exist_ok=True)
                            if options["move_files"]:
                                shutil.move(source_path, destination_path)
                                handled_moves.add(source_key)
                            else:
                                shutil.copy2(source_path, destination_path)
                            if source_key not in found_path_keys:
                                found_path_keys.add(source_key)
                                found_source_paths.append(source_path)
                            emit_log(f"[SAVED] {destination_path}")
                        except OSError as error:
                            errors += 1
                            emit_log(f"[ERROR] Could not save {source_path}: {error}")

                self.event_queue.put(("progress", (idx + 1, max(total_lines, 1), f"Processing line {idx + 1}/{total_lines}")))

            if options["export_found_paths"]:
                paths_report = os.path.join(dest_dir, "found_files_paths.txt")
                with open(paths_report, "w", encoding="utf-8") as paths_file:
                    if found_source_paths:
                        paths_file.write("\n".join(found_source_paths) + "\n")
                emit_log(f"Found paths saved: {paths_report}")

            outcome = "cancelled" if self.cancel_event.is_set() else "finished"
            self.event_queue.put((outcome, {
                "errors": errors,
                "found_count": found_count,
                "missing_count": missing_count,
                "not_found_lines": not_found_lines,
                "found_paths": found_source_paths,
            }))
        except Exception as error:
            self.event_queue.put(("failed", str(error)))

    def _poll_worker(self):
        finished = False
        for _ in range(200):
            try:
                event, data = self.event_queue.get_nowait()
            except queue.Empty:
                break

            if event == "log":
                self.log(data)
            elif event == "indeterminate":
                self.progress.configure(mode="indeterminate")
                self.progress_mode = "indeterminate"
                self.progress.start()
                self.set_status(f"Status: {data}", self.colors["accent_hover"])
            elif event == "progress":
                value, maximum, status = data
                if self.progress_mode == "indeterminate":
                    self.progress.stop()
                    self.progress.configure(mode="determinate")
                    self.progress_mode = "determinate"
                self.progress.set(value / maximum if maximum else 0)
                self.set_status(f"Status: {status}", self.colors["accent_hover"])
            elif event in ("finished", "cancelled"):
                errors = data["errors"]
                self.found_source_paths = data["found_paths"]
                status_text = "Status: Cancelled" if event == "cancelled" else f"Status: Completed ({errors} errors)"
                self.set_status(status_text)
                summary = (
                    f"Files found: {data['found_count']}\n"
                    f"Items with no matching files: {data['missing_count']}"
                )
                if data["not_found_lines"]:
                    summary += "\n\nUnmatched source lines:\n" + "\n".join(data["not_found_lines"])
                if errors:
                    summary += f"\nFile errors: {errors}"
                if event == "cancelled":
                    messagebox.showinfo("Cancelled", f"Processing stopped. Completed results were kept.\n\n{summary}")
                elif errors:
                    messagebox.showwarning("Completed with errors", summary)
                else:
                    messagebox.showinfo("Done", summary)
                finished = True
            elif event == "failed":
                self.set_status("Status: Failed")
                messagebox.showerror("Processing Error", data)
                finished = True

        if finished:
            self.worker_thread = None
            self.start_button.configure(state=tk.NORMAL)
            self.cancel_button.configure(state=tk.DISABLED)
            if self.progress_mode == "indeterminate":
                self.progress.stop()
            self.progress.configure(mode="determinate")
            self.progress_mode = "determinate"
            if not self.cancel_event.is_set():
                self.progress.set(1)
            self._set_input_controls_enabled(True)
        elif (self.worker_thread and self.worker_thread.is_alive()) or not self.event_queue.empty():
            self.root.after(100, self._poll_worker)

    def _safe_component(self, value):
        cleaned = "".join("_" if char in '<>:"/\\|?*' or ord(char) < 32 else char for char in value)
        return cleaned.strip(" .") or "item"

    def _unique_destination(self, path, reserved_paths):
        base, extension = os.path.splitext(path)
        candidate = path
        suffix = 1
        while (
            os.path.exists(candidate)
            or os.path.normcase(os.path.abspath(candidate)) in reserved_paths
        ):
            candidate = f"{base} ({suffix}){extension}"
            suffix += 1
        reserved_paths.add(os.path.normcase(os.path.abspath(candidate)))
        return candidate

    def create_pdf_from_files(self, file_paths, output_pdf):
        """Convert images to PDF pages and merge them with PDFs in input order."""
        pdf_merger = PyPDF2.PdfMerger()
        pdf_buffers = []

        try:
            for path in file_paths:
                if os.path.splitext(path)[1].lower() == ".pdf":
                    pdf_merger.append(path)
                    continue

                with Image.open(path) as image:
                    image_frames = [frame.convert("RGB") for frame in ImageSequence.Iterator(image)]

                pdf_buffer = BytesIO()
                pdf_buffers.append(pdf_buffer)
                try:
                    image_frames[0].save(
                        pdf_buffer,
                        format="PDF",
                        save_all=True,
                        append_images=image_frames[1:],
                    )
                finally:
                    for frame in image_frames:
                        frame.close()

                pdf_buffer.seek(0)
                pdf_merger.append(pdf_buffer)

            pdf_merger.write(output_pdf)
        finally:
            pdf_merger.close()
            for pdf_buffer in pdf_buffers:
                pdf_buffer.close()

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    root = ctk.CTk()
    app = FileSearcherPro(root)
    root.mainloop()