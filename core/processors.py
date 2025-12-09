import cv2
import numpy as np
import logging

class VideoEffects:
    """
    Robust effect processor with error handling.
    Prevents worker crashes by catching exceptions on a per-frame basis.
    """
    
    @staticmethod
    def apply_denoise(frame):
        try:
            return cv2.GaussianBlur(frame, (5, 5), 0)
        except Exception as e:
            logging.error(f"Denoise failed: {e}")
            return frame

    @staticmethod
    def apply_sharpen(frame):
        try:
            kernel = np.array([[0, -1, 0], [-1, 5,-1], [0, -1, 0]])
            return cv2.filter2D(frame, -1, kernel)
        except Exception:
            return frame

    @staticmethod
    def apply_edge_detect(frame):
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 100, 200)
            return cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
        except Exception:
            return frame

    @staticmethod
    def apply_hdr(frame):
        try:
            return cv2.detailEnhance(frame, sigma_s=12, sigma_r=0.15)
        except Exception:
            return frame

    @staticmethod
    def apply_contrast(frame):
        try:
            return cv2.convertScaleAbs(frame, alpha=1.5, beta=0)
        except Exception:
            return frame

    @staticmethod
    def apply_sepia(frame):
        try:
            kernel = np.array([[0.272, 0.534, 0.131],
                               [0.349, 0.686, 0.168],
                               [0.393, 0.769, 0.189]])
            return cv2.transform(frame, kernel)
        except Exception:
            return frame

    @staticmethod
    def apply_emboss(frame):
        try:
            kernel = np.array([[-2, -1, 0],
                               [-1,  1, 1],
                               [ 0,  1, 2]])
            return cv2.filter2D(frame, -1, kernel)
        except Exception:
            return frame

    @staticmethod
    def apply_invert(frame):
        try:
            return cv2.bitwise_not(frame)
        except Exception:
            return frame

    @staticmethod
    def apply_sketch(frame):
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            inverted = cv2.bitwise_not(gray)
            blurred = cv2.GaussianBlur(inverted, (21, 21), 0)
            inverted_blurred = cv2.bitwise_not(blurred)
            sketch = cv2.divide(gray, inverted_blurred, scale=256.0)
            return cv2.cvtColor(sketch, cv2.COLOR_GRAY2BGR)
        except Exception:
            return frame

    @staticmethod
    def apply_vignette(frame):
        try:
            rows, cols = frame.shape[:2]
            # Optimization: Calculate kernel only once if possible, 
            # but for safety we do it per frame here.
            kernel_x = cv2.getGaussianKernel(cols, cols/2.5)
            kernel_y = cv2.getGaussianKernel(rows, rows/2.5)
            kernel = kernel_y * kernel_x.T
            mask = 255 * kernel / np.linalg.norm(kernel)
            
            output = np.copy(frame)
            for i in range(3):
                output[:, :, i] = output[:, :, i] * mask
                
            return output.astype(np.uint8)
        except Exception:
            return frame

# Dispatcher Map used by workers.py
PROCESSOR_MAP = {
    "Sharpen": VideoEffects.apply_sharpen,
    "Denoise": VideoEffects.apply_denoise,
    "Edge Detect": VideoEffects.apply_edge_detect,
    "HDR": VideoEffects.apply_hdr,
    "Contrast": VideoEffects.apply_contrast,
    "Sepia": VideoEffects.apply_sepia,
    "Emboss": VideoEffects.apply_emboss,
    "Invert": VideoEffects.apply_invert,
    "Sketch": VideoEffects.apply_sketch,
    "Vignette": VideoEffects.apply_vignette
}