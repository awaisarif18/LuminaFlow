import time
import cv2
import queue
import multiprocessing
import numpy as np
from core.processors import PROCESSOR_MAP
from core.memory import SharedMemoryBuffer 

def producer_task(video_path, buffer_name, shape, buffer_count, 
                  input_queue, stop_event, frame_limit=None):
    try:
        cap = cv2.VideoCapture(video_path)
        shm_handler = SharedMemoryBuffer(buffer_name, shape, count=buffer_count)
        
        try:
            shm_handler.shm = multiprocessing.shared_memory.SharedMemory(name=buffer_name)
        except FileNotFoundError:
            return

        for i in range(buffer_count):
            offset = i * shm_handler.frame_nbytes
            shm_handler.buffers.append(
                np.ndarray(shape, dtype=np.uint8, buffer=shm_handler.shm.buf, offset=offset)
            )
            
        frame_idx = 0
        slot_idx = 0
        
        while not stop_event.is_set():
            ret, frame = cap.read()
            if not ret: break
            
            # SAFEGUARD: Ensure frame matches expected shape EXACTLY
            # This prevents the "slanting/glitch" effect
            if frame.shape != shape:
                frame = cv2.resize(frame, (shape[1], shape[0]))
            
            frame = np.ascontiguousarray(frame)

            target_buffer = shm_handler.get_buffer(slot_idx)
            np.copyto(target_buffer, frame)
            
            input_queue.put((slot_idx, frame_idx))
            
            frame_idx += 1
            slot_idx = (slot_idx + 1) % buffer_count
            
            if frame_limit and frame_idx >= frame_limit: break

        cap.release()
    except Exception as e:
        print(f"Producer Error: {e}")
    finally:
        input_queue.put(None) 

def worker_task(input_shm_name, output_shm_name, shape, buffer_count,
                input_queue, output_queue, stop_event, active_effects):
    try:
        in_shm = multiprocessing.shared_memory.SharedMemory(name=input_shm_name)
        out_shm = multiprocessing.shared_memory.SharedMemory(name=output_shm_name)
        nbytes = int(np.prod(shape) * np.dtype(np.uint8).itemsize)
        
        while not stop_event.is_set():
            try:
                task = input_queue.get(timeout=0.1)
            except queue.Empty:
                continue
                
            if task is None:
                input_queue.put(None)
                output_queue.put(None)
                break
                
            slot_idx, frame_idx = task
            offset = slot_idx * nbytes
            
            # Read-Only Input View
            input_frame = np.ndarray(shape, dtype=np.uint8, buffer=in_shm.buf, offset=offset)
            
            # Local copy for processing (Important for safety)
            processed = input_frame.copy()
            
            if active_effects:
                for effect in active_effects:
                    if effect in PROCESSOR_MAP:
                        processed = PROCESSOR_MAP[effect](processed)
            
            # Write to Output View
            output_frame = np.ndarray(shape, dtype=np.uint8, buffer=out_shm.buf, offset=offset)
            np.copyto(output_frame, processed)
            
            output_queue.put((slot_idx, frame_idx))
            
    except Exception as e:
        print(f"Worker Error: {e}")

def consumer_task(output_path, output_shm_name, shape, buffer_count,
                  output_queue, stop_event, fps, total_workers, shared_frame_count):
    writer = None
    try:
        out_shm = multiprocessing.shared_memory.SharedMemory(name=output_shm_name)
        
        # --- CODEC SELECTION ---
        # H.264 (avc1) is smaller/better. Fallback to mp4v if missing.
        codecs = ['avc1', 'mp4v', 'DIVX']
        for codec in codecs:
            try:
                fourcc = cv2.VideoWriter_fourcc(*codec)
                writer = cv2.VideoWriter(output_path, fourcc, fps, (shape[1], shape[0]))
                if writer.isOpened():
                    print(f"Using codec: {codec}")
                    break
            except:
                continue

        nbytes = int(np.prod(shape) * np.dtype(np.uint8).itemsize)
        
        next_frame_needed = 0
        pending_frames = {} 
        finished_workers_count = 0
        
        while not stop_event.is_set():
            try:
                item = output_queue.get(timeout=0.1)
            except queue.Empty:
                continue
                
            if item is None:
                finished_workers_count += 1
                if finished_workers_count >= total_workers:
                    break
                continue
                
            slot_idx, frame_idx = item
            offset = slot_idx * nbytes
            
            # Copy data immediately to release buffer
            frame_data = np.ndarray(shape, dtype=np.uint8, buffer=out_shm.buf, offset=offset).copy()
            pending_frames[frame_idx] = frame_data
            
            while next_frame_needed in pending_frames:
                writer.write(pending_frames.pop(next_frame_needed))
                with shared_frame_count.get_lock():
                    shared_frame_count.value += 1
                next_frame_needed += 1
                
    except Exception as e:
        print(f"Consumer Error: {e}")
    finally:
        if writer: writer.release()