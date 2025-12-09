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
            print("Producer failed: Shared Memory not found.")
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
            if not ret:
                break
                
            target_buffer = shm_handler.get_buffer(slot_idx)
            if frame.shape != shape:
                frame = cv2.resize(frame, (shape[1], shape[0]))

            np.copyto(target_buffer, frame)
            input_queue.put((slot_idx, frame_idx))
            
            frame_idx += 1
            slot_idx = (slot_idx + 1) % buffer_count
            
            if frame_limit and frame_idx >= frame_limit:
                break

        cap.release()
    except Exception as e:
        print(f"Producer Error: {e}")
    finally:
        input_queue.put(None) 
        print("Producer finished.")

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
            
            input_frame = np.ndarray(shape, dtype=np.uint8, buffer=in_shm.buf, offset=offset)
            output_frame = np.ndarray(shape, dtype=np.uint8, buffer=out_shm.buf, offset=offset)
            
            # PROCESS
            processed = input_frame
            if active_effects:
                for effect in active_effects:
                    if effect in PROCESSOR_MAP:
                        processed = PROCESSOR_MAP[effect](processed)
            
            np.copyto(output_frame, processed)
            output_queue.put((slot_idx, frame_idx))
            
    except Exception as e:
        print(f"Worker Error: {e}")
    finally:
        print("Worker finished.")

def consumer_task(output_path, output_shm_name, shape, buffer_count,
                  output_queue, stop_event, fps, total_workers, shared_frame_count):
    """
    UPDATED: Now accepts 'shared_frame_count' to report progress atomically.
    """
    writer = None
    try:
        out_shm = multiprocessing.shared_memory.SharedMemory(name=output_shm_name)
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(output_path, fourcc, fps, (shape[1], shape[0]))
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
                    print("All workers finished. Finalizing Consumer...")
                    break
                continue
                
            slot_idx, frame_idx = item
            
            offset = slot_idx * nbytes
            frame_data = np.ndarray(shape, dtype=np.uint8, buffer=out_shm.buf, offset=offset).copy()
            pending_frames[frame_idx] = frame_data
            
            while next_frame_needed in pending_frames:
                writer.write(pending_frames.pop(next_frame_needed))
                
                # --- ATOMIC UPDATE FOR FPS TRACKING ---
                with shared_frame_count.get_lock():
                    shared_frame_count.value += 1
                    
                next_frame_needed += 1
                
    except Exception as e:
        print(f"Consumer Error: {e}")
    finally:
        if writer:
            writer.release()
        print(f"Consumer finished. Total frames written: {next_frame_needed}")