# LuminaFlow | High-Performance Parallel Video Engine

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![Architecture](https://img.shields.io/badge/Architecture-Zero--Copy%20Shared%20Memory-green)
![GUI](https://img.shields.io/badge/GUI-CustomTkinter-purple)

**LuminaFlow** is a research-grade video processing framework designed to bypass the Global Interpreter Lock (GIL) in Python. By utilizing **multiprocessing** with a **Zero-Copy Shared Memory Ring Buffer**, it achieves real-time parallelism for CPU-intensive computer vision tasks.

---

## 🚀 Key Features

* [cite_start]**Zero-Copy Architecture:** Uses `multiprocessing.shared_memory` to pass raw video frames between processes without serialization (pickling) overhead[cite: 15, 16].
* [cite_start]**Producer-Consumer Pipeline:** A lock-free ring buffer design that decouples frame reading (I/O) from processing (CPU)[cite: 33].
* **Hardware-Aware Tuning:** Automatically detects CPU cores and available RAM to prevent system freezing.
* [cite_start]**Live Benchmarking:** Real-time plotting of **Parallel Speedup** and **Throughput (FPS)** using an embedded Matplotlib graph[cite: 85].
* **Modern UI:** A dark-mode, responsive interface built with CustomTkinter.
* **Extensible Effects:** Modular filter system supporting Sharpen, Edge Detection, Sepia, and more.

---

## 🛠️ Architecture

[cite_start]The system solves the "Sequential Bottleneck" [cite: 22] by implementing a 3-stage pipeline:

1.  [cite_start]**Producer (Stage 1):** Reads frames from disk and writes raw bytes directly into a pre-allocated RAM block (Ring Buffer)[cite: 40].
2.  [cite_start]**Workers (Stage 2):** $N$ independent processes attach to the Shared Memory, apply OpenCV filters in parallel, and write results to an output buffer[cite: 45].
3.  [cite_start]**Consumer (Stage 3):** Reorders frames to ensure correct sequence and writes the final video stream to disk[cite: 55].

---

## 📦 Installation

1.  **Clone the Repository**
    ```bash
    git clone [https://github.com/yourusername/LuminaFlow.git](https://github.com/yourusername/LuminaFlow.git)
    cd LuminaFlow
    ```

2.  **Set up Virtual Environment**
    ```bash
    # Windows
    python -m venv venv
    .\venv\Scripts\activate

    # Mac/Linux
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

---

## 🖥️ Usage

1.  **Run the Application**
    ```bash
    python main.py
    ```

2.  **Workflow**
    * Click **"Import Video File"** to select a source video.
    * Use the **"Performance Tuning"** sliders to allocate Worker Threads (Physical Cores) and Buffer Size (RAM).
    * Select filters from the **"Active Filters"** grid (e.g., Edge Detect, HDR).
    * Click **"INITIALIZE ENGINE"** to start processing.

3.  **Analyze Performance**
    * Watch the **Live Parallel Speedup** graph to see how adding threads improves throughput.
    * Monitor the **FPS** counter to verify real-time performance.

---

## 📂 Project Structure

```text
LuminaFlow/
│
├── core/
│   ├── engine.py          # Main Orchestrator (Process Management)
│   ├── memory.py          # Shared Memory Manager (Ring Buffer Logic)
│   ├── workers.py         # Producer, Worker, and Consumer Tasks
│   └── processors.py      # OpenCV Algorithms (Filters)
│
├── ui/
│   ├── app.py             # Main GUI Window & Layout
│   ├── components.py      # Custom Widgets (Cards, Buttons)
│   ├── graph.py           # Live Matplotlib Benchmarking Graph
│   └── styles.py          # Design Tokens (Colors, Fonts)
│
├── main.py                # Entry Point (Windows Freeze Support)
├── requirements.txt       # Dependencies
└── README.md              # Documentation