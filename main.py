# main.py
"""Task 1 - To-Do List Manager

A feature‑rich Tkinter application that supports adding, deleting, completing,
searching tasks, light/dark theme toggle, and keyboard shortcuts.
"""

import json
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------
DATA_FILE = Path(__file__).with_name("tasks.json")

# Color schemes for light and dark modes
THEMES = {
    "dark": {
        "bg": "#2b2b2b",
        "fg": "#f0f0f0",
        "entry_bg": "#3c3f41",
        "button_bg": "#3c3f41",
        "button_active": "#4b4b4b",
        "scroll_bg": "#555555",
        "progress": "#4caf50",
    },
    "light": {
        "bg": "#f5f5f5",
        "fg": "#212121",
        "entry_bg": "#ffffff",
        "button_bg": "#e0e0e0",
        "button_active": "#c0c0c0",
        "scroll_bg": "#d0d0d0",
        "progress": "#4caf50",
    },
}


class Task:
    """Simple data container for a to‑do item."""

    def __init__(self, description: str, completed: bool = False):
        self.description = description
        self.completed = completed

    def to_dict(self) -> dict:
        return {"description": self.description, "completed": self.completed}

    @staticmethod
    def from_dict(data: dict) -> "Task":
        return Task(data.get("description", ""), data.get("completed", False))


