import tkinter as tk
import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import numpy as np

class RealTimeGraph(ctk.CTkFrame):
    def __init__(self, parent, title="Live Performance (FPS)", **kwargs):
        super().__init__(parent, fg_color="#2B2B2B", corner_radius=12, **kwargs)
        
        # Title
        self.lbl_title = ctk.CTkLabel(self, text=title, font=("Roboto", 12, "bold"), text_color="#A0A0A0")
        self.lbl_title.pack(anchor="w", padx=15, pady=(10, 0))
        
        # Matplotlib Figure
        # figsize=(5, 2) defines the aspect ratio (Wide and Short)
        self.fig = Figure(figsize=(5, 2), dpi=100)
        self.fig.patch.set_facecolor('#2B2B2B')
        
        # --- CRITICAL FIX: Internal Padding ---
        # This prevents the graph from touching the edges and getting "cropped"
        self.fig.subplots_adjust(left=0.1, right=0.95, bottom=0.2, top=0.85)
        
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor('#2B2B2B')
        
        # Style
        self.ax.tick_params(colors='#A0A0A0', labelsize=8)
        self.ax.spines['bottom'].set_color('#404040')
        self.ax.spines['top'].set_color('#2B2B2B') 
        self.ax.spines['left'].set_color('#404040')
        self.ax.spines['right'].set_color('#2B2B2B') 
        
        self.line, = self.ax.plot([], [], color='#2CC985', linewidth=2)
        self.ax.grid(True, color='#404040', linestyle='--', linewidth=0.5)
        
        self.x_data = []
        self.y_data = []
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)
        
    def update_graph(self, x_val, y_val):
        self.x_data.append(x_val)
        self.y_data.append(y_val)
        
        # Update Data
        self.line.set_data(range(len(self.y_data)), self.y_data)
        
        # Rescale Axes (Full History View)
        # X-Axis: 0 to current count
        self.ax.set_xlim(0, max(10, len(self.y_data)))
        
        # Y-Axis: 0 to max FPS + padding
        current_max = max(self.y_data) if self.y_data else 0
        self.ax.set_ylim(0, max(10, current_max * 1.2))
        
        self.canvas.draw()
        
    def reset(self):
        self.x_data = []
        self.y_data = []
        self.line.set_data([], [])
        self.canvas.draw()