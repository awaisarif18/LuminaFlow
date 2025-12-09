import logging
import os
from datetime import datetime
from pathlib import Path

def setup_logging():
    """
    Configures logging to file and console.
    Returns a logger instance.
    """
    # Create logs directory in user's home folder (standard practice)
    log_dir = Path.home() / ".luminaflow" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    log_file = log_dir / f"session_{timestamp}.log"
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler() # Also print to terminal
        ]
    )
    
    logger = logging.getLogger("LuminaFlow")
    logger.info(f"Logging initialized. Saving to: {log_file}")
    return logger

# Singleton instance
log = setup_logging()