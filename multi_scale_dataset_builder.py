import cv2
import pandas as pd
import numpy as np
import os
import re


# ============================================================
# USER SETTINGS
# ============================================================

# ------------------------------------------------------------
# THREE SEPARATE EXCEL FILES
# ------------------------------------------------------------

EXCEL_FILES = {
    "Small": r"D:\Fasci_Scales_Dataset\Small – 112x112.xlsx",
    "Medium": r"D:\Fasci_Scales_Dataset\Medium – 160x160.xlsx",
    "Large": r"D:\Fasci_Scales_Dataset\Large – 224x224.xlsx"
}


# ------------------------------------------------------------
# ORIGINAL VIDEO DATASET
# ------------------------------------------------------------

VIDEO_FOLDER = r"D:\Fasci\Fasciculaaation_Dataset"


# ------------------------------------------------------------
# FIXED ROI SIZES
# ------------------------------------------------------------

ROI_SIZES = {
    "Small": 112,
    "Medium": 160,
    "Large": 224
}


# ============================================================
# SELECT SCALE
# ============================================================

print("=" * 75)
print("SELECT SPATIAL SCALE")
print("=" * 75)

print()
print("1 = Small   (112 × 112)")
print("2 = Medium  (160 × 160)")
print("3 = Large   (224 × 224)")

choice = input("\nEnter 1, 2, or 3: ").strip()


if choice == "1":
    scale_name = "Small"

elif choice == "2":
    scale_name = "Medium"

elif choice == "3":
    scale_name = "Large"

else:
    raise ValueError(
        "Invalid selection. Please enter 1, 2, or 3."
    )


ROI_SIZE = ROI_SIZES[scale_name]

EXCEL_PATH = EXCEL_FILES[scale_name]


print()
print(f"Selected scale : {scale_name}")
print(f"Fixed ROI size : {ROI_SIZE} × {ROI_SIZE}")
print(f"Excel file     : {EXCEL_PATH}")
print(f"Video dataset  : {VIDEO_FOLDER}")
print()


# ============================================================
# CHECK EXCEL
# ============================================================

if not os.path.exists(EXCEL_PATH):

    raise FileNotFoundError(
        f"\nExcel file not found:\n{EXCEL_PATH}"
    )


# ============================================================
# CHECK VIDEO FOLDER
# ============================================================

if not os.path.isdir(VIDEO_FOLDER):

    raise FileNotFoundError(
        f"\nVideo dataset folder not found:\n{VIDEO_FOLDER}"
    )


# ============================================================
# LOAD EXCEL
# ============================================================

df = pd.read_excel(EXCEL_PATH)


print("Excel columns:")
print(df.columns.tolist())

print()
print(f"Number of clips: {len(df)}")


# ============================================================
# REQUIRED COLUMNS
# ============================================================

required_columns = [
    "Main_Video",
    "Clip_in_Main_Video",
    "Fasciculation_Interval",
    "ROI_xmin",
    "ROI_xmax",
    "ROI_ymin",
    "ROI_ymax"
]


missing_columns = [
    column
    for column in required_columns
    if column not in df.columns
]


if missing_columns:

    raise ValueError(
        "\nMissing columns in Excel:\n"
        + "\n".join(missing_columns)
    )


# ============================================================
# GLOBAL MOUSE VARIABLES
# ============================================================

current_x = 0
current_y = 0

dragging = False

drag_offset_x = 0
drag_offset_y = 0


# ============================================================
# TIME TO SECONDS
# ============================================================

def time_to_seconds(time_string):

    """
    Convert:

        HH:MM:SS.xxx

    to seconds.
    """

    time_string = str(
        time_string
    ).strip()


    match = re.match(
        r"^(\d+):(\d+):(\d+(?:\.\d+)?)$",
        time_string
    )


    if not match:

        raise ValueError(
            f"Cannot parse time: {time_string}"
        )


    hours = int(match.group(1))

    minutes = int(match.group(2))

    seconds = float(match.group(3))


    return (
        hours * 3600
        + minutes * 60
        + seconds
    )


# ============================================================
# PARSE FASCICULATION INTERVAL
# ============================================================

