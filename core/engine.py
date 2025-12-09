import multiprocessing
import queue
import time
import os
import cv2
import numpy as np
from core.memory import SharedMemoryBuffer
from core.workers import producer_task, worker_task, consumer_task

class VideoEngine:
    def __init__(self):
        self.procs = []
        self.input_queue = None 
        self.output_queue = None
        self.stop_event = multiprocessing.Event()
        self.input_shm = None
        self.output_shm = None
        
        # Shared Counter for FPS
        self.shared_frame_count = None
        
        # FPS Calculation State
        self.last_fps_check_time = 0
        self.last_frame_count = 0
        self.current_fps = 0.0
        
        # Status
        self.is_running = False
        self.start_time = 0
        
    def start(self, video_path, output_path, worker_count, buffer_size, effects):
        self.stop()
        
        # Init Queues & Counter
        self.input_queue = multiprocessing.Queue(maxsize=1000)
        self.output_queue = multiprocessing.Queue(maxsize=1000)
        self.shared_frame_count = multiprocessing.Value('i', 0) # 'i' = signed int
        self.stop_event.clear()
        
        self.is_running = True
        self.start_time = time.time()
        self.last_fps_check_time = time.time()
        self.last_frame_count = 0

        # Video Props
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened(): raise Exception("Could not open video file.")
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        cap.release()
        
        if width == 0 or height == 0: raise Exception("Invalid video dimensions.")
        shape = (height, width, 3) 

        # Allocate Memory
        self.input_shm = SharedMemoryBuffer("shm_in", shape, count=buffer_size)
        if not self.input_shm.allocate(): 
            self.input_shm.close()
            if not self.input_shm.allocate(): raise Exception("Failed to alloc Input SHM")
        
        self.output_shm = SharedMemoryBuffer("shm_out", shape, count=buffer_size)
        if not self.output_shm.allocate(): 
            self.output_shm.close()
            if not self.output_shm.allocate(): raise Exception("Failed to alloc Output SHM")

        # Spawn Processes
        p_prod = multiprocessing.Process(target=producer_task, args=(video_path, "shm_in", shape, buffer_size, self.input_queue, self.stop_event))
        p_prod.start()
        self.procs.append(p_prod)

        for _ in range(worker_count):
            p_work = multiprocessing.Process(target=worker_task, args=("shm_in", "shm_out", shape, buffer_size, self.input_queue, self.output_queue, self.stop_event, effects))
            p_work.start()
            self.procs.append(p_work)

        p_cons = multiprocessing.Process(
            target=consumer_task, 
            args=(output_path, "shm_out", shape, buffer_size, self.output_queue, self.stop_event, fps, worker_count, self.shared_frame_count)
        )
        p_cons.start()
        self.procs.append(p_cons)
        
        return True

    def stop(self):
        self.stop_event.set()
        for p in self.procs:
            p.join(timeout=0.1)
        for p in self.procs:
            if p.is_alive(): p.terminate() 
        self.procs = []
        if self.input_shm: self.input_shm.close()
        if self.output_shm: self.output_shm.close()
        self.is_running = False

    def check_health(self):
        if not self.is_running:
            return False
        if self.procs:
            alive_count = sum(1 for p in self.procs if p.is_alive())
            if alive_count == 0:
                return False 
            return True
        return False

    def get_progress(self):
        """Returns (elapsed_time, fps, frames_processed)"""
        if not self.is_running:
            return 0, 0, 0
            
        elapsed = time.time() - self.start_time
        
        # Calculate instantaneous FPS
        now = time.time()
        delta_time = now - self.last_fps_check_time
        
        current_count = self.shared_frame_count.value
        delta_frames = current_count - self.last_frame_count
        
        # Update FPS every 0.5 seconds to prevent jitter
        if delta_time > 0.5:
            self.current_fps = delta_frames / delta_time
            self.last_fps_check_time = now
            self.last_frame_count = current_count
            
        return elapsed, self.current_fps, current_count