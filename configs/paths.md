# Path Configuration

Before running multi_scale_dataset_builder.py, update these paths at the top of the script:

    EXCEL_FILES = {
        "Small":  r"data/annotations/Small - 112x112.xlsx",
        "Medium": r"data/annotations/Medium - 160x160.xlsx",
        "Large":  r"data/annotations/Large - 224x224.xlsx",
    }
    VIDEO_FOLDER = r"data/raw"

The Excel files are produced by manual_roi_select.py (Stage 2).
You will add your own annotation files - they are not included in this repository.
