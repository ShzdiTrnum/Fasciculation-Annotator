# Annotation Guide

## Stage 1 - annotator.py

1. Run: python annotator.py
2. Click Open MPEG / Video and select an ultrasound video
3. Navigate to a fasciculation event using the slider or arrow keys
4. Click and drag on the video to draw an ROI over the muscle
5. Fine-tune with the Xmin/Ymin/Xmax/Ymax spin boxes
6. Press S to mark START frame, navigate to end, press E for END
7. Click Save ROI Video Clips and choose output folder
8. Clips saved to ROI_Clips/, annotations to fasciculation_annotations.csv
9. Click New Event to annotate the next event

## Stage 2 - multi_scale_dataset_builder.py

1. Update EXCEL_FILES and VIDEO_FOLDER at top of script
2. Run: python multi_scale_dataset_builder.py
3. Select scale: 1, 2, or 3
4. Script processes all clips and saves cropped clips + Excel

