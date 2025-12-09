import multiprocessing
from ui.app import VideoProcessingApp

if __name__ == "__main__":
    # Essential for Windows execution
    multiprocessing.freeze_support()
    
    app = VideoProcessingApp()
    app.mainloop()