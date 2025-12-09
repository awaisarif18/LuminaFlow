import customtkinter as ctk

class InfoCard(ctk.CTkFrame):
    def __init__(self, parent, title, value="0", color="#1F6AA5", **kwargs):
        super().__init__(parent, fg_color="#2B2B2B", corner_radius=12, border_width=0, **kwargs)
        
        self.grid_columnconfigure(1, weight=1)
        
        # Color Strip
        self.strip = ctk.CTkFrame(self, width=8, fg_color=color, corner_radius=6)
        self.strip.grid(row=0, column=0, rowspan=2, sticky="ns", padx=(10, 10), pady=10)
        
        # Title
        self.lbl_title = ctk.CTkLabel(self, text=title.upper(), font=("Roboto Medium", 11), text_color="#808080")
        self.lbl_title.grid(row=0, column=1, sticky="sw", pady=(10, 0))
        
        # Value
        self.lbl_value = ctk.CTkLabel(self, text=value, font=("Roboto", 24, "bold"), text_color="#FFFFFF")
        self.lbl_value.grid(row=1, column=1, sticky="nw", pady=(0, 10))

    def update_value(self, new_value):
        self.lbl_value.configure(text=str(new_value))

class EffectCard(ctk.CTkButton):
    def __init__(self, parent, text, icon="✨", command=None, **kwargs):
        # Layout: Icon on top, Text on bottom
        text_content = f"{icon}  {text}"
        
        super().__init__(parent, text=text_content, command=self._on_click, **kwargs)
        self.user_command = command
        self.is_active = False
        
        # Colors
        self.off_color = "#2B2B2B"
        self.on_color = "#1F6AA5" 
        self.hover_off = "#333333"
        self.hover_on = "#144870"
        
        self.configure(
            fg_color=self.off_color, 
            hover_color=self.hover_off,
            height=65, 
            corner_radius=10,
            font=("Segoe UI Emoji", 13, "bold"),
            border_width=0
        )

    def _on_click(self):
        self.is_active = not self.is_active
        new_color = self.on_color if self.is_active else self.off_color
        new_hover = self.hover_on if self.is_active else self.hover_off
        self.configure(fg_color=new_color, hover_color=new_hover)
        
        if self.user_command:
            self.user_command()

    def get(self):
        return 1 if self.is_active else 0