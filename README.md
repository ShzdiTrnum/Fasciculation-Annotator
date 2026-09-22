# Fasciculation-Annotator

> A three-script desktop annotation and dataset-building pipeline for ALS fasciculation events in ultrasound video. Covers the full workflow from interactive ROI annotation → manual scale-specific ROI selection → multi-scale cropped clip export — producing a structured dataset ready for deep-learning experiments.

---

## Table of Contents

- [Project Description](#project-description)
- [Pipeline Overview](#pipeline-overview)
- [Repository Structure](#repository-structure)
- [Scripts](#scripts)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Data Directory](#data-directory)
- [Related Repositories](#related-repositories)
- [Citation](#citation)
- [License](#license)

---

## Project Description

This repository provides the manual annotation and multi-scale dataset construction pipeline for ALS fasciculation detection. It is used to prepare the labelled video clip dataset that feeds into downstream 3D model for fasciculation classification.

Three scripts implement the three stages of the pipeline:

| Stage | Script | Tool |
|-------|--------|------|
| 1. Annotate fasciculation events and ROIs | `annotator.py` | PySide6 GUI |
| 2. Build multi-scale cropped clip dataset | `multi_scale_dataset_builder.py` | OpenCV + pandas (CLI) |

---

## Pipeline Overview

```
Original ultrasound video (.mpeg / .mp4 / .avi)
            │
            ▼
  ┌─────────────────────────────────────┐
  │  Stage 1: annotator.py             │
  │  - Open video                      │
  │  - Draw ROI on muscle region       │
  │  - Mark START frame (S)            │
  │  - Mark END frame (E)              │
  │  - Save cropped ROI clip (.mp4)    │
  │  - Save fasciculation_annotations  │
  │    .csv                            │
  └──────────────┬──────────────────────┘
                 │  ROI clips + CSV
                 ▼
  ┌─────────────────────────────────────┐
  │  Stage 2:                          │
  │  multi_scale_dataset_builder.py    │
  │  - Select scale (1/2/3)            │
  │  - Read Excel annotation file      │
  │  - Locate original videos          │
  │  - Crop fixed ROI from each clip   │
  │  - Save 112×112 / 160×160 /        │
  │    224×224 output clips            │
  │  - Save Selected_ROIs_*.xlsx       │
  └─────────────────────────────────────┘
                 │
                 ▼
    data/clips/small_112/   *.mp4
    data/clips/medium_160/  *.mp4
    data/clips/large_224/   *.mp4
```

---

## Repository Structure

```
fasciculation-annotator/
│
├── annotator.py                    # Stage 1: PySide6 GUI — event annotation + ROI clip export
├── multi_scale_dataset_builder.py  # Stage 2: CLI script — build multi-scale clip dataset
│
├── configs/
│   └── paths.md                    # Where to set VIDEO_FOLDER and EXCEL_FILES paths
│
├── data/
│   ├── raw/                        # Original ultrasound videos         [gitignored]
│   ├── annotations/                # Stage 1 output: fasciculation_annotations.csv
│   ├── clips/
│   │   ├── small_112/              # Stage 3 output: 112×112 cropped clips  [gitignored]
│   │   ├── medium_160/             # Stage 3 output: 160×160 cropped clips  [gitignored]
│   │   └── large_224/              # Stage 3 output: 224×224 cropped clips  [gitignored]
│   └── processed/                  # Further processed clips for training    [gitignored]
│
├── docs/
│   └── annotation_guide.md         # Step-by-step annotation instructions
│
├── assets/                         # Screenshots for README
│
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Scripts

### `annotator.py` — Stage 1: Event Annotation GUI

A PySide6 desktop application for annotating fasciculation events directly on ultrasound video.

**What it does:**
- Opens MPEG / MP4 / AVI / MOV / MKV video files
- Plays video at variable speed (0.1× to 2.0×)
- Draws, moves, and resizes rectangular ROIs with 8-handle drag controls
- Numeric editor (Xmin / Ymin / Xmax / Ymax) for pixel-accurate placement
- Marks fasciculation event START frame (key: S) and END frame (key: E)
- Exports each ROI as a cropped MP4 clip for the marked frame range
- Saves a cumulative `fasciculation_annotations.csv` with all event metadata

**Run:**
```bash
python annotator.py
```

---
Divide the "Fasciculation_Detection_Original_Labels.xlsx" into Muti-Scale files to train the mutimodels.
---

### `multi_scale_dataset_builder.py` — Stage 2: Dataset Builder CLI

A command-line script that reads the Excel files and builds the final cropped multi-scale clip dataset.

**What it does:**
- Prompts to select scale: 1 = Small (112×112), 2 = Medium (160×160), 3 = Large (224×224)
- Reads the corresponding Excel annotation file
- Locates each original video in the video folder
- Finds the fasciculation interval (parses `HH:MM:SS.mmm-HH:MM:SS.mmm` format)
- Crops the fixed-size ROI from each frame of the interval
- Saves the cropped clip as MP4
- Saves a `Selected_ROIs_{scale}_{size}x{size}.xlsx` with final coordinates

**Before running**, update the paths at the top of the script:
```python
EXCEL_FILES = {
    "Small":  r"path/to/Small – 112x112.xlsx",
    "Medium": r"path/to/Medium – 160x160.xlsx",
    "Large":  r"path/to/Large – 224x224.xlsx",
}
VIDEO_FOLDER = r"path/to/original/videos"
```

**Run:**
```bash
python multi_scale_dataset_builder.py
```

---

## Requirements

| Package | Version | Used by |
|---------|---------|---------|
| Python | ≥ 3.10 | All |
| PySide6 | ≥ 6.5 | `annotator.py` |
| opencv-python | ≥ 4.8 | All three scripts |
| pandas | ≥ 2.0 | `multi_scale_dataset_builder.py` |
| openpyxl | ≥ 3.1 | `multi_scale_dataset_builder.py` (Excel read/write) |
| numpy | ≥ 1.24 | `multi_scale_dataset_builder.py` |

---

## Installation

```bash
git clone https://github.com/ShzdiTrnum/Fasciculation-Annotator.git
cd Fasciculation-Annotator
pip install -r requirements.txt
```

---

## Usage

### Stage 1 — Annotate events

```bash
python annotator.py
```

1. Click **📂 Open MPEG / Video** and select an ultrasound video.
2. Navigate to a fasciculation event and draw an ROI on the muscle.
3. Press **S** (START) then navigate to the end and press **E** (END).
4. Click **💾 Save ROI Video Clips** → choose output folder.
5. Clips saved to `ROI_Clips/` and annotations appended to `fasciculation_annotations.csv`.


### Stage 2 — Build dataset

```bash
python multi_scale_dataset_builder.py
```

1. Enter 1 / 2 / 3 to select scale.
2. Script processes all clips automatically and saves cropped clips + Excel.

---

## Data Directory

```
data/
├── raw/              Original .mpeg / .mp4 ultrasound videos   [gitignored — private medical data]
├── annotations/      Stage 1 CSV: fasciculation_annotations.csv
├── clips/
│   ├── small_112/    Stage 2 output: 112 × 112 clips           [gitignored — large generated files]
│   ├── medium_160/   Stage 2 output: 160 × 160 clips           [gitignored]
│   └── large_224/    Stage 2 output: 224 × 224 clips           [gitignored]
└── processed/        Further normalised clips for training      [gitignored]
```

Raw videos and generated clips are excluded from version control. Only anonymised annotation CSV / Excel files may be committed.

---

## Annotation Excel Format

The Excel files used by Stage 2 and Stage 3 must contain these columns:

| Column | Description |
|--------|-------------|
| `Main_Video` | Original video filename |
| `Clip_in_Main_Video` | Clip number within that video |
| `Fasciculation_Interval` | Time range: `HH:MM:SS.mmm-HH:MM:SS.mmm` |
| `ROI_xmin` | Left boundary from Stage 1 annotation |
| `ROI_xmax` | Right boundary |
| `ROI_ymin` | Top boundary |
| `ROI_ymax` | Bottom boundary |

---

---

## Related Repositories

| Repo | Role |
|------|------|
| [Optical-Flow](https://github.com/ShzdiTrnum/Optical-Flow) | Optical flow rotation estimation on the annotated clips |
| [Fasciculation-Detection-ALS](https://github.com/ShzdiTrnum/Fasciculation-Detection-ALS) | BBVI rotation detection on real ALS ultrasound |
| [Fasciculation-Simulation](https://github.com/ShzdiTrnum/Fasciculation-Simulation) | Synthetic video generation for method validation |

---

## Citation

If you use this annotation pipeline in your research, please cite:

```bibtex
@misc{fasciculation-annotator,
  author = {Shahzadi, Turrnum and Tagawa, Norio},
  title  = {Fasciculation Video Annotator and Multi-Scale Dataset Builder},
  year   = {2025},
  url    = {https://github.com/ShzdiTrnum/Fasciculation-Annotator}
}
```

---

## License

MIT License. See `LICENSE` for details.