def parse_interval(interval):

    """
    Example:

        00:00:34.280-00:00:35.040
    """

    interval = str(
        interval
    ).strip()


    parts = interval.split("-")


    if len(parts) != 2:

        raise ValueError(
            f"Invalid interval: {interval}"
        )


    start_time = parts[0].strip()

    end_time = parts[1].strip()


    start_seconds = time_to_seconds(
        start_time
    )

    end_seconds = time_to_seconds(
        end_time
    )


    if end_seconds <= start_seconds:

        raise ValueError(
            f"Invalid interval: {interval}"
        )


    return start_seconds, end_seconds


# ============================================================
# FIND VIDEO
# ============================================================

def find_video(video_name):

    """
    Search for the original video.

    Supports:
        MP4
        AVI
        MPEG
        MPG
        MOV
        MKV
    """

    video_name = str(
        video_name
    ).strip()


    # --------------------------------------------------------
    # Direct path
    # --------------------------------------------------------

    direct_path = os.path.join(
        VIDEO_FOLDER,
        video_name
    )


    if os.path.isfile(direct_path):

        return direct_path


    # --------------------------------------------------------
    # Try extensions
    # --------------------------------------------------------

    extensions = [
        ".mp4",
        ".avi",
        ".mpeg",
        ".mpg",
        ".mov",
        ".mkv"
    ]


    for extension in extensions:

        candidate = os.path.join(
            VIDEO_FOLDER,
            video_name + extension
        )


        if os.path.isfile(candidate):

            return candidate


    # --------------------------------------------------------
    # Remove extension and try again
    # --------------------------------------------------------

    base_name = os.path.splitext(
        video_name
    )[0]


    for extension in extensions:

        candidate = os.path.join(
            VIDEO_FOLDER,
            base_name + extension
        )


        if os.path.isfile(candidate):

            return candidate


    return None


# ============================================================
# KEEP ROI INSIDE COMPLETE VIDEO
# ============================================================

def keep_roi_inside(
        x,
        y,
        frame_width,
        frame_height,
        roi_size):

    x = int(x)

    y = int(y)


    x = max(
        0,
        min(
            x,
            frame_width - roi_size
        )
    )


    y = max(
        0,
        min(
            y,
            frame_height - roi_size
        )
    )


    return x, y


# ============================================================
# MOUSE CALLBACK
# ============================================================

def mouse_callback(
        event,
        x,
        y,
        flags,
        param):

    global current_x
    global current_y

    global dragging

    global drag_offset_x
    global drag_offset_y


    frame_width = param[
        "frame_width"
    ]

    frame_height = param[
        "frame_height"
    ]

    # --------------------------------------------------------
    # IMPORTANT:
    #
    # The video is displayed BELOW the information area.
    #
    # Therefore mouse Y coordinate must subtract
    # VIDEO_TOP_OFFSET.
    # --------------------------------------------------------

    video_y = (
        y - param["video_top_offset"]
    )

    video_x = x


    # --------------------------------------------------------
    # Ignore mouse clicks in information area
    # --------------------------------------------------------

    if video_y < 0:

        if event == cv2.EVENT_LBUTTONUP:

            dragging = False

        return


    # --------------------------------------------------------
    # LEFT BUTTON DOWN
    # --------------------------------------------------------

    if event == cv2.EVENT_LBUTTONDOWN:

        inside_roi = (

            current_x <= video_x <=
            current_x + ROI_SIZE

            and

            current_y <= video_y <=
            current_y + ROI_SIZE
        )


        if inside_roi:

            dragging = True

            drag_offset_x = (
                video_x - current_x
            )

            drag_offset_y = (
                video_y - current_y
            )


    # --------------------------------------------------------
    # MOUSE MOVE
    # --------------------------------------------------------

    elif event == cv2.EVENT_MOUSEMOVE:

        if dragging:

            new_x = (
                video_x - drag_offset_x
            )

            new_y = (
                video_y - drag_offset_y
            )


            current_x, current_y = (
                keep_roi_inside(
                    new_x,
                    new_y,
                    frame_width,
                    frame_height,
                    ROI_SIZE
                )
            )


    # --------------------------------------------------------
    # LEFT BUTTON UP
    # --------------------------------------------------------

    elif event == cv2.EVENT_LBUTTONUP:

        dragging = False


# ============================================================
# RESULTS
# ============================================================

results = []


# ============================================================
# INFORMATION AREA HEIGHT
#
# This is ABOVE the video.
# It does NOT cover any video pixels.
# ============================================================

INFO_HEIGHT = 165


# ============================================================
# WINDOW
# ============================================================

