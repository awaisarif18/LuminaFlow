import customtkinter as ctk
from tkinter import filedialog
import threading
import time
import os
import psutil
from ui.styles import *
from core.engine import VideoEngine
from ui.components import InfoCard, EffectCard
from ui.graph import RealTimeGraph # <--- NEW IMPORT

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

class VideoProcessingApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- HARDWARE ---
        self.cpu_count = os.cpu_count() or 4
        self.total_ram_gb = round(psutil.virtual_memory().total / (1024**3))
        self.max_workers = max(1, self.cpu_count - 1) 
        self.max_buffer_slots = int((self.total_ram_gb * 0.25 * 1024) / 6)
        self.max_buffer_slots = min(self.max_buffer_slots, 300)

        # Window Setup
        self.title("LuminaFlow Pro | Parallel Video Engine")
        self.geometry("1200x900") 
        self.engine = VideoEngine()
        self.selected_file = ""
        self.active_effects = []
        self.ui_is_processing = False 

        # --- ROOT GRID ---
        self.grid_columnconfigure(1, weight=1) 
        self.grid_rowconfigure(0, weight=1)    

        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=300, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False) 

        # Main Area
        self.main_area = ctk.CTkFrame(self, fg_color="transparent")
        self.main_area.grid(row=0, column=1, sticky="nsew", padx=30, pady=20)
        
        self.main_area.grid_rowconfigure(0, weight=1) 
        self.main_area.grid_columnconfigure(0, weight=1)

        self._build_sidebar()
        self._build_main_area()
        
        self.after(500, self._update_metrics)

    def _build_sidebar(self):
        ctk.CTkLabel(self.sidebar, text="LuminaFlow", font=("Roboto", 24, "bold"), text_color=ACCENT).pack(pady=(40, 5))
        ctk.CTkLabel(self.sidebar, text=f"Detected: {self.cpu_count} Cores / {self.total_ram_gb}GB RAM", 
                     font=("Roboto", 11), text_color=TEXT_GRAY).pack(pady=(0, 40))

        self._create_section_label(self.sidebar, "INPUT SOURCE")
        self.btn_browse = ctk.CTkButton(self.sidebar, text="Import Video File", command=self._select_file, height=45, fg_color="#333333", hover_color="#404040")
        self.btn_browse.pack(padx=25, pady=10, fill="x")
        self.lbl_file = ctk.CTkLabel(self.sidebar, text="No file selected", text_color=TEXT_GRAY, font=("Roboto", 11), wraplength=240)
        self.lbl_file.pack(padx=25, pady=5)

        self._create_section_label(self.sidebar, "SYSTEM TUNING")
        self.lbl_workers = ctk.CTkLabel(self.sidebar, text=f"Threads: 2", anchor="w", font=("Roboto", 12))
        self.lbl_workers.pack(padx=25, pady=(10, 0), fill="x")
        self.slider_workers = ctk.CTkSlider(self.sidebar, from_=1, to=self.max_workers, number_of_steps=self.max_workers-1, command=self._update_worker_label)
        self.slider_workers.set(max(1, self.max_workers // 2))
        self.slider_workers.pack(padx=25, pady=5, fill="x")
        
        self.lbl_buffer = ctk.CTkLabel(self.sidebar, text=f"Buffer: 30", anchor="w", font=("Roboto", 12))
        self.lbl_buffer.pack(padx=25, pady=(20, 0), fill="x")
        self.slider_buffer = ctk.CTkSlider(self.sidebar, from_=10, to=self.max_buffer_slots, number_of_steps=20, command=self._update_buffer_label)
        self.slider_buffer.set(30)
        self.slider_buffer.pack(padx=25, pady=5, fill="x")
        
        self._update_worker_label(self.slider_workers.get())

    def _build_main_area(self):
        # --- TOP SECTION ---
        self.content_frame = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.content_frame.grid(row=0, column=0, sticky="nsew")
        self.content_frame.grid_columnconfigure(0, weight=1)

        # 1. Effects
        ctk.CTkLabel(self.content_frame, text="Active Filters", font=("Roboto", 16, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 15))
        self.effects_grid = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.effects_grid.grid(row=1, column=0, sticky="ew")
        for i in range(5): self.effects_grid.grid_columnconfigure(i, weight=1)

        effects_data = {
            "Sharpen": "⚡", "Denoise": "🌫️", "Edge Detect": "🎨", "HDR": "🔆", "Contrast": "🌓",
            "Sepia": "📜", "Emboss": "🗿", "Invert": "🔄", "Sketch": "✏️", "Vignette": "🌑"
        }
        
        self.effect_cards = {}
        i = 0
        for name, icon in effects_data.items():
            card = EffectCard(self.effects_grid, text=name, icon=icon, command=self._update_effects)
            card.grid(row=i//5, column=i%5, padx=6, pady=6, sticky="ew")
            self.effect_cards[name] = card
            i += 1

        # 2. Metrics & Graph
        ctk.CTkLabel(self.content_frame, text="Performance Benchmarking", font=("Roboto", 16, "bold")).grid(row=2, column=0, sticky="w", pady=(40, 15))
        
        # Container for Cards + Graph
        self.stats_container = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.stats_container.grid(row=3, column=0, sticky="ew")
        self.stats_container.grid_columnconfigure(0, weight=1)
        self.stats_container.grid_columnconfigure(1, weight=2) # Graph gets more space
        
        # Left: Cards
        self.cards_frame = ctk.CTkFrame(self.stats_container, fg_color="transparent")
        self.cards_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        self.card_time = InfoCard(self.cards_frame, title="Processing Time", value="0.0s", color="#1F6AA5")
        self.card_time.pack(fill="x", pady=(0, 10))
        
        self.card_fps = InfoCard(self.cards_frame, title="Throughput (FPS)", value="0", color="#E2B93B")
        self.card_fps.pack(fill="x")

        # Right: Graph
        self.graph_frame = RealTimeGraph(self.stats_container, title="Live Parallel Speedup")
        self.graph_frame.grid(row=0, column=1, sticky="nsew")


        # --- BOTTOM SECTION ---
        self.footer_frame = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.footer_frame.grid(row=1, column=0, sticky="ew", pady=(20, 0))
        self.footer_frame.grid_columnconfigure(0, weight=1)

        self.progress_bar = ctk.CTkProgressBar(self.footer_frame, height=12)
        self.progress_bar.set(0)
        self.progress_bar.grid(row=0, column=0, sticky="ew", pady=(0, 15))

        self.console = ctk.CTkTextbox(self.footer_frame, height=140, fg_color="#1A1A1A", font=("Consolas", 11), border_width=0, corner_radius=10)
        self.console.grid(row=1, column=0, sticky="ew", pady=(0, 15))
        self.console.insert("0.0", f"[System] Ready. {self.cpu_count} logical cores available.\n")

        self.btn_start = ctk.CTkButton(self.footer_frame, text="INITIALIZE ENGINE", height=60, 
                                       font=("Roboto", 16, "bold"), command=self._toggle_processing, 
                                       fg_color=ACCENT, hover_color="#144870")
        self.btn_start.grid(row=2, column=0, sticky="ew")

    def _create_section_label(self, parent, text):
        ctk.CTkLabel(parent, text=text, font=("Roboto", 11, "bold"), text_color="#666666").pack(padx=25, pady=(30, 10), anchor="w")

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
            self.graph_frame.reset() # Reset graph on new file

    def _update_effects(self):
        self.active_effects = [name for name, card in self.effect_cards.items() if card.get() == 1]
        self.log(f"Effects Chain: {self.active_effects}")

    def _toggle_processing(self):
        if not self.ui_is_processing:
            if not self.selected_file:
                self.log("Error: No video selected.", "error")
                return

            output_file = os.path.splitext(self.selected_file)[0] + "_processed.mp4"
            workers = int(self.slider_workers.get())
            buffer = int(self.slider_buffer.get())
            
            self.log("Initializing Parallel Engine...")
            self.log(f"Pipeline: {workers} Threads | {buffer} Buffer Blocks | Zero-Copy ON")
            
            threading.Thread(target=self._run_engine, args=(output_file, workers, buffer)).start()
            
            self.ui_is_processing = True
            self.btn_start.configure(text="STOP ENGINE", fg_color="#C0392B", hover_color="#8B0000")
            self.progress_bar.configure(mode="indeterminate")
            self.progress_bar.start()
            self.graph_frame.reset()
        else:
            self.log("Stopping Engine...")
            self.engine.stop()
            self._reset_ui_state()

    def _run_engine(self, output, workers, buffer):
        try:
            self.engine.start(self.selected_file, output, workers, buffer, self.active_effects)
            self.log("Pipeline Active.")
        except Exception as e:
            self.log(f"Engine Error: {e}", "error")
            self.after(0, self._reset_ui_state)

    def _update_metrics(self):
        if self.ui_is_processing:
            is_alive = self.engine.check_health()
            if is_alive:
                # UPDATED: Unpack 3 values now
                elapsed, fps, frames = self.engine.get_progress()
                self.card_time.update_value(f"{elapsed:.1f}s")
                self.card_fps.update_value(f"{int(fps)}")
                
                # Update Graph
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
        timestamp = time.strftime("%H:%M:%S")
        self.console.insert("end", f"[{timestamp}] {message}\n")
        self.console.see("end")

if __name__ == "__main__":
    app = VideoProcessingApp()
    app.mainloop()