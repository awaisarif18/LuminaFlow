import multiprocessing
from multiprocessing import shared_memory
import numpy as np
import logging

class SharedMemoryBuffer:
    """
    Manages a Zero-Copy Shared Memory Ring Buffer.
    Allocates a single large block of RAM and creates NumPy views into it.
    """
    def __init__(self, name, shape, dtype=np.uint8, count=30):
        self.name = name
        self.shape = shape      # (Height, Width, Channels)
        self.dtype = dtype
        self.count = count      # Number of slots in the ring (Buffer size)
        
        # Calculate size of one frame in bytes
        self.frame_nbytes = int(np.prod(shape) * np.dtype(dtype).itemsize)
        # Total size needed = frame_size * buffer_count
        self.total_size = self.frame_nbytes * count
        
        self.shm = None
        self.buffers = []       # List of numpy arrays (views)

    def allocate(self):
        """Allocates the raw memory block."""
        try:
            # Create shared memory block
            self.shm = shared_memory.SharedMemory(create=True, size=self.total_size, name=self.name)
            
            # Create numpy views for each slot
            for i in range(self.count):
                offset = i * self.frame_nbytes
                # Create a numpy array that points directly to this shared memory offset
                # ZERO-COPY MAGIC HAPPENS HERE
                array_view = np.ndarray(
                    self.shape, 
                    dtype=self.dtype, 
                    buffer=self.shm.buf, 
                    offset=offset
                )
                self.buffers.append(array_view)
                
            logging.info(f"Shared Memory '{self.name}' allocated: {self.total_size / (1024**2):.2f} MB")
            return True
        except FileExistsError:
            logging.error(f"Shared memory '{self.name}' already exists. Please cleanup.")
            return False

    def close(self):
        """Cleanup to prevent memory leaks."""
        if self.shm:
            try:
                self.shm.close()
                self.shm.unlink() # Important: This releases the RAM back to OS
                logging.info(f"Shared Memory '{self.name}' released.")
            except Exception as e:
                logging.warning(f"Error closing memory: {e}")

    def get_buffer(self, index):
        """Retrieve the numpy array for a specific slot index."""
        if 0 <= index < self.count:
            return self.buffers[index]
        raise IndexError("Buffer index out of range")