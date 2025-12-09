import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import time
import os
import psutil
from ui.styles import *
from core.engine import VideoEngine
from ui.components import InfoCard, EffectCard
from ui.graph import RealTimeGraph 
from utils.logger import log 

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

class VideoProcessingApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- SAFETY ---
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # --- HARDWARE ---
        self.cpu_count = os.cpu_count() or 4
        self.total_ram_gb = round(psutil.virtual_memory().total / (1024**3))
        self.max_workers = max(1, self.cpu_count - 1) 
        self.max_buffer_slots = min(int((self.total_ram_gb * 0.25 * 1024) / 6), 300)

        # Window Setup - COMPACT
        self.title("LuminaFlow Pro")
        self.geometry("1100x700") 
        self.minsize(900, 600)
        
        self.engine = VideoEngine()
        self.selected_file = ""
        self.active_effects = []
        self.ui_is_processing = False 
        self.effect_cards = {} 

        # --- GRID ---
        self.grid_columnconfigure(1, weight=1) 
        self.grid_rowconfigure(0, weight=1)    

        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False) 

        # Main Area
        self.main_area = ctk.CTkFrame(self, fg_color="transparent")
        self.main_area.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.main_area.grid_rowconfigure(0, weight=1) 
        self.main_area.grid_columnconfigure(0, weight=1)

        self._build_sidebar()
        self._build_main_area()
        
        self.after(500, self._update_metrics)
        log.info("UI Initialized (Ultra Compact).")

    def _build_sidebar(self):
        # Header
        ctk.CTkLabel(self.sidebar, text="LuminaFlow", font=("Roboto", 20, "bold"), text_color=ACCENT).pack(pady=(20, 5))
        ctk.CTkLabel(self.sidebar, text=f"{self.cpu_count} Cores / {self.total_ram_gb}GB RAM", 
                     font=("Roboto", 10), text_color=TEXT_GRAY).pack(pady=(0, 20))

        # Input
        self._create_section_label(self.sidebar, "INPUT")
        self.btn_browse = ctk.CTkButton(self.sidebar, text="Import Video", command=self._select_file, height=32, fg_color="#333333", hover_color="#404040")
        self.btn_browse.pack(padx=15, pady=5, fill="x")
        self.lbl_file = ctk.CTkLabel(self.sidebar, text="No file selected", text_color=TEXT_GRAY, font=("Roboto", 10), wraplength=200)
        self.lbl_file.pack(padx=15, pady=2)

        # Presets
        self._create_section_label(self.sidebar, "PRESETS")
        presets = [("🎬 Cinematic", ["HDR", "Vignette"]), ("📜 Vintage", ["Sepia", "Vignette"]), ("🖍️ Sketch", ["Sketch", "Contrast"]), ("🔍 Repair", ["Denoise", "Sharpen"])]
        for name, filters in presets:
            btn = ctk.CTkButton(self.sidebar, text=name, command=lambda f=filters: self._apply_preset(f),
                                fg_color="transparent", border_width=1, border_color="#404040", text_color="#A0A0A0", height=28)
            btn.pack(padx=15, pady=2, fill="x")

        # Tuning
        self._create_section_label(self.sidebar, "TUNING")
        self.lbl_workers = ctk.CTkLabel(self.sidebar, text=f"Threads: 2", anchor="w", font=("Roboto", 10))
        self.lbl_workers.pack(padx=15, pady=(5, 0), fill="x")
        self.slider_workers = ctk.CTkSlider(self.sidebar, from_=1, to=self.max_workers, number_of_steps=self.max_workers-1, command=self._update_worker_label, height=14)
        self.slider_workers.set(max(1, self.max_workers // 2))
        self.slider_workers.pack(padx=15, pady=2, fill="x")
        
        self.lbl_buffer = ctk.CTkLabel(self.sidebar, text=f"Buffer: 30", anchor="w", font=("Roboto", 10))
        self.lbl_buffer.pack(padx=15, pady=(5, 0), fill="x")
        self.slider_buffer = ctk.CTkSlider(self.sidebar, from_=10, to=self.max_buffer_slots, number_of_steps=20, command=self._update_buffer_label, height=14)
        self.slider_buffer.set(30)
        self.slider_buffer.pack(padx=15, pady=2, fill="x")
        self._update_worker_label(self.slider_workers.get())

    def _build_main_area(self):
        self.content_frame = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.content_frame.grid(row=0, column=0, sticky="nsew")
        self.content_frame.grid_columnconfigure(0, weight=1)
        
        # --- LAYOUT WEIGHTS ---
        # Row 0: Title (0)
        # Row 1: Tabs (Weight 3 -> Takes most space)
        # Row 2: Metrics Title (0)
        # Row 3: Stats (Weight 1 -> Takes some space)
        self.content_frame.grid_rowconfigure(1, weight=3)
        self.content_frame.grid_rowconfigure(3, weight=1)

        # 1. Effects
        ctk.CTkLabel(self.content_frame, text="Effect Studio", font=("Roboto", 14, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 5))

        self.tab_view = ctk.CTkTabview(self.content_frame, height=200) # Force shorter height
        self.tab_view.grid(row=1, column=0, sticky="nsew")
        
        tab_enhance = self.tab_view.add("Enhance")
        tab_artistic = self.tab_view.add("Artistic")
        tab_lens = self.tab_view.add("Lens")
        
        effects_map = {
            "Enhance": {"Sharpen": "⚡", "Denoise": "🌫️", "HDR": "🔆", "Contrast": "🌓"},
            "Artistic": {"Sepia": "📜", "Emboss": "🗿", "Invert": "🔄", "Sketch": "✏️"},
            "Lens": {"Vignette": "🌑", "Edge Detect": "🎨"}
        }

        for tab_name, items in effects_map.items():
            tab_root = self.tab_view.tab(tab_name)
            # Scrollable Inner Frame
            scroll_inner = ctk.CTkScrollableFrame(tab_root, fg_color="transparent")
            scroll_inner.pack(fill="both", expand=True)
            scroll_inner.grid_columnconfigure((0, 1, 2, 3), weight=1)
            
            col, row = 0, 0
            for name, icon in items.items():
                card = EffectCard(scroll_inner, text=name, icon=icon, command=self._update_effects)
                card.grid(row=row, column=col, padx=5, pady=5, sticky="ew")
                self.effect_cards[name] = card
                col += 1
                if col > 3: col, row = 0, row + 1

        # 2. Benchmarking
        ctk.CTkLabel(self.content_frame, text="Benchmarks", font=("Roboto", 14, "bold")).grid(row=2, column=0, sticky="w", pady=(10, 5))
        
        self.stats_container = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.stats_container.grid(row=3, column=0, sticky="ew")
        self.stats_container.grid_columnconfigure(0, weight=1)
        self.stats_container.grid_columnconfigure(1, weight=2) 
        
        # Cards
        self.cards_frame = ctk.CTkFrame(self.stats_container, fg_color="transparent")
        self.cards_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        
        self.card_time = InfoCard(self.cards_frame, title="Time", value="0.0s", color="#1F6AA5")
        self.card_time.pack(fill="x", pady=(0, 5)) # Tight packing
        
        self.card_fps = InfoCard(self.cards_frame, title="FPS", value="0", color="#E2B93B")
        self.card_fps.pack(fill="x")

        # Graph
        self.graph_frame = RealTimeGraph(self.stats_container, title="Parallel Speedup")
        self.graph_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

        # --- FOOTER ---
        self.footer_frame = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.footer_frame.grid(row=1, column=0, sticky="ew", pady=(5, 0))
        self.footer_frame.grid_columnconfigure(0, weight=1)

        self.progress_bar = ctk.CTkProgressBar(self.footer_frame, height=8)
        self.progress_bar.set(0)
        self.progress_bar.grid(row=0, column=0, sticky="ew", pady=(0, 5))

        # Tiny Console
        self.console = ctk.CTkTextbox(self.footer_frame, height=60, fg_color="#1A1A1A", font=("Consolas", 9), border_width=0, corner_radius=6)
        self.console.grid(row=1, column=0, sticky="ew", pady=(0, 5))
        self.console.insert("0.0", f"[System] Ready. {self.cpu_count} logical cores.\n")

        self.btn_start = ctk.CTkButton(self.footer_frame, text="INITIALIZE ENGINE", height=40, 
                                       font=("Roboto", 13, "bold"), command=self._toggle_processing, 
                                       fg_color=ACCENT, hover_color="#144870")
        self.btn_start.grid(row=2, column=0, sticky="ew")

    # --- LOGIC ---
    def _create_section_label(self, parent, text):
        ctk.CTkLabel(parent, text=text, font=("Roboto", 9, "bold"), text_color="#666666").pack(padx=15, pady=(15, 5), anchor="w")

    def _on_close(self):
        if self.engine.is_running:
            if messagebox.askokcancel("Quit", "Processing is active. Stop engine?"):
                self.engine.stop()
                self.destroy()
        else:
            self.destroy()

    def _apply_preset(self, filters):
        self.log(f"Applying Preset: {filters}")
        for card in self.effect_cards.values():
            if card.is_active: card._on_click()
        for name in filters:
            if name in self.effect_cards:
                card = self.effect_cards[name]
                if not card.is_active: card._on_click()
        self._update_effects()

    def _update_worker_label(self, value):
        self.lbl_workers.configure(text=f"Threads: {int(value)}")

    def _update_buffer_label(self, value):
        self.lbl_buffer.configure(text=f"Buffer: {int(value)} frames")

    def _select_file(self):
        filename = filedialog.askopenfilename(filetypes=[("Video Files", "*.mp4 *.avi *.mov")])
        if filename:
            self.selected_file = filename
            self.lbl_file.configure(text=os.path.basename(filename))
            self.log(f"Selected: {filename}")
            self.btn_start.configure(text="START PROCESSING")
            self.graph_frame.reset() 

    def _update_effects(self):
        self.active_effects = [name for name, card in self.effect_cards.items() if card.get() == 1]
        self.log(f"Effects: {self.active_effects}")

    def _toggle_processing(self):
        if not self.ui_is_processing:
            if not self.selected_file:
                self.log("Error: No video selected.", "error")
                return
            output_file = os.path.splitext(self.selected_file)[0] + "_processed.mp4"
            workers = int(self.slider_workers.get())
            buffer = int(self.slider_buffer.get())
            
            self.log("Initializing...")
            threading.Thread(target=self._run_engine, args=(output_file, workers, buffer)).start()
            
            self.ui_is_processing = True
            self.btn_start.configure(text="STOP ENGINE", fg_color="#C0392B", hover_color="#8B0000")
            self.progress_bar.configure(mode="indeterminate")
            self.progress_bar.start()
            self.graph_frame.reset()
        else:
            self.log("Stopping...")
            self.engine.stop()
            self._reset_ui_state()

    def _run_engine(self, output, workers, buffer):
        try:
            self.engine.start(self.selected_file, output, workers, buffer, self.active_effects)
            self.log("Pipeline Active.")
        except Exception as e:
            self.log(f"Error: {e}", "error")
            self.after(0, self._reset_ui_state)

    def _update_metrics(self):
        if self.ui_is_processing:
            is_alive = self.engine.check_health()
            if is_alive:
                elapsed, fps, frames = self.engine.get_progress()
                self.card_time.update_value(f"{elapsed:.1f}s")
                self.card_fps.update_value(f"{int(fps)}")
                self.graph_frame.update_graph(elapsed, fps)
            else:
                self.log("Task Completed.")
                self.engine.stop()
                self._reset_ui_state()
        self.after(500, self._update_metrics)

    def _reset_ui_state(self):
        self.ui_is_processing = False
        self.btn_start.configure(text="START PROCESSING", fg_color=ACCENT, hover_color="#144870")
        self.progress_bar.stop()
        self.progress_bar.set(0)

    def log(self, message, level="info"):
        if level == "error": log.error(message)
        else: log.info(message)
        timestamp = time.strftime("%H:%M:%S")
        self.console.insert("end", f"[{timestamp}] {message}\n")
        self.console.see("end")

if __name__ == "__main__":
    app = VideoProcessingApp()
    app.mainloop()