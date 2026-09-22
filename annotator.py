import sys
import os
import csv
import cv2

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QLabel,
    QPushButton,
    QFileDialog,
    QHBoxLayout,
    QVBoxLayout,
    QComboBox,
    QMessageBox,
    QSlider,
    QSizePolicy,
    QGroupBox,
    QSpinBox,
)

from PySide6.QtCore import (
    Qt,
    QTimer,
    QRect,
    QPoint,
    Signal,
)

from PySide6.QtGui import (
    QPainter,
    QPen,
    QColor,
    QFont,
    QImage,
    QPixmap,
)


# ============================================================
# VIDEO / ROI WIDGET
# ============================================================

class VideoWidget(QWidget):

    roi_created = Signal(int)
    roi_selected = Signal(int)
    roi_changed = Signal(int)

    def __init__(self, parent=None):

        super().__init__(parent)

        self.setMinimumSize(
            500,
            350
        )

        self.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding
        )

        self.setMouseTracking(True)

        self.setStyleSheet(
            "background-color: black;"
        )

        # ====================================================
        # VIDEO
        # ====================================================

        self.frame = None

        self.frame_width = 0
        self.frame_height = 0

        # Displayed video rectangle
        self.display_x = 0
        self.display_y = 0

        self.display_width = 0
        self.display_height = 0

        # ====================================================
        # ROIs
        # ====================================================

        # Each ROI:
        #
        # (xmin, ymin, xmax, ymax)
        #
        self.rois = []

        self.selected_roi = -1

        # ====================================================
        # NEW ROI DRAWING
        # ====================================================

        self.drawing = False

        self.start_point = None
        self.current_point = None

        # ====================================================
        # MOVE / RESIZE
        # ====================================================

        self.dragging = False

        self.drag_mode = None

        self.drag_start_original = None

        self.original_roi_before_drag = None

        # Size of resize handles
        self.handle_size = 10

    # ========================================================
    # SET FRAME
    # ========================================================

    def set_video_frame(self, frame):

        self.frame = frame

        self.frame_height, self.frame_width = (
            frame.shape[:2]
        )

        self.update()

    # ========================================================
    # CALCULATE DISPLAY RECTANGLE
    # ========================================================

    def calculate_display_rect(self):

        if self.frame is None:
            return

        widget_width = self.width()
        widget_height = self.height()

        if widget_width <= 0:
            return

        if widget_height <= 0:
            return

        video_ratio = (
            self.frame_width /
            self.frame_height
        )

        widget_ratio = (
            widget_width /
            widget_height
        )

        if video_ratio > widget_ratio:

            self.display_width = widget_width

            self.display_height = int(
                widget_width /
                video_ratio
            )

        else:

            self.display_height = widget_height

            self.display_width = int(
                widget_height *
                video_ratio
            )

        self.display_x = (
            widget_width -
            self.display_width
        ) // 2

        self.display_y = (
            widget_height -
            self.display_height
        ) // 2

    # ========================================================
    # ORIGINAL VIDEO COORDINATE
    # TO DISPLAY COORDINATE
    # ========================================================

    def original_to_display(
        self,
        x,
        y
    ):

        if self.frame_width <= 0:
            return QPoint(0, 0)

        if self.frame_height <= 0:
            return QPoint(0, 0)

        dx = int(
            self.display_x +
            (
                x *
                self.display_width /
                self.frame_width
            )
        )

        dy = int(
            self.display_y +
            (
                y *
                self.display_height /
                self.frame_height
            )
        )

        return QPoint(
            dx,
            dy
        )

    # ========================================================
    # DISPLAY COORDINATE
    # TO ORIGINAL VIDEO COORDINATE
    # ========================================================

    def display_to_original(
        self,
        point
    ):

        if self.frame is None:
            return None

        if self.display_width <= 0:
            return None

        if self.display_height <= 0:
            return None

        x = (
            point.x() -
            self.display_x
        )

        y = (
            point.y() -
            self.display_y
        )

        if x < 0 or y < 0:
            return None

        if x >= self.display_width:
            return None

        if y >= self.display_height:
            return None

        original_x = int(
            x *
            self.frame_width /
            self.display_width
        )

        original_y = int(
            y *
            self.frame_height /
            self.display_height
        )

        original_x = max(
            0,
            min(
                original_x,
                self.frame_width - 1
            )
        )

        original_y = max(
            0,
            min(
                original_y,
                self.frame_height - 1
            )
        )

        return (
            original_x,
            original_y
        )

    # ========================================================
    # ROI → DISPLAY RECTANGLE
    # ========================================================

    def roi_to_display_rect(
        self,
        roi
    ):

        xmin, ymin, xmax, ymax = roi

        p1 = self.original_to_display(
            xmin,
            ymin
        )

        p2 = self.original_to_display(
            xmax,
            ymax
        )

        return QRect(
            p1,
            p2
        ).normalized()

    # ========================================================
    # PAINT EVENT
    # ========================================================

    def paintEvent(self, event):

        painter = QPainter(self)

        painter.fillRect(
            self.rect(),
            Qt.black
        )

        if self.frame is None:

            painter.setPen(
                Qt.white
            )

            painter.drawText(
                self.rect(),
                Qt.AlignCenter,
                "Open a medical video"
            )

            painter.end()

            return

        self.calculate_display_rect()

        # ====================================================
        # CONVERT FRAME
        # ====================================================

        rgb = cv2.cvtColor(
            self.frame,
            cv2.COLOR_BGR2RGB
        )

        height, width, channels = (
            rgb.shape
        )

        bytes_per_line = (
            channels * width
        )

        image = QImage(
            rgb.data,
            width,
            height,
            bytes_per_line,
            QImage.Format_RGB888
        )

        pixmap = QPixmap.fromImage(
            image
        )

        pixmap = pixmap.scaled(
            self.display_width,
            self.display_height,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        painter.drawPixmap(
            self.display_x,
            self.display_y,
            pixmap
        )

        # ====================================================
        # DRAW SAVED ROIS
        # ====================================================

        for index, roi in enumerate(
            self.rois
        ):

            xmin, ymin, xmax, ymax = roi

            rect = self.roi_to_display_rect(
                roi
            )

            # ------------------------------------------------
            # Selected ROI = GREEN
            # ------------------------------------------------

            if index == self.selected_roi:

                painter.setPen(
                    QPen(
                        QColor(
                            0,
                            255,
                            0
                        ),
                        3
                    )
                )

            # ------------------------------------------------
            # Other ROIs = RED
            # ------------------------------------------------

            else:

                painter.setPen(
                    QPen(
                        QColor(
                            255,
                            0,
                            0
                        ),
                        3
                    )
                )

            painter.drawRect(
                rect
            )

            # =================================================
            # ROI LABEL
            # =================================================

            painter.setFont(
                QFont(
                    "Arial",
                    11,
                    QFont.Bold
                )
            )

            painter.setPen(
                QPen(
                    QColor(
                        255,
                        255,
                        0
                    )
                )

            )

            painter.drawText(
                rect.topLeft()
                + QPoint(
                    5,
                    18
                ),
                f"ROI {index + 1}"
            )

            # =================================================
            # COORDINATES
            # =================================================

            coordinate_text = (
                f"X:{xmin}-{xmax} "
                f"Y:{ymin}-{ymax}"
            )

            painter.drawText(
                rect.bottomLeft()
                + QPoint(
                    0,
                    20
                ),
                coordinate_text
            )

            # =================================================
            # WIDTH / HEIGHT
            # =================================================

            size_text = (
                f"W:{xmax - xmin} "
                f"H:{ymax - ymin}"
            )

            painter.drawText(
                rect.bottomLeft()
                + QPoint(
                    0,
                    38
                ),
                size_text
            )

            # =================================================
            # RESIZE HANDLES
            # =================================================

            if index == self.selected_roi:

                self.draw_resize_handles(
                    painter,
                    rect
                )

        # ====================================================
        # DRAW NEW ROI WHILE MOUSE IS DRAGGING
        # ====================================================

        if (
            self.drawing
            and
            self.start_point is not None
            and
            self.current_point is not None
        ):

            rect = QRect(
                self.start_point,
                self.current_point
            ).normalized()

            painter.setPen(
                QPen(
                    QColor(
                        255,
                        255,
                        0
                    ),
                    2,
                    Qt.DashLine
                )
            )

            painter.drawRect(
                rect
            )

        painter.end()

    # ========================================================
    # DRAW 8 RESIZE HANDLES
    # ========================================================

    def draw_resize_handles(
        self,
        painter,
        rect
    ):

        s = self.handle_size

        points = [

            # Top-left
            rect.topLeft(),

            # Top
            QPoint(
                rect.center().x(),
                rect.top()
            ),

            # Top-right
            rect.topRight(),

            # Left
            QPoint(
                rect.left(),
                rect.center().y()
            ),

            # Right
            QPoint(
                rect.right(),
                rect.center().y()
            ),

            # Bottom-left
            rect.bottomLeft(),

            # Bottom
            QPoint(
                rect.center().x(),
                rect.bottom()
            ),

            # Bottom-right
            rect.bottomRight(),
        ]

        painter.setPen(
            QPen(
                QColor(
                    0,
                    255,
                    0
                ),
                2
            )
        )

        painter.setBrush(
            QColor(
                255,
                255,
                255
            )
        )

        for point in points:

            painter.drawRect(
                point.x() - s // 2,
                point.y() - s // 2,
                s,
                s
            )

    # ========================================================
    # FIND RESIZE HANDLE
    # ========================================================

    def get_handle_at(
        self,
        point,
        rect
    ):

        tolerance = (
            self.handle_size + 6
        )

        handles = {

            "TL":
                rect.topLeft(),

            "T":
                QPoint(
                    rect.center().x(),
                    rect.top()
                ),

            "TR":
                rect.topRight(),

            "L":
                QPoint(
                    rect.left(),
                    rect.center().y()
                ),

            "R":
                QPoint(
                    rect.right(),
                    rect.center().y()
                ),

            "BL":
                rect.bottomLeft(),

            "B":
                QPoint(
                    rect.center().x(),
                    rect.bottom()
                ),

            "BR":
                rect.bottomRight()
        }

        for name, hp in handles.items():

            if (
                abs(
                    point.x() - hp.x()
                ) <= tolerance
                and
                abs(
                    point.y() - hp.y()
                ) <= tolerance
            ):

                return name

        return None

    # ========================================================
    # FIND ROI UNDER MOUSE
    # ========================================================

    def find_roi_at_point(
        self,
        point
    ):

        # Check selected ROI first
        if (
            self.selected_roi >= 0
            and
            self.selected_roi < len(
                self.rois
            )
        ):

            rect = self.roi_to_display_rect(
                self.rois[
                    self.selected_roi
                ]
            )

            if rect.contains(point):

                return self.selected_roi

        # Check other ROIs
        for index in reversed(
            range(
                len(self.rois)
            )
        ):

            rect = self.roi_to_display_rect(
                self.rois[index]
            )

            if rect.contains(point):

                return index

        return -1

    # ========================================================
    # MOUSE PRESS
    # ========================================================

    def mousePressEvent(
        self,
        event
    ):

        if event.button() != Qt.LeftButton:
            return

        point = (
            event.position()
            .toPoint()
        )

        # ====================================================
        # CHECK SELECTED ROI HANDLES
        # ====================================================

        if (
            self.selected_roi >= 0
            and
            self.selected_roi < len(
                self.rois
            )
        ):

            rect = self.roi_to_display_rect(
                self.rois[
                    self.selected_roi
                ]
            )

            handle = self.get_handle_at(
                point,
                rect
            )

            if handle is not None:

                original = (
                    self.display_to_original(
                        point
                    )
                )

                if original is None:
                    return

                self.dragging = True

                self.drag_mode = handle

                self.drag_start_original = (
                    original
                )

                self.original_roi_before_drag = (
                    self.rois[
                        self.selected_roi
                    ]
                )

                return

        # ====================================================
        # CHECK EXISTING ROI
        # ====================================================

        roi_index = self.find_roi_at_point(
            point
        )

        if roi_index >= 0:

            self.selected_roi = (
                roi_index
            )

            self.roi_selected.emit(
                roi_index
            )

            original = (
                self.display_to_original(
                    point
                )
            )

            if original is None:
                return

            self.dragging = True

            self.drag_mode = "MOVE"

            self.drag_start_original = (
                original
            )

            self.original_roi_before_drag = (
                self.rois[
                    roi_index
                ]
            )

            self.update()

            return

        # ====================================================
        # CREATE NEW ROI
        # ====================================================

        original = self.display_to_original(
            point
        )

        if original is None:
            return

        self.drawing = True

        self.start_point = point

        self.current_point = point

        self.update()

    # ========================================================
    # MOUSE MOVE
    # ========================================================

    def mouseMoveEvent(
        self,
        event
    ):

        point = (
            event.position()
            .toPoint()
        )

        # ====================================================
        # MOVING / RESIZING ROI
        # ====================================================

        if self.dragging:

            current_original = (
                self.display_to_original(
                    point
                )
            )

            if current_original is None:
                return

            start_x, start_y = (
                self.drag_start_original
            )

            current_x, current_y = (
                current_original
            )

            (
                old_xmin,
                old_ymin,
                old_xmax,
                old_ymax
            ) = (
                self.original_roi_before_drag
            )

            dx = (
                current_x -
                start_x
            )

            dy = (
                current_y -
                start_y
            )

            xmin = old_xmin
            ymin = old_ymin
            xmax = old_xmax
            ymax = old_ymax

            # =================================================
            # MOVE WHOLE ROI
            # =================================================

            if self.drag_mode == "MOVE":

                width = (
                    old_xmax -
                    old_xmin
                )

                height = (
                    old_ymax -
                    old_ymin
                )

                xmin = old_xmin + dx

                ymin = old_ymin + dy

                xmax = xmin + width

                ymax = ymin + height

                # ---------------------------------------------
                # Keep inside video
                # ---------------------------------------------

                if xmin < 0:

                    xmin = 0

                    xmax = width

                if ymin < 0:

                    ymin = 0

                    ymax = height

                if xmax >= self.frame_width:

                    xmax = (
                        self.frame_width - 1
                    )

                    xmin = (
                        xmax -
                        width
                    )

                if ymax >= self.frame_height:

                    ymax = (
                        self.frame_height - 1
                    )

                    ymin = (
                        ymax -
                        height
                    )

            # =================================================
            # TOP LEFT
            # =================================================

            elif self.drag_mode == "TL":

                xmin = min(
                    current_x,
                    old_xmax - 5
                )

                ymin = min(
                    current_y,
                    old_ymax - 5
                )

            # =================================================
            # TOP
            # =================================================

            elif self.drag_mode == "T":

                ymin = min(
                    current_y,
                    old_ymax - 5
                )

            # =================================================
            # TOP RIGHT
            # =================================================

            elif self.drag_mode == "TR":

                xmax = max(
                    current_x,
                    old_xmin + 5
                )

                ymin = min(
                    current_y,
                    old_ymax - 5
                )

            # =================================================
            # LEFT
            # =================================================

            elif self.drag_mode == "L":

                xmin = min(
                    current_x,
                    old_xmax - 5
                )

            # =================================================
            # RIGHT
            # =================================================

            elif self.drag_mode == "R":

                xmax = max(
                    current_x,
                    old_xmin + 5
                )

            # =================================================
            # BOTTOM LEFT
            # =================================================

            elif self.drag_mode == "BL":

                xmin = min(
                    current_x,
                    old_xmax - 5
                )

                ymax = max(
                    current_y,
                    old_ymin + 5
                )

            # =================================================
            # BOTTOM
            # =================================================

            elif self.drag_mode == "B":

                ymax = max(
                    current_y,
                    old_ymin + 5
                )

            # =================================================
            # BOTTOM RIGHT
            # =================================================

            elif self.drag_mode == "BR":

                xmax = max(
                    current_x,
                    old_xmin + 5
                )

                ymax = max(
                    current_y,
                    old_ymin + 5
                )

            # =================================================
            # CLAMP TO VIDEO
            # =================================================

            xmin = max(
                0,
                min(
                    int(xmin),
                    self.frame_width - 2
                )
            )

            xmax = max(
                1,
                min(
                    int(xmax),
                    self.frame_width - 1
                )
            )

            ymin = max(
                0,
                min(
                    int(ymin),
                    self.frame_height - 2
                )
            )

            ymax = max(
                1,
                min(
                    int(ymax),
                    self.frame_height - 1
                )
            )

            # =================================================
            # SAVE LIVE ROI
            # =================================================

            self.rois[
                self.selected_roi
            ] = (
                xmin,
                ymin,
                xmax,
                ymax
            )

            # Tell main window to update
            self.roi_changed.emit(
                self.selected_roi
            )

            self.update()

            return

        # ====================================================
        # DRAW NEW ROI
        # ====================================================

        if self.drawing:

            self.current_point = point

            self.update()

            return

        # ====================================================
        # CURSOR
        # ====================================================

        if (
            self.selected_roi >= 0
            and
            self.selected_roi < len(
                self.rois
            )
        ):

            rect = self.roi_to_display_rect(
                self.rois[
                    self.selected_roi
                ]
            )

            handle = self.get_handle_at(
                point,
                rect
            )

            cursor_map = {

                "TL":
                    Qt.SizeFDiagCursor,

                "BR":
                    Qt.SizeFDiagCursor,

                "TR":
                    Qt.SizeBDiagCursor,

                "BL":
                    Qt.SizeBDiagCursor,

                "T":
                    Qt.SizeVerCursor,

                "B":
                    Qt.SizeVerCursor,

                "L":
                    Qt.SizeHorCursor,

                "R":
                    Qt.SizeHorCursor,
            }

            if handle in cursor_map:

                self.setCursor(
                    cursor_map[handle]
                )

                return

            if rect.contains(point):

                self.setCursor(
                    Qt.SizeAllCursor
                )

                return

        self.setCursor(
            Qt.ArrowCursor
        )

    # ========================================================
    # MOUSE RELEASE
    # ========================================================

    def mouseReleaseEvent(
        self,
        event
    ):

        if event.button() != Qt.LeftButton:
            return

        # ====================================================
        # FINISH MOVE / RESIZE
        # ====================================================

        if self.dragging:

            self.dragging = False

            self.drag_mode = None

            self.drag_start_original = None

            self.original_roi_before_drag = None

            self.setCursor(
                Qt.ArrowCursor
            )

            self.update()

            return

        # ====================================================
        # FINISH NEW ROI
        # ====================================================

        if not self.drawing:
            return

        self.drawing = False

        self.current_point = (
            event.position()
            .toPoint()
        )

        p1 = self.display_to_original(
            self.start_point
        )

        p2 = self.display_to_original(
            self.current_point
        )

        if p1 is None or p2 is None:

            self.update()

            return

        x1, y1 = p1

        x2, y2 = p2

        xmin = min(
            x1,
            x2
        )

        xmax = max(
            x1,
            x2
        )

        ymin = min(
            y1,
            y2
        )

        ymax = max(
            y1,
            y2
        )

        # Ignore very small boxes
        if (
            xmax - xmin < 5
            or
            ymax - ymin < 5
        ):

            self.update()

            return

        self.rois.append(
            (
                xmin,
                ymin,
                xmax,
                ymax
            )
        )

        self.selected_roi = (
            len(self.rois) - 1
        )

        self.roi_created.emit(
            self.selected_roi
        )

        self.update()

    # ========================================================
    # SET ROI
    # ========================================================

    def set_roi(
        self,
        index,
        xmin,
        ymin,
        xmax,
        ymax
    ):

        if index < 0:
            return

        if index >= len(
            self.rois
        ):
            return

        xmin = int(xmin)

        ymin = int(ymin)

        xmax = int(xmax)

        ymax = int(ymax)

        # Ensure correct ordering
        if xmax < xmin:

            xmin, xmax = (
                xmax,
                xmin
            )

        if ymax < ymin:

            ymin, ymax = (
                ymax,
                ymin
            )

        xmin = max(
            0,
            min(
                xmin,
                self.frame_width - 2
            )
        )

        xmax = max(
            1,
            min(
                xmax,
                self.frame_width - 1
            )
        )

        ymin = max(
            0,
            min(
                ymin,
                self.frame_height - 2
            )
        )

        ymax = max(
            1,
            min(
                ymax,
                self.frame_height - 1
            )
        )

        self.rois[index] = (
            xmin,
            ymin,
            xmax,
            ymax
        )

        self.selected_roi = index

        self.roi_changed.emit(
            index
        )

        self.update()

    # ========================================================
    # ADD MANUAL ROI
    # ========================================================

    def add_manual_roi(
        self,
        xmin,
        ymin,
        xmax,
        ymax
    ):

        if self.frame is None:
            return -1

        xmin = int(xmin)

        ymin = int(ymin)

        xmax = int(xmax)

        ymax = int(ymax)

        if xmax <= xmin:
            return -1

        if ymax <= ymin:
            return -1

        xmin = max(
            0,
            min(
                xmin,
                self.frame_width - 2
            )
        )

        xmax = max(
            1,
            min(
                xmax,
                self.frame_width - 1
            )
        )

        ymin = max(
            0,
            min(
                ymin,
                self.frame_height - 2
            )
        )

        ymax = max(
            1,
            min(
                ymax,
                self.frame_height - 1
            )
        )

        self.rois.append(
            (
                xmin,
                ymin,
                xmax,
                ymax
            )
        )

        self.selected_roi = (
            len(self.rois) - 1
        )

        self.roi_created.emit(
            self.selected_roi
        )

        self.update()

        return self.selected_roi

    # ========================================================
    # DELETE SELECTED ROI
    # ========================================================

    def delete_selected_roi(self):

        if (
            self.selected_roi < 0
            or
            self.selected_roi >= len(
                self.rois
            )
        ):
            return

        self.rois.pop(
            self.selected_roi
        )

        if not self.rois:

            self.selected_roi = -1

        else:

            self.selected_roi = min(
                self.selected_roi,
                len(self.rois) - 1
            )

        self.update()

    # ========================================================
    # RESET ALL ROIS
    # ========================================================

    def reset_rois(self):

        self.rois.clear()

        self.selected_roi = -1

        self.dragging = False

        self.drawing = False

        self.update()

    # ========================================================
    # RESIZE EVENT
    # ========================================================

    def resizeEvent(
        self,
        event
    ):

        self.update()

        super().resizeEvent(
            event
        )


# ============================================================
# MAIN WINDOW
# ============================================================

class FasciculationAnnotator(
    QMainWindow
):

    def __init__(self):

        super().__init__()

        self.setWindowTitle(
            "Fasciculation Video Annotator"
        )

        self.resize(
            1500,
            950
        )

        # ====================================================
        # VIDEO
        # ====================================================

        self.cap = None

        self.video_path = None

        self.fps = 30.0

        self.total_frames = 0

        self.frame_width = 0

        self.frame_height = 0

        self.current_frame = 0

        # ====================================================
        # PLAYBACK
        # ====================================================

        self.playing = False

        self.speed = 1.0

        self.timer = QTimer()

        self.timer.timeout.connect(
            self.next_frame
        )

        # ====================================================
        # FASCICULATION EVENT
        # ====================================================

        self.start_frame = None

        self.end_frame = None

        self.event_number = 0

        # ====================================================
        # ANNOTATIONS
        # ====================================================

        self.annotations = []

        # ====================================================
        # CREATE UI
        # ====================================================

        self.create_ui()

    # ========================================================
    # CREATE USER INTERFACE
    # ========================================================

    def create_ui(self):

        central = QWidget()

        self.setCentralWidget(
            central
        )

        main_layout = QVBoxLayout()

        main_layout.setContentsMargins(
            8,
            8,
            8,
            8
        )

        main_layout.setSpacing(
            5
        )

        # ====================================================
        # VIDEO DISPLAY
        # ====================================================

        self.video_widget = VideoWidget()

        self.video_widget.roi_created.connect(
            self.on_roi_created
        )

        self.video_widget.roi_selected.connect(
            self.on_roi_selected
        )

        self.video_widget.roi_changed.connect(
            self.on_roi_changed
        )

        main_layout.addWidget(
            self.video_widget,
            10
        )

        # ====================================================
        # INFORMATION BAR
        # ====================================================

        info_layout = QHBoxLayout()

        self.frame_label = QLabel(
            "Frame: 0 / 0"
        )

        self.time_label = QLabel(
            "Current Time: 00:00:00.000"
        )

        self.start_label = QLabel(
            "START: ---"
        )

        self.end_label = QLabel(
            "END: ---"
        )

        self.fps_label = QLabel(
            "FPS: ---"
        )

        info_layout.addWidget(
            self.frame_label
        )

        info_layout.addWidget(
            self.time_label
        )

        info_layout.addWidget(
            self.start_label
        )

        info_layout.addWidget(
            self.end_label
        )

        info_layout.addWidget(
            self.fps_label
        )

        main_layout.addLayout(
            info_layout
        )

        # ====================================================
        # OPEN VIDEO
        # ====================================================

        open_button = QPushButton(
            "📂 Open MPEG / Video"
        )

        open_button.clicked.connect(
            self.open_video
        )

        main_layout.addWidget(
            open_button
        )

        # ====================================================
        # PLAYBACK BUTTONS
        # ====================================================

        playback_layout = QHBoxLayout()

        previous_button = QPushButton(
            "← Previous Frame"
        )

        previous_button.clicked.connect(
            self.previous_frame
        )

        self.play_button = QPushButton(
            "▶ Play"
        )

        self.play_button.clicked.connect(
            self.toggle_play
        )

        next_button = QPushButton(
            "Next Frame →"
        )

        next_button.clicked.connect(
            self.next_frame
        )

        playback_layout.addWidget(
            previous_button
        )

        playback_layout.addWidget(
            self.play_button
        )

        playback_layout.addWidget(
            next_button
        )

        playback_layout.addWidget(
            QLabel("Speed:")
        )

        self.speed_box = QComboBox()

        self.speed_box.addItems(
            [
                "0.10x",
                "0.25x",
                "0.50x",
                "1.00x",
                "1.50x",
                "2.00x"
            ]
        )

        self.speed_box.setCurrentText(
            "1.00x"
        )

        self.speed_box.currentTextChanged.connect(
            self.change_speed
        )

        playback_layout.addWidget(
            self.speed_box
        )

        main_layout.addLayout(
            playback_layout
        )

        # ====================================================
        # TIMELINE
        # ====================================================

        self.timeline = QSlider(
            Qt.Horizontal
        )

        self.timeline.setMinimum(
            0
        )

        self.timeline.setMaximum(
            0
        )

        self.timeline.valueChanged.connect(
            self.slider_changed
        )

        main_layout.addWidget(
            self.timeline
        )

        # ====================================================
        # EVENT CONTROLS
        # ====================================================

        event_layout = QHBoxLayout()

        start_button = QPushButton(
            "🔴 START [S]"
        )

        start_button.clicked.connect(
            self.mark_start
        )

        end_button = QPushButton(
            "🟢 END [E]"
        )

        end_button.clicked.connect(
            self.mark_end
        )

        new_event_button = QPushButton(
            "➕ New Event"
        )

        new_event_button.clicked.connect(
            self.new_event
        )

        event_layout.addWidget(
            start_button
        )

        event_layout.addWidget(
            end_button
        )

        event_layout.addWidget(
            new_event_button
        )

        main_layout.addLayout(
            event_layout
        )

        # ====================================================
        # ROI EDITOR
        # ====================================================

        roi_group = QGroupBox(
            "ROI Editor - Original Video Coordinates"
        )

        roi_layout = QHBoxLayout()

        # ----------------------------------------------------
        # ROI SELECTOR
        # ----------------------------------------------------

        roi_layout.addWidget(
            QLabel("ROI:")
        )

        self.roi_selector = QComboBox()

        self.roi_selector.currentIndexChanged.connect(
            self.roi_selection_changed
        )

        roi_layout.addWidget(
            self.roi_selector
        )

        # ----------------------------------------------------
        # XMIN
        # ----------------------------------------------------

        roi_layout.addWidget(
            QLabel("Xmin:")
        )

        self.xmin_spin = QSpinBox()

        self.xmin_spin.setRange(
            0,
            10000
        )

        self.xmin_spin.setValue(
            667
        )

        self.xmin_spin.valueChanged.connect(
            self.editor_value_changed
        )

        roi_layout.addWidget(
            self.xmin_spin
        )

        # ----------------------------------------------------
        # YMIN
        # ----------------------------------------------------

        roi_layout.addWidget(
            QLabel("Ymin:")
        )

        self.ymin_spin = QSpinBox()

        self.ymin_spin.setRange(
            0,
            10000
        )

        self.ymin_spin.setValue(
            54
        )

        self.ymin_spin.valueChanged.connect(
            self.editor_value_changed
        )

        roi_layout.addWidget(
            self.ymin_spin
        )

        # ----------------------------------------------------
        # XMAX
        # ----------------------------------------------------

        roi_layout.addWidget(
            QLabel("Xmax:")
        )

        self.xmax_spin = QSpinBox()

        self.xmax_spin.setRange(
            0,
            10000
        )

        self.xmax_spin.setValue(
            933
        )

        self.xmax_spin.valueChanged.connect(
            self.editor_value_changed
        )

        roi_layout.addWidget(
            self.xmax_spin
        )

        # ----------------------------------------------------
        # YMAX
        # ----------------------------------------------------

        roi_layout.addWidget(
            QLabel("Ymax:")
        )

        self.ymax_spin = QSpinBox()

        self.ymax_spin.setRange(
            0,
            10000
        )

        self.ymax_spin.setValue(
            341
        )

        self.ymax_spin.valueChanged.connect(
            self.editor_value_changed
        )

        roi_layout.addWidget(
            self.ymax_spin
        )

        # ----------------------------------------------------
        # WIDTH
        # ----------------------------------------------------

        roi_layout.addWidget(
            QLabel("Width:")
        )

        self.width_label = QLabel(
            "266"
        )

        roi_layout.addWidget(
            self.width_label
        )

        # ----------------------------------------------------
        # HEIGHT
        # ----------------------------------------------------

        roi_layout.addWidget(
            QLabel("Height:")
        )

        self.height_label = QLabel(
            "287"
        )

        roi_layout.addWidget(
            self.height_label
        )

        # ----------------------------------------------------
        # UPDATE
        # ----------------------------------------------------

        update_roi_button = QPushButton(
            "✏ Update ROI"
        )

        update_roi_button.clicked.connect(
            self.update_selected_roi
        )

        roi_layout.addWidget(
            update_roi_button
        )

        # ----------------------------------------------------
        # ADD
        # ----------------------------------------------------

        add_roi_button = QPushButton(
            "➕ Add ROI"
        )

        add_roi_button.clicked.connect(
            self.add_manual_roi
        )

        roi_layout.addWidget(
            add_roi_button
        )

        roi_group.setLayout(
            roi_layout
        )

        main_layout.addWidget(
            roi_group
        )

        # ====================================================
        # ROI BUTTONS
        # ====================================================

        roi_buttons_layout = QHBoxLayout()

        reset_roi_button = QPushButton(
            "🔄 Reset All ROIs [R]"
        )

        reset_roi_button.clicked.connect(
            self.reset_rois
        )

        delete_roi_button = QPushButton(
            "❌ Delete Selected ROI [Delete]"
        )

        delete_roi_button.clicked.connect(
            self.delete_selected_roi
        )

        save_button = QPushButton(
            "💾 Save ROI Video Clips"
        )

        save_button.clicked.connect(
            self.save_event
        )

        roi_buttons_layout.addWidget(
            reset_roi_button
        )

        roi_buttons_layout.addWidget(
            delete_roi_button
        )

        roi_buttons_layout.addWidget(
            save_button
        )

        main_layout.addLayout(
            roi_buttons_layout
        )

        central.setLayout(
            main_layout
        )

        self.update_roi_dimensions()

    # ========================================================
    # OPEN VIDEO
    # ========================================================

    def open_video(self):

        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Medical Video",
            "",
            (
                "Video Files "
                "(*.mpeg *.mpg *.mp4 *.avi *.mov *.mkv);;"
                "MPEG Files (*.mpeg *.mpg);;"
                "MP4 Files (*.mp4);;"
                "All Files (*.*)"
            )
        )

        if not path:
            return

        # Stop playback
        self.timer.stop()

        self.playing = False

        self.play_button.setText(
            "▶ Play"
        )

        # ----------------------------------------------------
        # Open video
        # ----------------------------------------------------

        cap = cv2.VideoCapture(
            path
        )

        if not cap.isOpened():

            QMessageBox.critical(
                self,
                "Video Error",
                (
                    "OpenCV could not open this video.\n\n"
                    "The MPEG codec may not be supported by "
                    "your OpenCV installation."
                )
            )

            return

        self.cap = cap

        self.video_path = path

        # ----------------------------------------------------
        # Video properties
        # ----------------------------------------------------

        self.fps = self.cap.get(
            cv2.CAP_PROP_FPS
        )

        if self.fps <= 0:
            self.fps = 30.0

        self.total_frames = int(
            self.cap.get(
                cv2.CAP_PROP_FRAME_COUNT
            )
        )

        self.frame_width = int(
            self.cap.get(
                cv2.CAP_PROP_FRAME_WIDTH
            )
        )

        self.frame_height = int(
            self.cap.get(
                cv2.CAP_PROP_FRAME_HEIGHT
            )
        )

        self.current_frame = 0

        self.start_frame = None

        self.end_frame = None

        self.event_number = 0

        self.annotations.clear()

        # ----------------------------------------------------
        # Reset ROIs
        # ----------------------------------------------------

        self.video_widget.reset_rois()

        self.roi_selector.clear()

        # ----------------------------------------------------
        # Coordinate ranges
        # ----------------------------------------------------

        self.xmin_spin.setRange(
            0,
            max(
                0,
                self.frame_width - 1
            )
        )

        self.xmax_spin.setRange(
            0,
            max(
                0,
                self.frame_width - 1
            )
        )

        self.ymin_spin.setRange(
            0,
            max(
                0,
                self.frame_height - 1
            )
        )

        self.ymax_spin.setRange(
            0,
            max(
                0,
                self.frame_height - 1
            )
        )

        # ----------------------------------------------------
        # Timeline
        # ----------------------------------------------------

        self.timeline.setMaximum(
            max(
                0,
                self.total_frames - 1
            )
        )

        self.fps_label.setText(
            f"FPS: {self.fps:.3f}"
        )

        # ----------------------------------------------------
        # Show first frame
        # ----------------------------------------------------

        self.show_frame(
            0
        )

        self.update_event_labels()

    # ========================================================
    # SHOW FRAME
    # ========================================================

    def show_frame(
        self,
        frame_number
    ):

        if self.cap is None:
            return

        if self.total_frames <= 0:
            return

        frame_number = max(
            0,
            min(
                int(frame_number),
                self.total_frames - 1
            )
        )

        self.cap.set(
            cv2.CAP_PROP_POS_FRAMES,
            frame_number
        )

        ret, frame = (
            self.cap.read()
        )

        if not ret:
            return

        self.current_frame = (
            frame_number
        )

        self.video_widget.set_video_frame(
            frame
        )

        # Update slider without triggering
        # another frame read
        self.timeline.blockSignals(
            True
        )

        self.timeline.setValue(
            frame_number
        )

        self.timeline.blockSignals(
            False
        )

        self.update_information()

    # ========================================================
    # UPDATE INFORMATION
    # ========================================================

    def update_information(self):

        current_time = (
            self.current_frame /
            self.fps
        )

        self.frame_label.setText(
            (
                f"Frame: "
                f"{self.current_frame} / "
                f"{max(0, self.total_frames - 1)}"
            )
        )

        self.time_label.setText(
            (
                "Current Time: "
                +
                self.format_time(
                    current_time
                )
            )
        )

    # ========================================================
    # FORMAT TIMESTAMP
    # ========================================================

    def format_time(
        self,
        seconds
    ):

        seconds = max(
            0,
            float(seconds)
        )

        hours = int(
            seconds // 3600
        )

        minutes = int(
            (seconds % 3600) // 60
        )

        sec = (
            seconds % 60
        )

        return (
            f"{hours:02d}:"
            f"{minutes:02d}:"
            f"{sec:06.3f}"
        )

    # ========================================================
    # PLAY / PAUSE
    # ========================================================

    def toggle_play(self):

        if self.cap is None:
            return

        if self.playing:

            self.playing = False

            self.timer.stop()

            self.play_button.setText(
                "▶ Play"
            )

        else:

            self.playing = True

            self.play_button.setText(
                "⏸ Pause"
            )

            self.timer.setInterval(
                self.timer_interval()
            )

            self.timer.start()

    # ========================================================
    # TIMER INTERVAL
    # ========================================================

    def timer_interval(self):

        if self.fps <= 0:
            return 33

        interval = (
            1000 /
            (
                self.fps *
                self.speed
            )
        )

        return max(
            1,
            int(interval)
        )

    # ========================================================
    # SPEED
    # ========================================================

    def change_speed(
        self,
        text
    ):

        self.speed = float(
            text.replace(
                "x",
                ""
            )
        )

        if self.playing:

            self.timer.setInterval(
                self.timer_interval()
            )

    # ========================================================
    # NEXT FRAME
    # ========================================================

    def next_frame(self):

        if self.cap is None:
            return

        if (
            self.current_frame
            <
            self.total_frames - 1
        ):

            self.show_frame(
                self.current_frame + 1
            )

        else:

            self.playing = False

            self.timer.stop()

            self.play_button.setText(
                "▶ Play"
            )

    # ========================================================
    # PREVIOUS FRAME
    # ========================================================

    def previous_frame(self):

        if self.cap is None:
            return

        self.show_frame(
            self.current_frame - 1
        )

    # ========================================================
    # SLIDER
    # ========================================================

    def slider_changed(
        self,
        value
    ):

        if self.cap is None:
            return

        self.show_frame(
            value
        )

    # ========================================================
    # MARK START
    # ========================================================

    def mark_start(self):

        if self.cap is None:
            return

        self.start_frame = (
            self.current_frame
        )

        self.update_event_labels()

    # ========================================================
    # MARK END
    # ========================================================

    def mark_end(self):

        if self.cap is None:
            return

        if self.start_frame is None:

            QMessageBox.warning(
                self,
                "START Missing",
                (
                    "Please press S at the beginning "
                    "of the fasciculation."
                )
            )

            return

        if (
            self.current_frame
            <
            self.start_frame
        ):

            QMessageBox.warning(
                self,
                "Invalid END",
                (
                    "END must be after START."
                )
            )

            return

        self.end_frame = (
            self.current_frame
        )

        self.update_event_labels()

    # ========================================================
    # UPDATE EVENT LABELS
    # ========================================================

    def update_event_labels(self):

        if self.start_frame is None:

            self.start_label.setText(
                "START: ---"
            )

        else:

            self.start_label.setText(
                (
                    "START: "
                    +
                    self.format_time(
                        self.start_frame /
                        self.fps
                    )
                )
            )

        if self.end_frame is None:

            self.end_label.setText(
                "END: ---"
            )

        else:

            self.end_label.setText(
                (
                    "END: "
                    +
                    self.format_time(
                        self.end_frame /
                        self.fps
                    )
                )
            )

    # ========================================================
    # ROI CREATED
    # ========================================================

    def on_roi_created(
        self,
        index
    ):

        self.refresh_roi_selector()

        self.roi_selector.setCurrentIndex(
            index
        )

        self.load_roi_into_editor(
            index
        )

    # ========================================================
    # ROI SELECTED
    # ========================================================

    def on_roi_selected(
        self,
        index
    ):

        self.refresh_roi_selector()

        self.roi_selector.setCurrentIndex(
            index
        )

        self.load_roi_into_editor(
            index
        )

    # ========================================================
    # ROI CHANGED LIVE
    # ========================================================

    def on_roi_changed(
        self,
        index
    ):

        if index < 0:
            return

        if index >= len(
            self.video_widget.rois
        ):
            return

        (
            xmin,
            ymin,
            xmax,
            ymax
        ) = (
            self.video_widget.rois[index]
        )

        # Update editor without recursively
        # modifying the ROI
        self.xmin_spin.blockSignals(
            True
        )

        self.ymin_spin.blockSignals(
            True
        )

        self.xmax_spin.blockSignals(
            True
        )

        self.ymax_spin.blockSignals(
            True
        )

        self.xmin_spin.setValue(
            xmin
        )

        self.ymin_spin.setValue(
            ymin
        )

        self.xmax_spin.setValue(
            xmax
        )

        self.ymax_spin.setValue(
            ymax
        )

        self.xmin_spin.blockSignals(
            False
        )

        self.ymin_spin.blockSignals(
            False
        )

        self.xmax_spin.blockSignals(
            False
        )

        self.ymax_spin.blockSignals(
            False
        )

        self.update_roi_dimensions()

    # ========================================================
    # REFRESH ROI SELECTOR
    # ========================================================

    def refresh_roi_selector(self):

        selected = (
            self.video_widget.selected_roi
        )

        self.roi_selector.blockSignals(
            True
        )

        self.roi_selector.clear()

        for index in range(
            len(
                self.video_widget.rois
            )
        ):

            self.roi_selector.addItem(
                f"ROI {index + 1}"
            )

        self.roi_selector.blockSignals(
            False
        )

        if (
            selected >= 0
            and
            selected <
            self.roi_selector.count()
        ):

            self.roi_selector.setCurrentIndex(
                selected
            )

            self.load_roi_into_editor(
                selected
            )

    # ========================================================
    # ROI SELECTOR CHANGED
    # ========================================================

    def roi_selection_changed(
        self,
        index
    ):

        if index < 0:
            return

        if index >= len(
            self.video_widget.rois
        ):
            return

        self.video_widget.selected_roi = (
            index
        )

        self.load_roi_into_editor(
            index
        )

        self.video_widget.update()

    # ========================================================
    # LOAD ROI INTO EDITOR
    # ========================================================

    def load_roi_into_editor(
        self,
        index
    ):

        if index < 0:
            return

        if index >= len(
            self.video_widget.rois
        ):
            return

        (
            xmin,
            ymin,
            xmax,
            ymax
        ) = (
            self.video_widget.rois[index]
        )

        self.xmin_spin.blockSignals(
            True
        )

        self.ymin_spin.blockSignals(
            True
        )

        self.xmax_spin.blockSignals(
            True
        )

        self.ymax_spin.blockSignals(
            True
        )

        self.xmin_spin.setValue(
            xmin
        )

        self.ymin_spin.setValue(
            ymin
        )

        self.xmax_spin.setValue(
            xmax
        )

        self.ymax_spin.setValue(
            ymax
        )

        self.xmin_spin.blockSignals(
            False
        )

        self.ymin_spin.blockSignals(
            False
        )

        self.xmax_spin.blockSignals(
            False
        )

        self.ymax_spin.blockSignals(
            False
        )

        self.update_roi_dimensions()

    # ========================================================
    # EDITOR VALUE CHANGED
    # ========================================================

    def editor_value_changed(
        self,
        value
    ):

        self.update_roi_dimensions()

    # ========================================================
    # UPDATE WIDTH / HEIGHT
    # ========================================================

    def update_roi_dimensions(self):

        xmin = self.xmin_spin.value()

        ymin = self.ymin_spin.value()

        xmax = self.xmax_spin.value()

        ymax = self.ymax_spin.value()

        width = max(
            0,
            xmax - xmin
        )

        height = max(
            0,
            ymax - ymin
        )

        self.width_label.setText(
            str(width)
        )

        self.height_label.setText(
            str(height)
        )

    # ========================================================
    # UPDATE SELECTED ROI
    # ========================================================

    def update_selected_roi(self):

        index = (
            self.video_widget.selected_roi
        )

        if index < 0:

            QMessageBox.warning(
                self,
                "No ROI",
                (
                    "Please draw or add an ROI first."
                )
            )

            return

        xmin = self.xmin_spin.value()

        ymin = self.ymin_spin.value()

        xmax = self.xmax_spin.value()

        ymax = self.ymax_spin.value()

        if xmax <= xmin:

            QMessageBox.warning(
                self,
                "Invalid ROI",
                "Xmax must be greater than Xmin."
            )

            return

        if ymax <= ymin:

            QMessageBox.warning(
                self,
                "Invalid ROI",
                "Ymax must be greater than Ymin."
            )

            return

        self.video_widget.set_roi(
            index,
            xmin,
            ymin,
            xmax,
            ymax
        )

    # ========================================================
    # ADD MANUAL ROI
    # ========================================================

    def add_manual_roi(self):

        if self.cap is None:

            QMessageBox.warning(
                self,
                "No Video",
                "Open a video first."
            )

            return

        xmin = self.xmin_spin.value()

        ymin = self.ymin_spin.value()

        xmax = self.xmax_spin.value()

        ymax = self.ymax_spin.value()

        if xmax <= xmin:

            QMessageBox.warning(
                self,
                "Invalid ROI",
                "Xmax must be greater than Xmin."
            )

            return

        if ymax <= ymin:

            QMessageBox.warning(
                self,
                "Invalid ROI",
                "Ymax must be greater than Ymin."
            )

            return

        index = (
            self.video_widget.add_manual_roi(
                xmin,
                ymin,
                xmax,
                ymax
            )
        )

        if index >= 0:

            self.refresh_roi_selector()

            self.roi_selector.setCurrentIndex(
                index
            )

            self.load_roi_into_editor(
                index
            )

    # ========================================================
    # RESET ROIs
    # ========================================================

    def reset_rois(self):

        self.video_widget.reset_rois()

        self.roi_selector.clear()

        self.update_roi_dimensions()

    # ========================================================
    # DELETE ROI
    # ========================================================

    def delete_selected_roi(self):

        self.video_widget.delete_selected_roi()

        self.refresh_roi_selector()

    # ========================================================
    # NEW EVENT
    # ========================================================

    def new_event(self):

        self.start_frame = None

        self.end_frame = None

        self.video_widget.reset_rois()

        self.roi_selector.clear()

        self.update_event_labels()

    # ========================================================
    # SAVE EVENT / ROI VIDEO
    # ========================================================

    def save_event(self):

        if self.cap is None:

            QMessageBox.warning(
                self,
                "No Video",
                "Please open a video first."
            )

            return

        if self.start_frame is None:

            QMessageBox.warning(
                self,
                "START Missing",
                "Press S to mark the fasciculation START."
            )

            return

        if self.end_frame is None:

            QMessageBox.warning(
                self,
                "END Missing",
                "Press E to mark the fasciculation END."
            )

            return

        if not self.video_widget.rois:

            QMessageBox.warning(
                self,
                "No ROI",
                "Please create at least one ROI."
            )

            return

        # ====================================================
        # SELECT OUTPUT DIRECTORY
        # ====================================================

        output_dir = QFileDialog.getExistingDirectory(
            self,
            "Select Dataset Output Folder"
        )

        if not output_dir:
            return

        roi_dir = os.path.join(
            output_dir,
            "ROI_Clips"
        )

        os.makedirs(
            roi_dir,
            exist_ok=True
        )

        # ====================================================
        # VIDEO NAME
        # ====================================================

        video_name = os.path.splitext(
            os.path.basename(
                self.video_path
            )
        )[0]

        self.event_number += 1

        event_id = (
            f"FAS_{self.event_number:04d}"
        )

        saved_count = 0

        # ====================================================
        # SAVE EACH ROI AS VIDEO
        # ====================================================

        for roi_index, roi in enumerate(
            self.video_widget.rois
        ):

            (
                xmin,
                ymin,
                xmax,
                ymax
            ) = roi

            roi_width = (
                xmax - xmin
            )

            roi_height = (
                ymax - ymin
            )

            if roi_width <= 0:
                continue

            if roi_height <= 0:
                continue

            # ------------------------------------------------
            # Output filename
            # ------------------------------------------------

            output_filename = (
                f"{video_name}_"
                f"{event_id}_"
                f"ROI_{roi_index + 1:02d}.mp4"
            )

            output_path = os.path.join(
                roi_dir,
                output_filename
            )

            # ------------------------------------------------
            # MP4 writer
            # ------------------------------------------------

            fourcc = cv2.VideoWriter_fourcc(
                *"mp4v"
            )

            writer = cv2.VideoWriter(
                output_path,
                fourcc,
                self.fps,
                (
                    roi_width,
                    roi_height
                )
            )

            if not writer.isOpened():

                QMessageBox.warning(
                    self,
                    "Video Writer Error",
                    (
                        "Could not create:\n"
                        +
                        output_path
                    )
                )

                continue

            # ------------------------------------------------
            # Go to START frame
            # ------------------------------------------------

            self.cap.set(
                cv2.CAP_PROP_POS_FRAMES,
                self.start_frame
            )

            frames_written = 0

            # ------------------------------------------------
            # Extract video
            # ------------------------------------------------

            for frame_number in range(
                self.start_frame,
                self.end_frame + 1
            ):

                ret, frame = (
                    self.cap.read()
                )

                if not ret:
                    break

                # --------------------------------------------
                # Crop ROI
                # --------------------------------------------

                crop = frame[
                    ymin:ymax,
                    xmin:xmax
                ]

                if crop.size == 0:
                    continue

                writer.write(
                    crop
                )

                frames_written += 1

            writer.release()

            # ------------------------------------------------
            # Verify
            # ------------------------------------------------

            if frames_written == 0:

                if os.path.exists(
                    output_path
                ):

                    os.remove(
                        output_path
                    )

                continue

            saved_count += 1

            # =================================================
            # TIMESTAMP
            # =================================================

            start_time_seconds = (
                self.start_frame /
                self.fps
            )

            end_time_seconds = (
                self.end_frame /
                self.fps
            )

            duration = (
                end_time_seconds -
                start_time_seconds
            )

            # =================================================
            # ANNOTATION
            # =================================================

            annotation = {

                "event":
                    event_id,

                "video":
                    os.path.basename(
                        self.video_path
                    ),

                "start_frame":
                    self.start_frame,

                "end_frame":
                    self.end_frame,

                "start_time":
                    self.format_time(
                        start_time_seconds
                    ),

                "end_time":
                    self.format_time(
                        end_time_seconds
                    ),

                "duration":
                    round(
                        duration,
                        3
                    ),

                "roi":
                    roi_index + 1,

                "xmin":
                    xmin,

                "ymin":
                    ymin,

                "xmax":
                    xmax,

                "ymax":
                    ymax,

                "roi_clip":
                    output_filename
            }

            self.annotations.append(
                annotation
            )

        # ====================================================
        # SAVE CSV
        # ====================================================

        csv_path = os.path.join(
            output_dir,
            "fasciculation_annotations.csv"
        )

        self.save_csv(
            csv_path
        )

        # ====================================================
        # RESTORE CURRENT FRAME
        # ====================================================

        self.show_frame(
            self.current_frame
        )

        # ====================================================
        # RESULT
        # ====================================================

        if saved_count > 0:

            QMessageBox.information(
                self,
                "Saved Successfully",
                (
                    f"Saved {saved_count} ROI video clip(s).\n\n"
                    f"Event: {event_id}\n\n"
                    f"ROI clips:\n{roi_dir}\n\n"
                    f"Annotations:\n{csv_path}"
                )
            )

    # ========================================================
    # SAVE CSV
    # ========================================================

    def save_csv(
        self,
        path
    ):

        if not self.annotations:
            return

        fields = [

            "event",
            "video",
            "start_frame",
            "end_frame",
            "start_time",
            "end_time",
            "duration",
            "roi",
            "xmin",
            "ymin",
            "xmax",
            "ymax",
            "roi_clip"
        ]

        with open(
            path,
            "w",
            newline="",
            encoding="utf-8"
        ) as file:

            writer = csv.DictWriter(
                file,
                fieldnames=fields
            )

            writer.writeheader()

            writer.writerows(
                self.annotations
            )

    # ========================================================
    # KEYBOARD CONTROLS
    # ========================================================

    def keyPressEvent(
        self,
        event
    ):

        key = event.key()

        # ----------------------------------------------------
        # SPACE = PLAY / PAUSE
        # ----------------------------------------------------

        if key == Qt.Key_Space:

            self.toggle_play()

        # ----------------------------------------------------
        # LEFT = PREVIOUS FRAME
        # ----------------------------------------------------

        elif key == Qt.Key_Left:

            self.previous_frame()

        # ----------------------------------------------------
        # RIGHT = NEXT FRAME
        # ----------------------------------------------------

        elif key == Qt.Key_Right:

            self.next_frame()

        # ----------------------------------------------------
        # S = START
        # ----------------------------------------------------

        elif key == Qt.Key_S:

            self.mark_start()

        # ----------------------------------------------------
        # E = END
        # ----------------------------------------------------

        elif key == Qt.Key_E:

            self.mark_end()

        # ----------------------------------------------------
        # R = RESET ROIs
        # ----------------------------------------------------

        elif key == Qt.Key_R:

            self.reset_rois()

        # ----------------------------------------------------
        # DELETE = DELETE ROI
        # ----------------------------------------------------

        elif key == Qt.Key_Delete:

            self.delete_selected_roi()

        else:

            super().keyPressEvent(
                event
            )

    # ========================================================
    # CLOSE APPLICATION
    # ========================================================

    def closeEvent(
        self,
        event
    ):

        self.timer.stop()

        if self.cap is not None:

            self.cap.release()

        event.accept()


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    app = QApplication(
        sys.argv
    )

    window = FasciculationAnnotator()

    window.show()

    sys.exit(
        app.exec()
    )