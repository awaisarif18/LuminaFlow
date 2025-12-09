import multiprocessing
import sys
from ui.app import VideoProcessingApp

if __name__ == "__main__":
    # Crucial for Windows multiprocessing to work correctly
    multiprocessing.freeze_support()
    
    try:
        app = VideoProcessingApp()
        app.mainloop()
    except KeyboardInterrupt:
        print("\nForce close detected.")
        sys.exit(0)