window_name = (
    f"Fasciculation ROI Selector - "
    f"{scale_name} - "
    f"{ROI_SIZE}x{ROI_SIZE}"
)


cv2.namedWindow(
    window_name,
    cv2.WINDOW_NORMAL
)


# ============================================================
# CLIP INDEX
# ============================================================

clip_index = 0


# ============================================================
# MAIN LOOP
# ============================================================

while clip_index < len(df):


    # ========================================================
    # GET CURRENT ROW
    # ========================================================

    row = df.iloc[
        clip_index
    ]


    print()
    print("=" * 75)

    print(
        f"CLIP "
        f"{clip_index + 1} / "
        f"{len(df)}"
    )

    print("=" * 75)


    # ========================================================
    # EXCEL INFORMATION
    # ========================================================

    video_name = str(
        row["Main_Video"]
    ).strip()


    clip_number = row[
        "Clip_in_Main_Video"
    ]


    interval = str(
        row["Fasciculation_Interval"]
    ).strip()


    # ========================================================
    # ORIGINAL ANNOTATED ROI
    # ========================================================

    original_xmin = int(
        row["ROI_xmin"]
    )

    original_xmax = int(
        row["ROI_xmax"]
    )

    original_ymin = int(
        row["ROI_ymin"]
    )

    original_ymax = int(
        row["ROI_ymax"]
    )


    original_width = (
        original_xmax
        - original_xmin
    )


    original_height = (
        original_ymax
        - original_ymin
    )


    # ========================================================
    # ORIGINAL ROI CENTER
    # ========================================================

    original_center_x = (
        original_xmin
        + original_xmax
    ) // 2


    original_center_y = (
        original_ymin
        + original_ymax
    ) // 2


    # ========================================================
    # PRINT INFORMATION
    # ========================================================

    print(
        f"Main video: {video_name}"
    )

    print(
        f"Clip: {clip_number}"
    )

    print(
        f"Interval: {interval}"
    )

    print(
        f"Original ROI size: "
        f"{original_width} × "
        f"{original_height}"
    )

    print(
        f"Original ROI_xmin = "
        f"{original_xmin}"
    )

    print(
        f"Original ROI_xmax = "
        f"{original_xmax}"
    )

    print(
        f"Original ROI_ymin = "
        f"{original_ymin}"
    )

    print(
        f"Original ROI_ymax = "
        f"{original_ymax}"
    )


    # ========================================================
    # PARSE INTERVAL
    # ========================================================

    try:

        start_seconds, end_seconds = (
            parse_interval(
                interval
            )
        )

    except ValueError as error:

        print(
            f"ERROR: {error}"
        )

        clip_index += 1

        continue


    # ========================================================
    # FIND VIDEO
    # ========================================================

    video_path = find_video(
        video_name
    )


    if video_path is None:

        print()
        print(
            "WARNING: Video not found."
        )

        print(
            f"Expected: {video_name}"
        )

        print(
            f"Dataset: {VIDEO_FOLDER}"
        )

        print()
        print(
            "Press N to skip."
        )


        key = cv2.waitKey(
            0
        ) & 0xFF


        if key == ord("n"):

            clip_index += 1

            continue


        if key == ord("q"):

            break


        continue


    # ========================================================
    # OPEN VIDEO
    # ========================================================

    cap = cv2.VideoCapture(
        video_path
    )


    if not cap.isOpened():

        print(
            "ERROR: Cannot open video."
        )

        clip_index += 1

        continue


    # ========================================================
    # VIDEO INFORMATION
    # ========================================================

    fps = cap.get(
        cv2.CAP_PROP_FPS
    )


    if fps <= 0:

        fps = 50.0


    frame_width = int(
        cap.get(
            cv2.CAP_PROP_FRAME_WIDTH
        )
    )


    frame_height = int(
        cap.get(
            cv2.CAP_PROP_FRAME_HEIGHT
        )
    )


    print(
        f"Video resolution: "
        f"{frame_width} × "
        f"{frame_height}"
    )


    print(
        f"FPS: {fps}"
    )


    # ========================================================
    # FRAME RANGE
    # ========================================================

    start_frame = int(
        round(
            start_seconds * fps
        )
    )


    end_frame = int(
        round(
            end_seconds * fps
        )
    )


    if end_frame <= start_frame:

        end_frame = (
            start_frame + 1
        )


    print(
        f"Start frame: {start_frame}"
    )

    print(
        f"End frame: {end_frame}"
    )


    print(
        f"Duration: "
        f"{end_seconds - start_seconds:.3f} sec"
    )


    # ========================================================
    # INITIAL FIXED ROI
    #
    # CENTERED ON ORIGINAL ANNOTATED ROI
    #
    # NO Center_X / Center_Y FROM EXCEL.
    # ========================================================

    current_x = (
        original_center_x
        - ROI_SIZE // 2
    )


    current_y = (
        original_center_y
        - ROI_SIZE // 2
    )


    current_x, current_y = (
        keep_roi_inside(
            current_x,
            current_y,
            frame_width,
            frame_height,
            ROI_SIZE
        )
    )


    # ========================================================
    # MOUSE PARAMETERS
    # ========================================================

    mouse_params = {

        "frame_width":
            frame_width,

        "frame_height":
            frame_height,

        "video_top_offset":
            INFO_HEIGHT
    }


    cv2.setMouseCallback(
        window_name,
        mouse_callback,
        mouse_params
    )


    # ========================================================
    # PLAYBACK VARIABLES
    # ========================================================

    paused = False

    saved = False


    current_frame_number = (
        start_frame
    )


    # ========================================================
    # START AT FASCICULATION
    # ========================================================

    cap.set(
        cv2.CAP_PROP_POS_FRAMES,
        start_frame
    )


    # ========================================================
    # LOOP FASCICULATION INTERVAL
    # ========================================================

    while True:


        # ====================================================
        # READ FRAME
        # ====================================================

        if not paused:

            ret, frame = cap.read()


            if not ret:

                cap.set(
                    cv2.CAP_PROP_POS_FRAMES,
                    start_frame
                )

                current_frame_number = (
                    start_frame
                )

                continue


            current_frame_number = int(
                cap.get(
                    cv2.CAP_PROP_POS_FRAMES
                )
            ) - 1


            # ------------------------------------------------
            # LOOP AT END OF INTERVAL
            # ------------------------------------------------

            if (
                current_frame_number
                >= end_frame
            ):

                cap.set(
                    cv2.CAP_PROP_POS_FRAMES,
                    start_frame
                )

                current_frame_number = (
                    start_frame
                )

                continue


        # ====================================================
        # FIXED ROI COORDINATES
        # ====================================================

        roi_xmin = int(
            current_x
        )


        roi_xmax = int(
            current_x + ROI_SIZE
        )


        roi_ymin = int(
            current_y
        )


        roi_ymax = int(
            current_y + ROI_SIZE
        )


        # ====================================================
        # FIXED ROI CENTER
        # ====================================================

        fixed_center_x = (
            roi_xmin
            + ROI_SIZE // 2
        )


        fixed_center_y = (
            roi_ymin
            + ROI_SIZE // 2
        )


        # ====================================================
        # CREATE INFORMATION AREA
        #
        # IMPORTANT:
        #
        # This is a NEW area ABOVE the video.
        #
        # The original video frame remains COMPLETE.
        # ====================================================

        info_area = np.zeros(
            (
                INFO_HEIGHT,
                frame_width,
                3
            ),
            dtype=np.uint8
        )


        # ====================================================
        # INFORMATION TEXT
        # ====================================================

        info1 = (
            f"{scale_name} | "
            f"FIXED ROI: "
            f"{ROI_SIZE} x {ROI_SIZE}"
        )


        info2 = (
            f"Original ROI: "
            f"{original_width} x "
            f"{original_height}"
        )


        info3 = (
            f"ROI_xmin = {roi_xmin}    "
            f"|    ROI_xmax = {roi_xmax}"
        )


        info4 = (
            f"ROI_ymin = {roi_ymin}    "
            f"|    ROI_ymax = {roi_ymax}"
        )


        info5 = (
            f"Frame: "
            f"{current_frame_number}    "
            f"|    Fasciculation: "
            f"{interval}"
        )


        # ====================================================
        # DRAW INFORMATION
        # ====================================================

        cv2.putText(
            info_area,
            info1,
            (15, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.70,
            (255, 255, 255),
            2
        )


        cv2.putText(
            info_area,
            info2,
            (15, 60),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.60,
            (255, 255, 255),
            2
        )


        cv2.putText(
            info_area,
            info3,
            (15, 90),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.60,
            (255, 255, 255),
            2
        )


        cv2.putText(
            info_area,
            info4,
            (15, 120),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.60,
            (255, 255, 255),
            2
        )


        cv2.putText(
            info_area,
            info5,
            (15, 150),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.52,
            (255, 255, 255),
            2
        )


        # ====================================================
        # DRAW ORIGINAL ROI ON COMPLETE FRAME
        # ====================================================

        display_frame = frame.copy()


        # ----------------------------------------------------
        # ORIGINAL ROI = YELLOW
        # ----------------------------------------------------

        cv2.rectangle(
            display_frame,

            (
                original_xmin,
                original_ymin
            ),

            (
                original_xmax,
                original_ymax
            ),

            (0, 255, 255),

            2
        )


        # ----------------------------------------------------
        # ORIGINAL ROI CENTER
        # ----------------------------------------------------

        cv2.drawMarker(
            display_frame,

            (
                original_center_x,
                original_center_y
            ),

            (0, 255, 255),

            cv2.MARKER_CROSS,

            15,

            2
        )


        # ====================================================
        # DRAW FIXED ROI
        # ====================================================

        # ----------------------------------------------------
        # FIXED ROI = GREEN
        # ----------------------------------------------------

        cv2.rectangle(
            display_frame,

            (
                roi_xmin,
                roi_ymin
            ),

            (
                roi_xmax,
                roi_ymax
            ),

            (0, 255, 0),

            3
        )


        # ----------------------------------------------------
        # FIXED ROI CENTER
        # ----------------------------------------------------

        cv2.drawMarker(
            display_frame,

            (
                fixed_center_x,
                fixed_center_y
            ),

            (0, 255, 0),

            cv2.MARKER_CROSS,

            15,

            2
        )


        # ====================================================
        # COMBINE INFORMATION + COMPLETE VIDEO
        #
        # NO VIDEO PIXELS ARE REMOVED.
        # ====================================================

        display = cv2.vconcat(
            [
                info_area,
                display_frame
            ]
        )


        # ====================================================
        # BOTTOM INSTRUCTIONS
        #
        # Put instructions in the information area,
        # not over the video.
        # ====================================================

        instruction = (
            "DRAG green ROI | "
            "S=Save | P=Pause | "
            "N=Next | B=Previous | "
            "R=Reset | Q=Quit"
        )


        # We do not draw this over the video.
        # Instead, draw it on the top area.

        cv2.putText(
            display,
            instruction,
            (
                500,
                150
            ),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.48,
            (255, 255, 255),
            1
        )


        # ====================================================
        # SHOW COMPLETE FRAME
        # ====================================================

        cv2.imshow(
            window_name,
            display
        )


        # ====================================================
        # PLAYBACK SPEED
        # ====================================================

        wait_time = max(
            1,
            int(
                1000 / fps
            )
        )


        key = cv2.waitKey(
            wait_time
        ) & 0xFF


        # ====================================================
        # SAVE
        # ====================================================

        if key == ord("s"):


            selected_xmin = int(
                current_x
            )

            selected_xmax = int(
                current_x + ROI_SIZE
            )

            selected_ymin = int(
                current_y
            )

            selected_ymax = int(
                current_y + ROI_SIZE
            )


            selected_center_x = (
                current_x
                + ROI_SIZE // 2
            )

            selected_center_y = (
                current_y
                + ROI_SIZE // 2
            )


            print()
            print("-" * 65)
            print("FIXED ROI SAVED")
            print("-" * 65)


            print(
                f"Scale       = {scale_name}"
            )

            print(
                f"ROI size    = "
                f"{ROI_SIZE} × {ROI_SIZE}"
            )

            print(
                f"ROI_xmin    = "
                f"{selected_xmin}"
            )

            print(
                f"ROI_xmax    = "
                f"{selected_xmax}"
            )

            print(
                f"ROI_ymin    = "
                f"{selected_ymin}"
            )

            print(
                f"ROI_ymax    = "
                f"{selected_ymax}"
            )

            print(
                f"ROI center  = "
                f"({selected_center_x}, "
                f"{selected_center_y})"
            )


            # =================================================
            # SAVE RESULT
            # =================================================

            results.append({

                "Scale":
                    scale_name,

                "ROI_Size":
                    ROI_SIZE,

                "Main_Video":
                    video_name,

                "Clip_in_Main_Video":
                    clip_number,

                "Fasciculation_Interval":
                    interval,


                # ------------------------------------------------
                # ORIGINAL ROI
                # ------------------------------------------------

                "Original_ROI_xmin":
                    original_xmin,

                "Original_ROI_xmax":
                    original_xmax,

                "Original_ROI_ymin":
                    original_ymin,

                "Original_ROI_ymax":
                    original_ymax,

                "Original_ROI_Width":
                    original_width,

                "Original_ROI_Height":
                    original_height,


                # ------------------------------------------------
                # SELECTED ROI
                # ------------------------------------------------

                "ROI_xmin":
                    selected_xmin,

                "ROI_xmax":
                    selected_xmax,

                "ROI_ymin":
                    selected_ymin,

                "ROI_ymax":
                    selected_ymax,

                "ROI_Width":
                    ROI_SIZE,

                "ROI_Height":
                    ROI_SIZE,

                "ROI_Center_X":
                    selected_center_x,

                "ROI_Center_Y":
                    selected_center_y

            })


            saved = True


            print()
            print(
                "ROI saved successfully."
            )

            print(
                "Press N for the next clip."
            )


        # ====================================================
        # PAUSE
        # ====================================================

        elif key == ord("p"):

            paused = not paused


            if paused:

                print(
                    "Playback PAUSED."
                )

            else:

                print(
                    "Playback RESUMED."
                )


        # ====================================================
        # RESET
        # ====================================================

        elif key == ord("r"):


            current_x = (
                original_center_x
                - ROI_SIZE // 2
            )


            current_y = (
                original_center_y
                - ROI_SIZE // 2
            )


            current_x, current_y = (
                keep_roi_inside(
                    current_x,
                    current_y,
                    frame_width,
                    frame_height,
                    ROI_SIZE
                )
            )


            print(
                "ROI reset to the center "
                "of the original annotated ROI."
            )


        # ====================================================
        # NEXT
        # ====================================================

        elif key == ord("n"):


            if not saved:

                print()
                print(
                    "WARNING: ROI has not been saved."
                )

                print(
                    "Press S to save."
                )

                print(
                    "Press N again to skip."
                )


                next_key = cv2.waitKey(
                    0
                ) & 0xFF


                if next_key == ord("n"):

                    cap.release()

                    clip_index += 1

                    break


                elif next_key == ord("q"):

                    cap.release()

                    cv2.destroyAllWindows()

                    raise SystemExit


            else:

                cap.release()

                clip_index += 1

                break


        # ====================================================
        # PREVIOUS
        # ====================================================

        elif key == ord("b"):


            cap.release()


            if clip_index > 0:

                clip_index -= 1

            else:

                print(
                    "Already at first clip."
                )


            break


        # ====================================================
        # QUIT
        # ====================================================

        elif key == ord("q"):


            cap.release()

            cv2.destroyAllWindows()


            # ------------------------------------------------
            # SAVE PROGRESS
            # ------------------------------------------------

            if results:

                output_df = pd.DataFrame(
                    results
                )


                output_path = os.path.join(
                    os.path.dirname(
                        EXCEL_PATH
                    ),

                    f"Selected_ROIs_"
                    f"{scale_name}_"
                    f"{ROI_SIZE}x{ROI_SIZE}.xlsx"
                )


                output_df.to_excel(
                    output_path,
                    index=False
                )


                print()
                print("=" * 75)
                print("PROGRAM STOPPED")
                print("=" * 75)

                print(
                    f"Saved ROIs: "
                    f"{len(results)}"
                )

                print(
                    f"Output file:\n"
                    f"{output_path}"
                )


            else:

                print(
                    "\nNo ROIs were saved."
                )


            raise SystemExit


# ============================================================
# CLOSE
# ============================================================

cv2.destroyAllWindows()


# ============================================================
# SAVE FINAL RESULTS
# ============================================================

if results:


    output_df = pd.DataFrame(
        results
    )


    output_path = os.path.join(
        os.path.dirname(
            EXCEL_PATH
        ),

        f"Selected_ROIs_"
        f"{scale_name}_"
        f"{ROI_SIZE}x{ROI_SIZE}.xlsx"
    )


    output_df.to_excel(
        output_path,
        index=False
    )


    print()
    print("=" * 75)
    print("ALL CLIPS COMPLETED")
    print("=" * 75)


    print(
        f"Total saved ROIs: "
        f"{len(results)}"
    )


    print(
        f"Output file:\n"
        f"{output_path}"
    )


else:

    print(
        "\nNo ROIs were saved."
    )