class ToDoApp(tk.Tk):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.title("Task 1 – To‑Do List Manager")
        self.geometry("560x680")
        self.resizable(False, False)

        # ------------------------------------------------------------------
        # State
        # ------------------------------------------------------------------
        self.tasks: list[Task] = []
        self.current_theme: str = "dark"                     # default

        # ------------------------------------------------------------------
        # Load saved configuration and tasks
        # ------------------------------------------------------------------
        self._setup_style()
        self._build_ui()
        self.load_tasks()
        self.update_stats()
        self._bind_shortcuts()

    # ------------------------------------------------------------
    # Styling
    # ------------------------------------------------------------
    def _setup_style(self):
        """Configure ttk styles based on the selected theme."""
        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self._apply_theme()
        # Hover style – created once
        if "Hover.TButton" not in self.style.layout("Hover.TButton"):
            self.style.configure("Hover.TButton", background=self.themed("button_active"))

    def themed(self, key: str) -> str:
        """Helper to fetch colour from the active theme dictionary."""
        return THEMES[self.current_theme][key]

    def _apply_theme(self):
        """Apply the colour values from the active theme to ttk widgets."""
        bg = self.themed("bg")
        fg = self.themed("fg")
        self.configure(bg=bg)
        self.style.configure("TLabel", background=bg, foreground=fg)
        self.style.configure(
            "TButton",
            background=self.themed("button_bg"),
            foreground=fg,
            padding=5,
        )
        self.style.map(
            "TButton",
            background=[("active", self.themed("button_active"))],
        )
        self.style.configure(
            "TEntry",
            fieldbackground=self.themed("entry_bg"),
            foreground=fg,
        )
        self.style.configure(
            "Vertical.TScrollbar",
            troughcolor=bg,
            background=self.themed("scroll_bg"),
            arrowcolor=fg,
        )
        self.style.configure(
            "Horizontal.TScrollbar",
            troughcolor=bg,
            background=self.themed("scroll_bg"),
            arrowcolor=fg,
        )
        self.style.configure("TProgressbar", background=self.themed("progress"))

    # ------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------
    def _build_ui(self):
        # ===== Top controls (Add + Theme toggle) =====
        top_frame = ttk.Frame(self)
        top_frame.pack(fill="x", padx=10, pady=10)

        self.new_task_var = tk.StringVar()
        self.entry = ttk.Entry(top_frame, textvariable=self.new_task_var, width=40)
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<Return>", lambda e: self.add_task())

        add_btn = ttk.Button(top_frame, text="Add Task", command=self.add_task)
        add_btn.pack(side="left", padx=5)
        self._add_hover_effect(add_btn)

        # Theme toggle
        self.theme_btn = ttk.Button(
            top_frame,
            text="Switch to Light",
            command=self.toggle_theme,
        )
        self.theme_btn.pack(side="right", padx=5)
        self._add_hover_effect(self.theme_btn)

        # ===== Search bar =====
        search_frame = ttk.Frame(self)
        search_frame.pack(fill="x", padx=10, pady=5)
        ttk.Label(search_frame, text="Search:").pack(side="left")
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(side="left", fill="x", expand=True, padx=5)
        search_entry.bind("<KeyRelease>", lambda e: self._filter_tasks())
        search_entry.bind("<Control-f>", lambda e: search_entry.focus_set())

        # ===== Task list =====
        list_frame = ttk.Frame(self)
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)
        self.task_listbox = tk.Listbox(
            list_frame,
            selectmode="multiple",
            bg=self.themed("entry_bg"),
            fg=self.themed("fg"),
            activestyle="none",
        )
        self.task_listbox.pack(side="left", fill="both", expand=True)
        self.task_listbox.bind("<Double-Button-1>", self.toggle_complete)
        self.task_listbox.bind("<Delete>", lambda e: self.delete_selected())
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.task_listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.task_listbox.config(yscrollcommand=scrollbar.set)

        # ===== Action buttons =====
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", padx=10, pady=5)
        del_btn = ttk.Button(btn_frame, text="Delete Selected", command=self.delete_selected)
        del_btn.pack(side="left", padx=5)
        self._add_hover_effect(del_btn)
        clear_btn = ttk.Button(btn_frame, text="Clear All", command=self.clear_all)
        clear_btn.pack(side="left", padx=5)
        self._add_hover_effect(clear_btn)

        # ===== Statistics dashboard =====
        stats_frame = ttk.LabelFrame(self, text="Statistics")
        stats_frame.pack(fill="x", padx=10, pady=10)
        self.total_var = tk.StringVar(value="Total: 0")
        self.completed_var = tk.StringVar(value="Completed: 0")
        self.pending_var = tk.StringVar(value="Pending: 0")
        self.percent_var = tk.StringVar(value="Progress: 0%")
        ttk.Label(stats_frame, textvariable=self.total_var).grid(row=0, column=0, sticky="w", padx=5)
        ttk.Label(stats_frame, textvariable=self.completed_var).grid(row=0, column=1, sticky="w", padx=5)
        ttk.Label(stats_frame, textvariable=self.pending_var).grid(row=1, column=0, sticky="w", padx=5)
        ttk.Label(stats_frame, textvariable=self.percent_var).grid(row=1, column=1, sticky="w", padx=5)

        # Progress bar
        self.progress = ttk.Progressbar(self, orient="horizontal", mode="determinate")
        self.progress.pack(fill="x", padx=10, pady=5)

    # ------------------------------------------------------------
    # Hover effect helper
    # ------------------------------------------------------------
    def _add_hover_effect(self, widget: ttk.Button):
        def on_enter(e):
            e.widget.configure(style="Hover.TButton")

        def on_leave(e):
            e.widget.configure(style="TButton")

        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)

    # ------------------------------------------------------------
    # Task manipulation methods
    # ------------------------------------------------------------
    def add_task(self):
        """Add a new task from the entry field.
        The listbox is refreshed via _refresh_task_list to ensure consistent formatting
        (e.g., check‑mark handling) and the entry regains focus for rapid entry.
        """
        description = self.new_task_var.get().strip()
        if not description:
            messagebox.showwarning('Input Error', 'Task description cannot be empty.')
            return
        # create and store the task
        task = Task(description)
        self.tasks.append(task)
        # persist and update UI
        self.save_tasks()
        self._refresh_task_list()
        self.update_stats()
        # clear entry and keep focus
        self.new_task_var.set('')
        self.entry.focus_set()
        messagebox.showinfo('Success', f'Task added: {description}')

    def delete_selected(self):
        selected = list(self.task_listbox.curselection())
        if not selected:
            return
        if not messagebox.askyesno("Confirm Delete", "Delete selected task(s)?"):
            return
        for idx in reversed(selected):
            self.task_listbox.delete(idx)
            del self.tasks[idx]
        self.save_tasks()
        self.update_stats()
        messagebox.showinfo("Deleted", "Selected task(s) removed.")

    def clear_all(self):
        if not self.tasks:
            return
        if not messagebox.askyesno("Confirm", "Delete all tasks?"):
            return
        self.task_listbox.delete(0, "end")
        self.tasks.clear()
        self.save_tasks()
        self.update_stats()
        messagebox.showinfo("Cleared", "All tasks have been cleared.")

    def toggle_complete(self, event):
        index = self.task_listbox.nearest(event.y)
        if index < 0 or index >= len(self.tasks):
            return
        task = self.tasks[index]
        task.completed = not task.completed
        display = task.description + (" ✅" if task.completed else "")
        self.task_listbox.delete(index)
        self.task_listbox.insert(index, display)
        self.save_tasks()
        self.update_stats()

    # ------------------------------------------------------------
    # Search / filter
    # ------------------------------------------------------------
    def _filter_tasks(self):
        query = self.search_var.get().lower()
        self.task_listbox.delete(0, "end")
        for task in self.tasks:
            if query in task.description.lower():
                display = task.description + (" ✅" if task.completed else "")
                self.task_listbox.insert("end", display)

    def _add_sample_tasks(self):
        self.tasks = [Task("Learn Tkinter"), Task("Build an App", True)]
        self.save_tasks()

    def _refresh_task_list(self):
        self.task_listbox.delete(0, "end")
        for task in self.tasks:
            display = task.description + (" ✅" if task.completed else "")
            self.task_listbox.insert("end", display)

    # ------------------------------------------------------------
    # Statistics & persistence
    # ------------------------------------------------------------
    def update_stats(self):
        total = len(self.tasks)
        completed = sum(t.completed for t in self.tasks)
        pending = total - completed
        percent = int((completed / total) * 100) if total else 0
        self.total_var.set(f"Total: {total}")
        self.completed_var.set(f"Completed: {completed}")
        self.pending_var.set(f"Pending: {pending}")
        self.percent_var.set(f"Progress: {percent}%")
        self.progress["value"] = percent

    def load_tasks(self):
        """Load tasks from JSON; if the file is empty, create sample tasks for demo purposes."""
        if not DATA_FILE.exists():
            DATA_FILE.touch()
            self.tasks = []
            self._add_sample_tasks()
            self._refresh_task_list()
            return

        try:
            data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
            self.tasks = [Task.from_dict(item) for item in data]
            if not self.tasks:
                self._add_sample_tasks()
            self._refresh_task_list()
        except (json.JSONDecodeError, OSError) as e:
            messagebox.showerror("Load Error", f"Failed to load tasks: {e}")
            self.tasks = []
            self._add_sample_tasks()
            self._refresh_task_list()

    def save_tasks(self):
        """Persist the current task list to the JSON file."""
        try:
            content = json.dumps([t.to_dict() for t in self.tasks], indent=2)
            DATA_FILE.write_text(content, encoding="utf-8")
        except OSError as e:
            messagebox.showerror("Save Error", f"Failed to save tasks: {e}")

    # ------------------------------------------------------------
    # Theme toggle
    # ------------------------------------------------------------
    def toggle_theme(self):
        self.current_theme = "light" if self.current_theme == "dark" else "dark"
        self._apply_theme()
        # Update button label
        self.theme_btn.configure(text="Switch to Dark" if self.current_theme == "light" else "Switch to Light")
        # Refresh widget colours
        self.task_listbox.configure(bg=self.themed("entry_bg"), fg=self.themed("fg"))

    # ------------------------------------------------------------
    # Keyboard shortcuts
    # ------------------------------------------------------------
    def _bind_shortcuts(self):
        self.bind_all("<Control-f>", lambda e: self.focus_set())  # Focus on search (handled by entry bind)
        self.bind_all("<Control-l>", lambda e: self.toggle_theme())
        self.bind_all("<Control-n>", lambda e: self.add_task())
        self.bind_all("<Delete>", lambda e: self.delete_selected())

    def on_close(self):
        self.destroy()

if __name__ == "__main__":
    # Start the application with sample data if needed
    app = ToDoApp()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()
