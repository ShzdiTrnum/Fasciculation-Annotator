# Fasciculation-Annotator

> A desktop GUI tool (PySide6 + OpenCV) for frame-accurate annotation of fasciculation events in ALS ultrasound video. Draws, moves, and resizes ROIs interactively, marks START / END frames with keyboard shortcuts, and exports cropped MP4 clips with a cumulative CSV annotation file — ready for downstream deep-learning experiments.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Repository Structure](#repository-structure)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Keyboard Shortcuts](#keyboard-shortcuts)
- [Annotation Workflow](#annotation-workflow)
- [Annotation CSV Format](#annotation-csv-format)
- [Data Directory](#data-directory)
- [Related Repositories](#related-repositories)
- [Citation](#citation)
- [License](#license)

---

## Overview

Fasciculation (involuntary muscle twitching) is an early biomarker of ALS. This tool supports the manual annotation pipeline for the ALS ultrasound video dataset used in Bayesian BBVI-based fasciculation detection research at Tokyo Metropolitan University (Tagawa Lab).

The annotator allows a researcher to:
1. Open an ultrasound video file
2. Navigate frame-by-frame or play at variable speed
3. Draw one or more ROIs on the muscle region of interest
4. Mark the temporal start and end of a fasciculation event
5. Export each ROI as a cropped video clip for the marked frame range
6. Save all annotations to a running CSV file

---

## Features

- Supports MPEG, MP4, AVI, MOV, MKV video files
- Frame-accurate playback at 0.1× to 2.0× speed
- Interactive ROI drawing, moving, and resizing with 8 drag handles
- Numeric editor (Xmin / Ymin / Xmax / Ymax) for pixel-accurate placement
- Multiple ROIs per event, colour-coded (green = selected, red = others)
- Keyboard-driven annotation: S = START, E = END, Space = play/pause, ←/→ = step
- Exports each ROI as a cropped MP4 clip (codec: mp4v)
- Accumulates annotations in a CSV file across events within a session

---

## Repository Structure

```
fasciculation-annotator/
│
├── main.py                        # Entry point — run this
│
├── annotator/
│   ├── __init__.py
│   ├── video_widget.py            # VideoWidget: frame rendering + ROI interaction
│   └── main_window.py             # FasciculationAnnotator: main window + all logic
│
├── configs/
│   └── default_roi.json           # Optional: saved default ROI coordinates
│
├── data/
│   ├── raw/                       # Original ultrasound videos (gitignored)
│   ├── annotations/               # Saved CSV annotation files
│   ├── clips/                     # Exported ROI video clips (gitignored)
│   ├── processed/                 # Processed/resized clips for training (gitignored)
│   └── README.md
│
├── docs/
│   └── annotation_guide.md        # Step-by-step annotation instructions
│
├── assets/                        # Screenshots for README
│
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Requirements

- Python ≥ 3.10
- PySide6 ≥ 6.5
- opencv-python ≥ 4.8

See `requirements.txt` for the full list.

---

## Installation

```bash
git clone https://github.com/ShzdiTrnum/Fasciculation-Annotator.git
cd Fasciculation-Annotator
pip install -r requirements.txt
```

---

## Usage

```bash
python main.py
```

1. Click **📂 Open MPEG / Video** and select an ultrasound video file.
2. Navigate to the start of a fasciculation event.
3. Draw an ROI by clicking and dragging on the video.
4. Press **S** to mark START, then navigate to the end and press **E** to mark END.
5. Click **💾 Save ROI Video Clips**, choose an output folder.
6. A cropped MP4 clip and updated `fasciculation_annotations.csv` are saved.

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Space` | Play / Pause |
| `←` | Previous frame |
| `→` | Next frame |
| `S` | Mark START frame |
| `E` | Mark END frame |
| `R` | Reset all ROIs |
| `Delete` | Delete selected ROI |

---

## Annotation Workflow

```
Open video
    │
    ▼
Navigate to fasciculation
    │
    ▼
Draw ROI on muscle region
    │
    ▼
Press S (START frame)
    │
    ▼
Navigate to end of twitch
    │
    ▼
Press E (END frame)
    │
    ▼
Save ROI Video Clips
    │
    ├── ROI_Clips/{video}_{event}_ROI_01.mp4
    └── fasciculation_annotations.csv
```

---

## Annotation CSV Format

The saved `fasciculation_annotations.csv` contains one row per ROI per event:

| Column | Description |
|--------|-------------|
| `event` | Unique event ID (e.g. `FAS_0001`) |
| `video` | Source video filename |
| `start_frame` | Start frame index (0-based) |
| `end_frame` | End frame index (0-based, inclusive) |
| `start_time` | Timestamp `HH:MM:SS.mmm` |
| `end_time` | Timestamp `HH:MM:SS.mmm` |
| `duration` | Duration in seconds |
| `roi` | ROI number within this event |
| `xmin` | Left boundary (pixels, original video coordinates) |
| `ymin` | Top boundary |
| `xmax` | Right boundary |
| `ymax` | Bottom boundary |
| `roi_clip` | Filename of the exported MP4 clip |

---

## Data Directory

```
data/
├── raw/          ← original ultrasound videos  [gitignored — private medical data]
├── annotations/  ← saved CSV files             [committed if anonymised]
├── clips/        ← exported ROI MP4 clips      [gitignored — large files]
├── processed/    ← resized/normalised clips     [gitignored — generated]
└── README.md
```

Raw videos and exported clips are excluded from version control.
Only anonymised annotation CSV files may be committed.

---

## Related Repositories

This tool produces the annotated clips consumed by the detection pipeline:

| Repo | Role |
|------|------|
| [Optical-Flow](https://github.com/ShzdiTrnum/Optical-Flow) | Optical flow rotation estimation on annotated clips |
| [Fasciculation-Detection-ALS](https://github.com/ShzdiTrnum/Fasciculation-Detection-ALS) | BBVI rotation detection on real ALS ultrasound |
| [Fasciculation-Simulation](https://github.com/ShzdiTrnum/Fasciculation-Simulation) | Synthetic video generation for method validation |

---

## Citation

If you use this annotation tool in your research, please cite:

```bibtex
@misc{fasciculation-annotator,
  author = {Shahzadi, Turrnum and Tagawa, Norio},
  title  = {Fasciculation Video Annotator},
  year   = {2025},
  url    = {https://github.com/ShzdiTrnum/Fasciculation-Annotator}
}
```

---

## License

MIT License. See `LICENSE` for details.
