import cv2
import numpy as np

# --- EXISTING EFFECTS ---
def apply_sharpen(frame):
    kernel = np.array([[0, -1, 0], [-1, 5,-1], [0, -1, 0]])
    return cv2.filter2D(frame, -1, kernel)

def apply_denoise(frame):
    return cv2.GaussianBlur(frame, (5, 5), 0)

def apply_edge_detection(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 100, 200)
    return cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)

def apply_hdr(frame):
    return cv2.detailEnhance(frame, sigma_s=12, sigma_r=0.15)

def apply_contrast(frame):
    return cv2.convertScaleAbs(frame, alpha=1.5, beta=0)

# --- NEW EFFECTS ---

def apply_sepia(frame):
    """Applies a vintage warm tone using a matrix transformation."""
    # Standard Sepia Matrix
    kernel = np.array([[0.272, 0.534, 0.131],
                       [0.349, 0.686, 0.168],
                       [0.393, 0.769, 0.189]])
    return cv2.transform(frame, kernel)

def apply_emboss(frame):
    """Creates a 3D relief effect."""
    kernel = np.array([[-2, -1, 0],
                       [-1,  1, 1],
                       [ 0,  1, 2]])
    return cv2.filter2D(frame, -1, kernel)

def apply_invert(frame):
    """Inverts colors (Negative)."""
    return cv2.bitwise_not(frame)

def apply_sketch(frame):
    """Simulates a pencil sketch."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    inverted = cv2.bitwise_not(gray)
    blurred = cv2.GaussianBlur(inverted, (21, 21), 0)
    inverted_blurred = cv2.bitwise_not(blurred)
    sketch = cv2.divide(gray, inverted_blurred, scale=256.0)
    return cv2.cvtColor(sketch, cv2.COLOR_GRAY2BGR)

def apply_vignette(frame):
    """Adds a dark border to focus on the center."""
    rows, cols = frame.shape[:2]
    # Create a Gaussian kernel for masking
    kernel_x = cv2.getGaussianKernel(cols, cols/2.5)
    kernel_y = cv2.getGaussianKernel(rows, rows/2.5)
    kernel = kernel_y * kernel_x.T
    
    # Normalize and scale mask
    mask = 255 * kernel / np.linalg.norm(kernel)
    
    # Apply mask to each channel
    output = np.copy(frame)
    for i in range(3):
        output[:, :, i] = output[:, :, i] * mask
        
    return output.astype(np.uint8)

# --- DISPATCHER ---
PROCESSOR_MAP = {
    "Sharpen": apply_sharpen,
    "Denoise": apply_denoise,
    "Edge Detect": apply_edge_detection,
    "HDR": apply_hdr,
    "Contrast": apply_contrast,
    "Sepia": apply_sepia,
    "Emboss": apply_emboss,
    "Invert": apply_invert,
    "Sketch": apply_sketch,
    "Vignette": apply_vignette
}