"""
video_widget.py
===============
Interactive video display widget with draw / move / resize ROI support.

Responsibilities:
  - Render video frames via QPainter
  - Draw all ROIs with colour coding (green = selected, red = others)
  - Show ROI label, pixel coordinates, and W/H on screen
  - Draw 8-handle resize controls on the selected ROI
  - Handle mouse: draw new ROI, click to select, drag to move, drag handle to resize
  - Emit signals: roi_created, roi_selected, roi_changed
  - Convert between original video coordinates and scaled display coordinates
"""

import cv2

from PySide6.QtWidgets import QWidget, QSizePolicy
from PySide6.QtCore import Qt, QRect, QPoint, Signal
from PySide6.QtGui import (
    QPainter, QPen, QColor, QFont, QImage, QPixmap,
)


class VideoWidget(QWidget):
    """
    Custom QWidget that renders a video frame and allows interactive
    drawing, selecting, moving, and resizing of rectangular ROIs.

    Signals:
        roi_created(int):  emitted when a new ROI is drawn; carries its index.
        roi_selected(int): emitted when an existing ROI is clicked; carries its index.
        roi_changed(int):  emitted whenever an ROI is moved or resized; carries its index.
    """

    roi_created  = Signal(int)
    roi_selected = Signal(int)
    roi_changed  = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setMinimumSize(500, 350)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMouseTracking(True)
        self.setStyleSheet("background-color: black;")

        # ── Video ─────────────────────────────────────────────────────
        self.frame        = None
        self.frame_width  = 0
        self.frame_height = 0

        # Displayed video rectangle (computed in paintEvent)
        self.display_x      = 0
        self.display_y      = 0
        self.display_width  = 0
        self.display_height = 0

        # ── ROIs ──────────────────────────────────────────────────────
        # Each ROI stored as (xmin, ymin, xmax, ymax) in original coords
        self.rois         = []
        self.selected_roi = -1

        # ── New ROI drawing state ─────────────────────────────────────
        self.drawing       = False
        self.start_point   = None
        self.current_point = None

        # ── Move / resize state ───────────────────────────────────────
        self.dragging                = False
        self.drag_mode               = None     # "MOVE" | "TL"|"T"|"TR"|"L"|"R"|"BL"|"B"|"BR"
        self.drag_start_original     = None
        self.original_roi_before_drag = None
        self.handle_size             = 10

    # ── Frame ─────────────────────────────────────────────────────────

    def set_video_frame(self, frame):
        """Set the current video frame (BGR numpy array) and repaint."""
        self.frame        = frame
        self.frame_height, self.frame_width = frame.shape[:2]
        self.update()

    # ── Coordinate conversion ─────────────────────────────────────────

    def _calculate_display_rect(self):
        """Compute the centred letterbox rectangle for the current widget size."""
        if self.frame is None:
            return

        widget_w = self.width()
        widget_h = self.height()
        if widget_w <= 0 or widget_h <= 0:
            return

        video_ratio  = self.frame_width  / self.frame_height
        widget_ratio = widget_w / widget_h

        if video_ratio > widget_ratio:
            self.display_width  = widget_w
            self.display_height = int(widget_w / video_ratio)
        else:
            self.display_height = widget_h
            self.display_width  = int(widget_h * video_ratio)

        self.display_x = (widget_w - self.display_width)  // 2
        self.display_y = (widget_h - self.display_height) // 2

    def original_to_display(self, x, y):
        """Convert original video pixel → QPoint in widget space."""
        if self.frame_width <= 0 or self.frame_height <= 0:
            return QPoint(0, 0)
        dx = int(self.display_x + x * self.display_width  / self.frame_width)
        dy = int(self.display_y + y * self.display_height / self.frame_height)
        return QPoint(dx, dy)

    def display_to_original(self, point):
        """
        Convert widget QPoint → (x, y) in original video coordinates.
        Returns None if the point is outside the displayed video rectangle.
        """
        if self.frame is None or self.display_width <= 0 or self.display_height <= 0:
            return None

        x = point.x() - self.display_x
        y = point.y() - self.display_y

        if x < 0 or y < 0 or x >= self.display_width or y >= self.display_height:
            return None

        ox = int(x * self.frame_width  / self.display_width)
        oy = int(y * self.frame_height / self.display_height)
        ox = max(0, min(ox, self.frame_width  - 1))
        oy = max(0, min(oy, self.frame_height - 1))
        return (ox, oy)

    def roi_to_display_rect(self, roi):
        """Return the QRect covering an ROI in widget coordinates."""
        xmin, ymin, xmax, ymax = roi
        p1 = self.original_to_display(xmin, ymin)
        p2 = self.original_to_display(xmax, ymax)
        return QRect(p1, p2).normalized()

    # ── Paint ─────────────────────────────────────────────────────────

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.black)

        if self.frame is None:
            painter.setPen(Qt.white)
            painter.drawText(self.rect(), Qt.AlignCenter, "Open a medical video")
            painter.end()
            return

        self._calculate_display_rect()

        # Draw video frame
        rgb            = cv2.cvtColor(self.frame, cv2.COLOR_BGR2RGB)
        h, w, channels = rgb.shape
        image          = QImage(rgb.data, w, h, channels * w, QImage.Format_RGB888)
        pixmap         = QPixmap.fromImage(image).scaled(
            self.display_width, self.display_height,
            Qt.KeepAspectRatio, Qt.SmoothTransformation,
        )
        painter.drawPixmap(self.display_x, self.display_y, pixmap)

        # Draw saved ROIs
        for index, roi in enumerate(self.rois):
            xmin, ymin, xmax, ymax = roi
            rect = self.roi_to_display_rect(roi)

            # Colour: green = selected, red = others
            color = QColor(0, 255, 0) if index == self.selected_roi else QColor(255, 0, 0)
            painter.setPen(QPen(color, 3))
            painter.drawRect(rect)

            # Label and coordinates in yellow
            painter.setFont(QFont("Arial", 11, QFont.Bold))
            painter.setPen(QPen(QColor(255, 255, 0)))
            painter.drawText(rect.topLeft()  + QPoint(5,  18), f"ROI {index + 1}")
            painter.drawText(rect.bottomLeft() + QPoint(0, 20), f"X:{xmin}-{xmax} Y:{ymin}-{ymax}")
            painter.drawText(rect.bottomLeft() + QPoint(0, 38), f"W:{xmax - xmin} H:{ymax - ymin}")

            if index == self.selected_roi:
                self._draw_resize_handles(painter, rect)

        # Draw new ROI while dragging
        if self.drawing and self.start_point and self.current_point:
            rect = QRect(self.start_point, self.current_point).normalized()
            painter.setPen(QPen(QColor(255, 255, 0), 2, Qt.DashLine))
            painter.drawRect(rect)

        painter.end()

    def _draw_resize_handles(self, painter, rect):
        """Draw 8 white square handles at corners and edge midpoints."""
        s = self.handle_size
        for point in self._handle_points(rect):
            painter.setPen(QPen(QColor(0, 255, 0), 2))
            painter.setBrush(QColor(255, 255, 255))
            painter.drawRect(point.x() - s // 2, point.y() - s // 2, s, s)

    def _handle_points(self, rect):
        """Return the 8 handle centre QPoints for a QRect."""
        cx, cy = rect.center().x(), rect.center().y()
        return [
            rect.topLeft(),
            QPoint(cx, rect.top()),
            rect.topRight(),
            QPoint(rect.left(), cy),
            QPoint(rect.right(), cy),
            rect.bottomLeft(),
            QPoint(cx, rect.bottom()),
            rect.bottomRight(),
        ]

    def _get_handle_at(self, point, rect):
        """Return the handle name ('TL','T','TR','L','R','BL','B','BR') or None."""
        tolerance = self.handle_size + 6
        named = zip(
            ["TL", "T", "TR", "L", "R", "BL", "B", "BR"],
            self._handle_points(rect),
        )
        for name, hp in named:
            if abs(point.x() - hp.x()) <= tolerance and abs(point.y() - hp.y()) <= tolerance:
                return name
        return None

    def _find_roi_at_point(self, point):
        """Return the index of the topmost ROI under point, or -1."""
        # Check selected first for priority
        if 0 <= self.selected_roi < len(self.rois):
            if self.roi_to_display_rect(self.rois[self.selected_roi]).contains(point):
                return self.selected_roi
        for index in reversed(range(len(self.rois))):
            if self.roi_to_display_rect(self.rois[index]).contains(point):
                return index
        return -1

    # ── Mouse events ──────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        point = event.position().toPoint()

        # Check resize handles on selected ROI
        if 0 <= self.selected_roi < len(self.rois):
            rect   = self.roi_to_display_rect(self.rois[self.selected_roi])
            handle = self._get_handle_at(point, rect)
            if handle:
                orig = self.display_to_original(point)
                if orig is None:
                    return
                self.dragging                = True
                self.drag_mode               = handle
                self.drag_start_original     = orig
                self.original_roi_before_drag = self.rois[self.selected_roi]
                return

        # Click existing ROI to select and move
        roi_index = self._find_roi_at_point(point)
        if roi_index >= 0:
            self.selected_roi = roi_index
            self.roi_selected.emit(roi_index)
            orig = self.display_to_original(point)
            if orig is None:
                return
            self.dragging                = True
            self.drag_mode               = "MOVE"
            self.drag_start_original     = orig
            self.original_roi_before_drag = self.rois[roi_index]
            self.update()
            return

        # Draw new ROI
        orig = self.display_to_original(point)
        if orig is None:
            return
        self.drawing       = True
        self.start_point   = point
        self.current_point = point
        self.update()

    def mouseMoveEvent(self, event):
        point = event.position().toPoint()

        if self.dragging:
            curr = self.display_to_original(point)
            if curr is None:
                return
            self._apply_drag(curr)
            self.roi_changed.emit(self.selected_roi)
            self.update()
            return

        if self.drawing:
            self.current_point = point
            self.update()
            return

        # Update cursor
        if 0 <= self.selected_roi < len(self.rois):
            rect   = self.roi_to_display_rect(self.rois[self.selected_roi])
            handle = self._get_handle_at(point, rect)
            cursor_map = {
                "TL": Qt.SizeFDiagCursor, "BR": Qt.SizeFDiagCursor,
                "TR": Qt.SizeBDiagCursor, "BL": Qt.SizeBDiagCursor,
                "T":  Qt.SizeVerCursor,   "B":  Qt.SizeVerCursor,
                "L":  Qt.SizeHorCursor,   "R":  Qt.SizeHorCursor,
            }
            if handle in cursor_map:
                self.setCursor(cursor_map[handle])
                return
            if rect.contains(point):
                self.setCursor(Qt.SizeAllCursor)
                return
        self.setCursor(Qt.ArrowCursor)

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.LeftButton:
            return

        if self.dragging:
            self.dragging                = False
            self.drag_mode               = None
            self.drag_start_original     = None
            self.original_roi_before_drag = None
            self.setCursor(Qt.ArrowCursor)
            self.update()
            return

        if not self.drawing:
            return

        self.drawing       = False
        self.current_point = event.position().toPoint()

        p1 = self.display_to_original(self.start_point)
        p2 = self.display_to_original(self.current_point)

        if p1 is None or p2 is None:
            self.update()
            return

        x1, y1 = p1
        x2, y2 = p2
        xmin, xmax = min(x1, x2), max(x1, x2)
        ymin, ymax = min(y1, y2), max(y1, y2)

        # Ignore very small boxes
        if xmax - xmin < 5 or ymax - ymin < 5:
            self.update()
            return

        self.rois.append((xmin, ymin, xmax, ymax))
        self.selected_roi = len(self.rois) - 1
        self.roi_created.emit(self.selected_roi)
        self.update()

    def _apply_drag(self, current_original):
        """Apply MOVE or resize transform to the selected ROI."""
        sx, sy             = self.drag_start_original
        cx, cy             = current_original
        ox1, oy1, ox2, oy2 = self.original_roi_before_drag
        dx, dy             = cx - sx, cy - sy

        xmin, ymin, xmax, ymax = ox1, oy1, ox2, oy2

        mode = self.drag_mode
        if mode == "MOVE":
            w, h = ox2 - ox1, oy2 - oy1
            xmin = max(0, min(ox1 + dx, self.frame_width  - w - 1))
            ymin = max(0, min(oy1 + dy, self.frame_height - h - 1))
            xmax, ymax = xmin + w, ymin + h
        elif mode == "TL": xmin = min(cx, ox2 - 5);  ymin = min(cy, oy2 - 5)
        elif mode == "T":  ymin = min(cy, oy2 - 5)
        elif mode == "TR": xmax = max(cx, ox1 + 5);  ymin = min(cy, oy2 - 5)
        elif mode == "L":  xmin = min(cx, ox2 - 5)
        elif mode == "R":  xmax = max(cx, ox1 + 5)
        elif mode == "BL": xmin = min(cx, ox2 - 5);  ymax = max(cy, oy1 + 5)
        elif mode == "B":  ymax = max(cy, oy1 + 5)
        elif mode == "BR": xmax = max(cx, ox1 + 5);  ymax = max(cy, oy1 + 5)

        # Clamp to frame
        xmin = max(0, min(int(xmin), self.frame_width  - 2))
        xmax = max(1, min(int(xmax), self.frame_width  - 1))
        ymin = max(0, min(int(ymin), self.frame_height - 2))
        ymax = max(1, min(int(ymax), self.frame_height - 1))

        self.rois[self.selected_roi] = (xmin, ymin, xmax, ymax)

    # ── ROI management ────────────────────────────────────────────────

    def set_roi(self, index, xmin, ymin, xmax, ymax):
        """Overwrite an existing ROI by index (called from the numeric editor)."""
        if not (0 <= index < len(self.rois)):
            return
        xmin, ymin, xmax, ymax = int(xmin), int(ymin), int(xmax), int(ymax)
        if xmax < xmin: xmin, xmax = xmax, xmin
        if ymax < ymin: ymin, ymax = ymax, ymin
        xmin = max(0, min(xmin, self.frame_width  - 2))
        xmax = max(1, min(xmax, self.frame_width  - 1))
        ymin = max(0, min(ymin, self.frame_height - 2))
        ymax = max(1, min(ymax, self.frame_height - 1))
        self.rois[index]  = (xmin, ymin, xmax, ymax)
        self.selected_roi = index
        self.roi_changed.emit(index)
        self.update()

    def add_manual_roi(self, xmin, ymin, xmax, ymax):
        """Add an ROI from the numeric editor. Returns the new index or -1."""
        if self.frame is None:
            return -1
        xmin, ymin, xmax, ymax = int(xmin), int(ymin), int(xmax), int(ymax)
        if xmax <= xmin or ymax <= ymin:
            return -1
        xmin = max(0, min(xmin, self.frame_width  - 2))
        xmax = max(1, min(xmax, self.frame_width  - 1))
        ymin = max(0, min(ymin, self.frame_height - 2))
        ymax = max(1, min(ymax, self.frame_height - 1))
        self.rois.append((xmin, ymin, xmax, ymax))
        self.selected_roi = len(self.rois) - 1
        self.roi_created.emit(self.selected_roi)
        self.update()
        return self.selected_roi

    def delete_selected_roi(self):
        """Remove the currently selected ROI."""
        if not (0 <= self.selected_roi < len(self.rois)):
            return
        self.rois.pop(self.selected_roi)
        self.selected_roi = min(self.selected_roi, len(self.rois) - 1) if self.rois else -1
        self.update()

    def reset_rois(self):
        """Clear all ROIs."""
        self.rois.clear()
        self.selected_roi = -1
        self.dragging     = False
        self.drawing      = False
        self.update()

    def resizeEvent(self, event):
        self.update()
        super().resizeEvent(event)
