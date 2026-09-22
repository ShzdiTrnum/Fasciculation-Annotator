"""
main_window.py
==============
Main application window for the Fasciculation Video Annotator.

Responsibilities:
  - Load and play ultrasound video files (MPEG / MP4 / AVI / MOV / MKV)
  - Frame-accurate playback with variable speed (0.1×–2.0×)
  - Mark fasciculation event START and END frames with keyboard shortcuts
  - Draw, select, move, resize, and delete ROIs interactively
  - Numeric ROI editor (Xmin / Ymin / Xmax / Ymax spin boxes)
  - Export each ROI as a cropped MP4 clip for the marked frame range
  - Append annotation records and save a cumulative CSV file
  - Keyboard shortcuts: Space=play/pause, ←/→=step, S=start, E=end, R=reset, Del=delete
"""

import csv
import os

import cv2

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QLabel, QPushButton, QFileDialog,
    QHBoxLayout, QVBoxLayout, QComboBox, QMessageBox,
    QSlider, QSizePolicy, QGroupBox, QSpinBox,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

from annotator.video_widget import VideoWidget


class FasciculationAnnotator(QMainWindow):
    """
    Top-level window that wires together video playback, ROI management,
    temporal event marking, and annotation export.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Fasciculation Video Annotator")
        self.resize(1500, 950)

        # ── Video state ───────────────────────────────────────────────
        self.cap          = None
        self.video_path   = None
        self.fps          = 30.0
        self.total_frames = 0
        self.frame_width  = 0
        self.frame_height = 0
        self.current_frame = 0

        # ── Playback ──────────────────────────────────────────────────
        self.playing = False
        self.speed   = 1.0
        self.timer   = QTimer()
        self.timer.timeout.connect(self.next_frame)

        # ── Fasciculation event ───────────────────────────────────────
        self.start_frame  = None
        self.end_frame    = None
        self.event_number = 0

        # ── Annotations (accumulated across events in this session) ───
        self.annotations = []

        self._build_ui()

    # ── UI construction ───────────────────────────────────────────────

    def _build_ui(self):
        central     = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(5)
        self.setCentralWidget(central)

        # Video display
        self.video_widget = VideoWidget()
        self.video_widget.roi_created.connect(self._on_roi_created)
        self.video_widget.roi_selected.connect(self._on_roi_selected)
        self.video_widget.roi_changed.connect(self._on_roi_changed)
        main_layout.addWidget(self.video_widget, 10)

        # Info bar
        info_layout    = QHBoxLayout()
        self.frame_label = QLabel("Frame: 0 / 0")
        self.time_label  = QLabel("Current Time: 00:00:00.000")
        self.start_label = QLabel("START: ---")
        self.end_label   = QLabel("END: ---")
        self.fps_label   = QLabel("FPS: ---")
        for w in (self.frame_label, self.time_label,
                  self.start_label, self.end_label, self.fps_label):
            info_layout.addWidget(w)
        main_layout.addLayout(info_layout)

        # Open button
        open_btn = QPushButton("📂 Open MPEG / Video")
        open_btn.clicked.connect(self.open_video)
        main_layout.addWidget(open_btn)

        # Playback row
        pb_layout = QHBoxLayout()
        prev_btn  = QPushButton("← Previous Frame")
        prev_btn.clicked.connect(self.previous_frame)
        self.play_button = QPushButton("▶ Play")
        self.play_button.clicked.connect(self.toggle_play)
        next_btn  = QPushButton("Next Frame →")
        next_btn.clicked.connect(self.next_frame)
        self.speed_box = QComboBox()
        self.speed_box.addItems(["0.10x", "0.25x", "0.50x", "1.00x", "1.50x", "2.00x"])
        self.speed_box.setCurrentText("1.00x")
        self.speed_box.currentTextChanged.connect(self._change_speed)
        for w in (prev_btn, self.play_button, next_btn, QLabel("Speed:"), self.speed_box):
            pb_layout.addWidget(w)
        main_layout.addLayout(pb_layout)

        # Timeline slider
        self.timeline = QSlider(Qt.Horizontal)
        self.timeline.setMinimum(0)
        self.timeline.setMaximum(0)
        self.timeline.valueChanged.connect(self._slider_changed)
        main_layout.addWidget(self.timeline)

        # Event controls
        ev_layout  = QHBoxLayout()
        start_btn  = QPushButton("🔴 START [S]")
        start_btn.clicked.connect(self.mark_start)
        end_btn    = QPushButton("🟢 END [E]")
        end_btn.clicked.connect(self.mark_end)
        new_ev_btn = QPushButton("➕ New Event")
        new_ev_btn.clicked.connect(self.new_event)
        for w in (start_btn, end_btn, new_ev_btn):
            ev_layout.addWidget(w)
        main_layout.addLayout(ev_layout)

        # ROI editor group
        roi_group  = QGroupBox("ROI Editor — Original Video Coordinates")
        roi_layout = QHBoxLayout()

        roi_layout.addWidget(QLabel("ROI:"))
        self.roi_selector = QComboBox()
        self.roi_selector.currentIndexChanged.connect(self._roi_selection_changed)
        roi_layout.addWidget(self.roi_selector)

        for label, attr, default in [
            ("Xmin:", "xmin_spin", 667),
            ("Ymin:", "ymin_spin",  54),
            ("Xmax:", "xmax_spin", 933),
            ("Ymax:", "ymax_spin", 341),
        ]:
            roi_layout.addWidget(QLabel(label))
            spin = QSpinBox()
            spin.setRange(0, 10000)
            spin.setValue(default)
            spin.valueChanged.connect(self._editor_value_changed)
            setattr(self, attr, spin)
            roi_layout.addWidget(spin)

        roi_layout.addWidget(QLabel("Width:"))
        self.width_label = QLabel("266")
        roi_layout.addWidget(self.width_label)

        roi_layout.addWidget(QLabel("Height:"))
        self.height_label = QLabel("287")
        roi_layout.addWidget(self.height_label)

        update_roi_btn = QPushButton("✏ Update ROI")
        update_roi_btn.clicked.connect(self._update_selected_roi)
        roi_layout.addWidget(update_roi_btn)

        add_roi_btn = QPushButton("➕ Add ROI")
        add_roi_btn.clicked.connect(self._add_manual_roi)
        roi_layout.addWidget(add_roi_btn)

        roi_group.setLayout(roi_layout)
        main_layout.addWidget(roi_group)

        # ROI action buttons
        roi_btns = QHBoxLayout()
        reset_btn  = QPushButton("🔄 Reset All ROIs [R]")
        reset_btn.clicked.connect(self._reset_rois)
        delete_btn = QPushButton("❌ Delete Selected ROI [Delete]")
        delete_btn.clicked.connect(self._delete_selected_roi)
        save_btn   = QPushButton("💾 Save ROI Video Clips")
        save_btn.clicked.connect(self.save_event)
        for w in (reset_btn, delete_btn, save_btn):
            roi_btns.addWidget(w)
        main_layout.addLayout(roi_btns)

        central.setLayout(main_layout)
        self._update_roi_dimensions()

    # ── Video loading ─────────────────────────────────────────────────

    def open_video(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Medical Video", "",
            "Video Files (*.mpeg *.mpg *.mp4 *.avi *.mov *.mkv);;"
            "MPEG Files (*.mpeg *.mpg);;MP4 Files (*.mp4);;All Files (*.*)",
        )
        if not path:
            return

        self.timer.stop()
        self.playing = False
        self.play_button.setText("▶ Play")

        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            QMessageBox.critical(self, "Video Error",
                                 "OpenCV could not open this video.\n\n"
                                 "The codec may not be supported by your OpenCV build.")
            return

        self.cap          = cap
        self.video_path   = path
        self.fps          = self.cap.get(cv2.CAP_PROP_FPS) or 30.0
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.frame_width  = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.current_frame = 0
        self.start_frame   = None
        self.end_frame     = None
        self.event_number  = 0
        self.annotations.clear()

        self.video_widget.reset_rois()
        self.roi_selector.clear()

        for spin, limit in [
            (self.xmin_spin, self.frame_width  - 1),
            (self.xmax_spin, self.frame_width  - 1),
            (self.ymin_spin, self.frame_height - 1),
            (self.ymax_spin, self.frame_height - 1),
        ]:
            spin.setRange(0, max(0, limit))

        self.timeline.setMaximum(max(0, self.total_frames - 1))
        self.fps_label.setText(f"FPS: {self.fps:.3f}")
        self.show_frame(0)
        self._update_event_labels()

    # ── Playback ──────────────────────────────────────────────────────

    def show_frame(self, frame_number):
        if self.cap is None or self.total_frames <= 0:
            return
        frame_number = max(0, min(int(frame_number), self.total_frames - 1))
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = self.cap.read()
        if not ret:
            return
        self.current_frame = frame_number
        self.video_widget.set_video_frame(frame)
        self.timeline.blockSignals(True)
        self.timeline.setValue(frame_number)
        self.timeline.blockSignals(False)
        self._update_info()

    def _update_info(self):
        t = self.current_frame / self.fps
        self.frame_label.setText(f"Frame: {self.current_frame} / {max(0, self.total_frames - 1)}")
        self.time_label.setText(f"Current Time: {self._fmt_time(t)}")

    @staticmethod
    def _fmt_time(seconds):
        seconds = max(0.0, float(seconds))
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = seconds % 60
        return f"{h:02d}:{m:02d}:{s:06.3f}"

    def toggle_play(self):
        if self.cap is None:
            return
        if self.playing:
            self.playing = False
            self.timer.stop()
            self.play_button.setText("▶ Play")
        else:
            self.playing = True
            self.play_button.setText("⏸ Pause")
            self.timer.setInterval(self._timer_interval())
            self.timer.start()

    def _timer_interval(self):
        return max(1, int(1000 / (self.fps * self.speed))) if self.fps > 0 else 33

    def _change_speed(self, text):
        self.speed = float(text.replace("x", ""))
        if self.playing:
            self.timer.setInterval(self._timer_interval())

    def next_frame(self):
        if self.cap is None:
            return
        if self.current_frame < self.total_frames - 1:
            self.show_frame(self.current_frame + 1)
        else:
            self.playing = False
            self.timer.stop()
            self.play_button.setText("▶ Play")

    def previous_frame(self):
        if self.cap is None:
            return
        self.show_frame(self.current_frame - 1)

    def _slider_changed(self, value):
        if self.cap is None:
            return
        self.show_frame(value)

    # ── Event marking ─────────────────────────────────────────────────

    def mark_start(self):
        if self.cap is None:
            return
        self.start_frame = self.current_frame
        self._update_event_labels()

    def mark_end(self):
        if self.cap is None:
            return
        if self.start_frame is None:
            QMessageBox.warning(self, "START Missing",
                                "Please press S at the start of the fasciculation.")
            return
        if self.current_frame < self.start_frame:
            QMessageBox.warning(self, "Invalid END", "END must be after START.")
            return
        self.end_frame = self.current_frame
        self._update_event_labels()

    def _update_event_labels(self):
        self.start_label.setText(
            "START: " + self._fmt_time(self.start_frame / self.fps)
            if self.start_frame is not None else "START: ---"
        )
        self.end_label.setText(
            "END: " + self._fmt_time(self.end_frame / self.fps)
            if self.end_frame is not None else "END: ---"
        )

    def new_event(self):
        self.start_frame = None
        self.end_frame   = None
        self.video_widget.reset_rois()
        self.roi_selector.clear()
        self._update_event_labels()

    # ── ROI signals ───────────────────────────────────────────────────

    def _on_roi_created(self, index):
        self._refresh_roi_selector()
        self.roi_selector.setCurrentIndex(index)
        self._load_roi_into_editor(index)

    def _on_roi_selected(self, index):
        self._refresh_roi_selector()
        self.roi_selector.setCurrentIndex(index)
        self._load_roi_into_editor(index)

    def _on_roi_changed(self, index):
        if not (0 <= index < len(self.video_widget.rois)):
            return
        xmin, ymin, xmax, ymax = self.video_widget.rois[index]
        for spin, val in [
            (self.xmin_spin, xmin), (self.ymin_spin, ymin),
            (self.xmax_spin, xmax), (self.ymax_spin, ymax),
        ]:
            spin.blockSignals(True)
            spin.setValue(val)
            spin.blockSignals(False)
        self._update_roi_dimensions()

    def _refresh_roi_selector(self):
        selected = self.video_widget.selected_roi
        self.roi_selector.blockSignals(True)
        self.roi_selector.clear()
        for i in range(len(self.video_widget.rois)):
            self.roi_selector.addItem(f"ROI {i + 1}")
        self.roi_selector.blockSignals(False)
        if 0 <= selected < self.roi_selector.count():
            self.roi_selector.setCurrentIndex(selected)
            self._load_roi_into_editor(selected)

    def _roi_selection_changed(self, index):
        if not (0 <= index < len(self.video_widget.rois)):
            return
        self.video_widget.selected_roi = index
        self._load_roi_into_editor(index)
        self.video_widget.update()

    def _load_roi_into_editor(self, index):
        if not (0 <= index < len(self.video_widget.rois)):
            return
        xmin, ymin, xmax, ymax = self.video_widget.rois[index]
        for spin, val in [
            (self.xmin_spin, xmin), (self.ymin_spin, ymin),
            (self.xmax_spin, xmax), (self.ymax_spin, ymax),
        ]:
            spin.blockSignals(True)
            spin.setValue(val)
            spin.blockSignals(False)
        self._update_roi_dimensions()

    def _editor_value_changed(self, _):
        self._update_roi_dimensions()

    def _update_roi_dimensions(self):
        w = max(0, self.xmax_spin.value() - self.xmin_spin.value())
        h = max(0, self.ymax_spin.value() - self.ymin_spin.value())
        self.width_label.setText(str(w))
        self.height_label.setText(str(h))

    def _update_selected_roi(self):
        index = self.video_widget.selected_roi
        if index < 0:
            QMessageBox.warning(self, "No ROI", "Please draw or add an ROI first.")
            return
        xmin, ymin = self.xmin_spin.value(), self.ymin_spin.value()
        xmax, ymax = self.xmax_spin.value(), self.ymax_spin.value()
        if xmax <= xmin:
            QMessageBox.warning(self, "Invalid ROI", "Xmax must be greater than Xmin.")
            return
        if ymax <= ymin:
            QMessageBox.warning(self, "Invalid ROI", "Ymax must be greater than Ymin.")
            return
        self.video_widget.set_roi(index, xmin, ymin, xmax, ymax)

    def _add_manual_roi(self):
        if self.cap is None:
            QMessageBox.warning(self, "No Video", "Open a video first.")
            return
        xmin, ymin = self.xmin_spin.value(), self.ymin_spin.value()
        xmax, ymax = self.xmax_spin.value(), self.ymax_spin.value()
        if xmax <= xmin:
            QMessageBox.warning(self, "Invalid ROI", "Xmax must be greater than Xmin.")
            return
        if ymax <= ymin:
            QMessageBox.warning(self, "Invalid ROI", "Ymax must be greater than Ymin.")
            return
        index = self.video_widget.add_manual_roi(xmin, ymin, xmax, ymax)
        if index >= 0:
            self._refresh_roi_selector()
            self.roi_selector.setCurrentIndex(index)
            self._load_roi_into_editor(index)

    def _reset_rois(self):
        self.video_widget.reset_rois()
        self.roi_selector.clear()
        self._update_roi_dimensions()

    def _delete_selected_roi(self):
        self.video_widget.delete_selected_roi()
        self._refresh_roi_selector()

    # ── Save event / ROI clips ────────────────────────────────────────

    def save_event(self):
        if self.cap is None:
            QMessageBox.warning(self, "No Video", "Please open a video first."); return
        if self.start_frame is None:
            QMessageBox.warning(self, "START Missing", "Press S to mark the fasciculation START."); return
        if self.end_frame is None:
            QMessageBox.warning(self, "END Missing", "Press E to mark the fasciculation END."); return
        if not self.video_widget.rois:
            QMessageBox.warning(self, "No ROI", "Please create at least one ROI."); return

        output_dir = QFileDialog.getExistingDirectory(self, "Select Dataset Output Folder")
        if not output_dir:
            return

        roi_dir = os.path.join(output_dir, "ROI_Clips")
        os.makedirs(roi_dir, exist_ok=True)

        video_name    = os.path.splitext(os.path.basename(self.video_path))[0]
        self.event_number += 1
        event_id      = f"FAS_{self.event_number:04d}"
        saved_count   = 0

        for roi_index, roi in enumerate(self.video_widget.rois):
            xmin, ymin, xmax, ymax = roi
            roi_w, roi_h = xmax - xmin, ymax - ymin
            if roi_w <= 0 or roi_h <= 0:
                continue

            out_filename = f"{video_name}_{event_id}_ROI_{roi_index + 1:02d}.mp4"
            out_path     = os.path.join(roi_dir, out_filename)

            writer = cv2.VideoWriter(
                out_path,
                cv2.VideoWriter_fourcc(*"mp4v"),
                self.fps,
                (roi_w, roi_h),
            )
            if not writer.isOpened():
                QMessageBox.warning(self, "Video Writer Error", f"Could not create:\n{out_path}")
                continue

            self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.start_frame)
            frames_written = 0
            for _ in range(self.start_frame, self.end_frame + 1):
                ret, frame = self.cap.read()
                if not ret:
                    break
                crop = frame[ymin:ymax, xmin:xmax]
                if crop.size == 0:
                    continue
                writer.write(crop)
                frames_written += 1
            writer.release()

            if frames_written == 0:
                if os.path.exists(out_path):
                    os.remove(out_path)
                continue

            saved_count += 1
            start_t = self.start_frame / self.fps
            end_t   = self.end_frame   / self.fps

            self.annotations.append({
                "event":        event_id,
                "video":        os.path.basename(self.video_path),
                "start_frame":  self.start_frame,
                "end_frame":    self.end_frame,
                "start_time":   self._fmt_time(start_t),
                "end_time":     self._fmt_time(end_t),
                "duration":     round(end_t - start_t, 3),
                "roi":          roi_index + 1,
                "xmin":         xmin,
                "ymin":         ymin,
                "xmax":         xmax,
                "ymax":         ymax,
                "roi_clip":     out_filename,
            })

        csv_path = os.path.join(output_dir, "fasciculation_annotations.csv")
        self._save_csv(csv_path)
        self.show_frame(self.current_frame)

        if saved_count > 0:
            QMessageBox.information(
                self, "Saved Successfully",
                f"Saved {saved_count} ROI clip(s).\n\nEvent: {event_id}\n\n"
                f"Clips:\n{roi_dir}\n\nAnnotations:\n{csv_path}",
            )

    def _save_csv(self, path):
        if not self.annotations:
            return
        fields = ["event", "video", "start_frame", "end_frame",
                  "start_time", "end_time", "duration",
                  "roi", "xmin", "ymin", "xmax", "ymax", "roi_clip"]
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(self.annotations)

    # ── Keyboard shortcuts ────────────────────────────────────────────

    def keyPressEvent(self, event):
        key = event.key()
        if   key == Qt.Key_Space:  self.toggle_play()
        elif key == Qt.Key_Left:   self.previous_frame()
        elif key == Qt.Key_Right:  self.next_frame()
        elif key == Qt.Key_S:      self.mark_start()
        elif key == Qt.Key_E:      self.mark_end()
        elif key == Qt.Key_R:      self._reset_rois()
        elif key == Qt.Key_Delete: self._delete_selected_roi()
        else:                      super().keyPressEvent(event)

    def closeEvent(self, event):
        self.timer.stop()
        if self.cap is not None:
            self.cap.release()
        event.accept()
