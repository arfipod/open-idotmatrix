"""PySide6 desktop app for open-idotmatrix."""

from __future__ import annotations

import asyncio
import json
import sys
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Qt, QThread, Signal, Slot
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .device import OpenIDotMatrix
from .exceptions import OpenIDotMatrixError, ProtocolError
from .protocol import parse_packet
from .simulator import (
    MatrixSimulator,
    save_gif_preview_frames,
    save_text_animation,
    simulate_text_frame,
)
from .types import (
    GifTotalLengthMode,
    TextBackgroundMode,
    TextColorMode,
    TextMode,
    YearByteMode,
)

AsyncJob = Callable[[], Awaitable[Any]]


def _compact_result(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _compact_result(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_compact_result(item) for item in value]
    if isinstance(value, str) and len(value) > 320:
        return f"{value[:320]} ... <{len(value) - 320} chars truncated>"
    return value


def _json(value: Any) -> str:
    return json.dumps(_compact_result(value), indent=2, sort_keys=True, default=str)


class AsyncWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)
    done = Signal()

    def __init__(self, job: AsyncJob) -> None:
        super().__init__()
        self._job = job

    @Slot()
    def run(self) -> None:
        try:
            result = asyncio.run(self._job())
        except Exception as exc:  # pragma: no cover - exercised by GUI usage
            self.failed.emit(f"{type(exc).__name__}: {exc}")
        else:
            self.finished.emit(result)
        finally:
            self.done.emit()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("open-idotmatrix")
        self.resize(1120, 820)
        self._threads: list[QThread] = []
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumSize(260, 260)
        self.preview_label.setStyleSheet("background: #111; color: #ddd;")
        self._build_ui()

    def _build_ui(self) -> None:
        root = QWidget()
        root_layout = QVBoxLayout(root)
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMinimumHeight(180)
        root_layout.addWidget(self._connection_panel())

        tabs = QTabWidget()
        tabs.addTab(self._basic_tab(), "Device")
        tabs.addTab(self._pixels_tab(), "Pixels")
        tabs.addTab(self._text_gif_tab(), "Text & GIF")
        tabs.addTab(self._modes_tab(), "Modes")
        tabs.addTab(self._tools_tab(), "Tools")
        tabs.addTab(self._danger_tab(), "Danger")
        root_layout.addWidget(tabs, stretch=1)

        root_layout.addWidget(self.log)
        self.setCentralWidget(root)

    def _connection_panel(self) -> QWidget:
        panel = QWidget()
        layout = QGridLayout(panel)
        self.address_edit = QLineEdit()
        self.address_edit.setPlaceholderText("D3:55:F4:AB:0B:0A")
        self.device_combo = QComboBox()
        self.device_combo.currentIndexChanged.connect(self._select_scanned_device)
        self.scan_timeout = self._float_spin(0.5, 30.0, 5.0, 0.5)

        scan = QPushButton("Scan")
        scan.clicked.connect(self.scan_devices)
        clear = QPushButton("Clear Log")
        clear.clicked.connect(self.log.clear)

        layout.addWidget(QLabel("Address"), 0, 0)
        layout.addWidget(self.address_edit, 0, 1)
        layout.addWidget(QLabel("Scanned"), 0, 2)
        layout.addWidget(self.device_combo, 0, 3)
        layout.addWidget(QLabel("Timeout"), 0, 4)
        layout.addWidget(self.scan_timeout, 0, 5)
        layout.addWidget(scan, 0, 6)
        layout.addWidget(clear, 0, 7)
        layout.setColumnStretch(1, 2)
        layout.setColumnStretch(3, 2)
        return panel

    def _basic_tab(self) -> QWidget:
        tab = QWidget()
        layout = QGridLayout(tab)

        on = QPushButton("On")
        on.clicked.connect(lambda: self._run_device("on", lambda matrix: matrix.on()))
        off = QPushButton("Off")
        off.clicked.connect(lambda: self._run_device("off", lambda matrix: matrix.off()))
        freeze = QPushButton("Freeze")
        freeze.clicked.connect(lambda: self._run_device("freeze", lambda matrix: matrix.freeze()))
        reset = QPushButton("Reset")
        reset.clicked.connect(lambda: self._run_device("reset", lambda matrix: matrix.reset()))

        self.brightness = self._spin(5, 100, 80)
        brightness = QPushButton("Set Brightness")
        brightness.clicked.connect(
            lambda: self._run_device(
                "brightness",
                lambda matrix: matrix.set_brightness(self.brightness.value()),
            )
        )

        flip_on = QPushButton("Flip On")
        flip_on.clicked.connect(lambda: self._run_device("flip on", lambda matrix: matrix.flip(True)))
        flip_off = QPushButton("Flip Off")
        flip_off.clicked.connect(lambda: self._run_device("flip off", lambda matrix: matrix.flip(False)))

        self.year_mode = QComboBox()
        for mode in YearByteMode:
            self.year_mode.addItem(mode.value, mode)
        sync = QPushButton("Sync Time")
        sync.clicked.connect(
            lambda: self._run_device(
                "sync time",
                lambda matrix: matrix.sync_time(year_mode=self.year_mode.currentData()),
            )
        )

        layout.addWidget(on, 0, 0)
        layout.addWidget(off, 0, 1)
        layout.addWidget(freeze, 0, 2)
        layout.addWidget(reset, 0, 3)
        layout.addWidget(QLabel("Brightness"), 1, 0)
        layout.addWidget(self.brightness, 1, 1)
        layout.addWidget(brightness, 1, 2)
        layout.addWidget(flip_on, 2, 0)
        layout.addWidget(flip_off, 2, 1)
        layout.addWidget(QLabel("Year Mode"), 3, 0)
        layout.addWidget(self.year_mode, 3, 1)
        layout.addWidget(sync, 3, 2)
        layout.setColumnStretch(4, 1)
        return tab

    def _pixels_tab(self) -> QWidget:
        tab = QWidget()
        layout = QGridLayout(tab)

        fill_rgb, self.fill_rgb = self._rgb_editor((255, 0, 0))
        fill = QPushButton("Fill")
        fill.clicked.connect(
            lambda: self._run_device("fill", lambda matrix: matrix.fill(self._rgb(self.fill_rgb)))
        )

        self.pixel_x = self._spin(0, 31, 0)
        self.pixel_y = self._spin(0, 31, 0)
        pixel_rgb, self.pixel_rgb = self._rgb_editor((255, 255, 255))
        pixel = QPushButton("Set Pixel")
        pixel.clicked.connect(
            lambda: self._run_device(
                "pixel",
                lambda matrix: matrix.pixel(
                    self.pixel_x.value(),
                    self.pixel_y.value(),
                    self._rgb(self.pixel_rgb),
                ),
            )
        )

        spiral_rgb, self.spiral_rgb = self._rgb_editor((255, 0, 0))
        self.spiral_delay = self._float_spin(0.0, 5.0, 0.0, 0.01, decimals=3)
        spiral = QPushButton("Spiral")
        spiral.clicked.connect(
            lambda: self._run_device(
                "spiral",
                lambda matrix: matrix.spiral(
                    self._rgb(self.spiral_rgb),
                    delay=self.spiral_delay.value(),
                ),
            )
        )

        layout.addWidget(QLabel("Fill RGB"), 0, 0)
        layout.addWidget(fill_rgb, 0, 1)
        layout.addWidget(fill, 0, 2)
        layout.addWidget(QLabel("Pixel X"), 1, 0)
        layout.addWidget(self.pixel_x, 1, 1)
        layout.addWidget(QLabel("Pixel Y"), 1, 2)
        layout.addWidget(self.pixel_y, 1, 3)
        layout.addWidget(QLabel("Pixel RGB"), 2, 0)
        layout.addWidget(pixel_rgb, 2, 1)
        layout.addWidget(pixel, 2, 2)
        layout.addWidget(QLabel("Spiral RGB"), 3, 0)
        layout.addWidget(spiral_rgb, 3, 1)
        layout.addWidget(QLabel("Delay"), 3, 2)
        layout.addWidget(self.spiral_delay, 3, 3)
        layout.addWidget(spiral, 3, 4)
        layout.setColumnStretch(5, 1)
        return tab

    def _text_gif_tab(self) -> QWidget:
        tab = QWidget()
        outer = QHBoxLayout(tab)
        left = QWidget()
        right = QWidget()
        outer.addWidget(left, stretch=1)
        outer.addWidget(right, stretch=1)
        text_layout = QGridLayout(left)
        gif_layout = QGridLayout(right)

        self.text_value = QLineEdit("Hello")
        self.text_mode = self._enum_combo(TextMode)
        self.text_speed = self._spin(0, 255, 95)
        self.text_color_mode = self._enum_combo(TextColorMode)
        self.text_background_mode = self._enum_combo(TextBackgroundMode)
        text_rgb, self.text_rgb = self._rgb_editor((255, 255, 255))
        bg_rgb, self.text_bg_rgb = self._rgb_editor((0, 0, 0))
        self.font_path = QLineEdit()
        font_browse = QPushButton("Browse")
        font_browse.clicked.connect(lambda: self._browse_open(self.font_path, "Select Font"))
        self.font_size = self._spin(1, 96, 24)
        send_text = QPushButton("Send Text")
        send_text.clicked.connect(self.send_text)

        text_layout.addWidget(QLabel("Text"), 0, 0)
        text_layout.addWidget(self.text_value, 0, 1, 1, 2)
        text_layout.addWidget(QLabel("Mode"), 1, 0)
        text_layout.addWidget(self.text_mode, 1, 1)
        text_layout.addWidget(QLabel("Speed"), 1, 2)
        text_layout.addWidget(self.text_speed, 1, 3)
        text_layout.addWidget(QLabel("Color Mode"), 2, 0)
        text_layout.addWidget(self.text_color_mode, 2, 1)
        text_layout.addWidget(QLabel("RGB"), 2, 2)
        text_layout.addWidget(text_rgb, 2, 3)
        text_layout.addWidget(QLabel("Background"), 3, 0)
        text_layout.addWidget(self.text_background_mode, 3, 1)
        text_layout.addWidget(QLabel("BG RGB"), 3, 2)
        text_layout.addWidget(bg_rgb, 3, 3)
        text_layout.addWidget(QLabel("Font"), 4, 0)
        text_layout.addWidget(self.font_path, 4, 1, 1, 2)
        text_layout.addWidget(font_browse, 4, 3)
        text_layout.addWidget(QLabel("Font Size"), 5, 0)
        text_layout.addWidget(self.font_size, 5, 1)
        text_layout.addWidget(send_text, 5, 2)

        self.gif_path = QLineEdit()
        gif_browse = QPushButton("Browse")
        gif_browse.clicked.connect(lambda: self._browse_open(self.gif_path, "Select GIF or Image"))
        self.gif_raw = QCheckBox("Raw")
        self.gif_no_ack = QCheckBox("No ACK")
        self.gif_no_response = QCheckBox("No Response")
        self.gif_total_length = QComboBox()
        for mode in GifTotalLengthMode:
            self.gif_total_length.addItem(mode.value, mode)
        self.gif_ack_timeout = self._float_spin(0.1, 120.0, 10.0, 0.5)
        self.gif_sleep = self._float_spin(0.0, 10.0, 1.0, 0.1)
        upload_gif = QPushButton("Upload GIF")
        upload_gif.clicked.connect(self.upload_gif)

        self.gif_preview_out = QLineEdit("out/gif_preview")
        preview_browse = QPushButton("Browse")
        preview_browse.clicked.connect(lambda: self._browse_dir(self.gif_preview_out, "Select Output Directory"))
        self.gif_preview_max = self._spin(1, 999, 16)
        make_preview = QPushButton("Export Preview Frames")
        make_preview.clicked.connect(self.export_gif_preview)

        gif_layout.addWidget(QLabel("Path"), 0, 0)
        gif_layout.addWidget(self.gif_path, 0, 1, 1, 2)
        gif_layout.addWidget(gif_browse, 0, 3)
        gif_layout.addWidget(self.gif_raw, 1, 0)
        gif_layout.addWidget(self.gif_no_ack, 1, 1)
        gif_layout.addWidget(self.gif_no_response, 1, 2)
        gif_layout.addWidget(QLabel("Length Mode"), 2, 0)
        gif_layout.addWidget(self.gif_total_length, 2, 1)
        gif_layout.addWidget(QLabel("ACK Timeout"), 3, 0)
        gif_layout.addWidget(self.gif_ack_timeout, 3, 1)
        gif_layout.addWidget(QLabel("Sleep"), 3, 2)
        gif_layout.addWidget(self.gif_sleep, 3, 3)
        gif_layout.addWidget(upload_gif, 4, 0)
        gif_layout.addWidget(QLabel("Preview Out"), 5, 0)
        gif_layout.addWidget(self.gif_preview_out, 5, 1, 1, 2)
        gif_layout.addWidget(preview_browse, 5, 3)
        gif_layout.addWidget(QLabel("Frames"), 6, 0)
        gif_layout.addWidget(self.gif_preview_max, 6, 1)
        gif_layout.addWidget(make_preview, 6, 2)
        return tab

    def _modes_tab(self) -> QWidget:
        tab = QWidget()
        layout = QGridLayout(tab)

        self.clock_style = self._spin(0, 7, 0)
        self.clock_date = QCheckBox("Date")
        self.clock_date.setChecked(True)
        self.clock_24h = QCheckBox("24h")
        self.clock_24h.setChecked(True)
        clock_rgb, self.clock_rgb = self._rgb_editor((255, 255, 255))
        clock = QPushButton("Clock")
        clock.clicked.connect(
            lambda: self._run_device(
                "clock",
                lambda matrix: matrix.clock(
                    self.clock_style.value(),
                    visible_date=self.clock_date.isChecked(),
                    hour24=self.clock_24h.isChecked(),
                    color=self._rgb(self.clock_rgb),
                ),
            )
        )

        self.chrono_mode = self._spin(0, 3, 0)
        chrono = QPushButton("Chronograph")
        chrono.clicked.connect(
            lambda: self._run_device("chronograph", lambda matrix: matrix.chronograph(self.chrono_mode.value()))
        )

        self.countdown_mode = self._spin(0, 3, 0)
        self.countdown_minutes = self._spin(0, 255, 1)
        self.countdown_seconds = self._spin(0, 59, 0)
        countdown = QPushButton("Countdown")
        countdown.clicked.connect(
            lambda: self._run_device(
                "countdown",
                lambda matrix: matrix.countdown(
                    self.countdown_mode.value(),
                    self.countdown_minutes.value(),
                    self.countdown_seconds.value(),
                ),
            )
        )

        self.score_left = self._spin(0, 999, 0)
        self.score_right = self._spin(0, 999, 0)
        scoreboard = QPushButton("Scoreboard")
        scoreboard.clicked.connect(
            lambda: self._run_device(
                "scoreboard",
                lambda matrix: matrix.scoreboard(self.score_left.value(), self.score_right.value()),
            )
        )

        self.effect_style = self._spin(0, 6, 0)
        self.effect_speed = self._spin(0, 255, 90)
        self.effect_colors = QLineEdit("255,0,0;0,255,0")
        effect = QPushButton("Effect")
        effect.clicked.connect(self.send_effect)

        self.eco_flag = self._spin(0, 255, 1)
        self.eco_start_h = self._spin(0, 255, 22)
        self.eco_start_m = self._spin(0, 255, 0)
        self.eco_end_h = self._spin(0, 255, 7)
        self.eco_end_m = self._spin(0, 255, 0)
        self.eco_brightness = self._spin(0, 255, 20)
        eco = QPushButton("ECO")
        eco.clicked.connect(
            lambda: self._run_device(
                "eco",
                lambda matrix: matrix.eco(
                    self.eco_flag.value(),
                    self.eco_start_h.value(),
                    self.eco_start_m.value(),
                    self.eco_end_h.value(),
                    self.eco_end_m.value(),
                    self.eco_brightness.value(),
                ),
            )
        )

        row = 0
        layout.addWidget(QLabel("Clock Style"), row, 0)
        layout.addWidget(self.clock_style, row, 1)
        layout.addWidget(self.clock_date, row, 2)
        layout.addWidget(self.clock_24h, row, 3)
        layout.addWidget(clock_rgb, row, 4)
        layout.addWidget(clock, row, 5)
        row += 1
        layout.addWidget(QLabel("Chronograph Mode"), row, 0)
        layout.addWidget(self.chrono_mode, row, 1)
        layout.addWidget(chrono, row, 2)
        row += 1
        layout.addWidget(QLabel("Countdown"), row, 0)
        layout.addWidget(self.countdown_mode, row, 1)
        layout.addWidget(self.countdown_minutes, row, 2)
        layout.addWidget(self.countdown_seconds, row, 3)
        layout.addWidget(countdown, row, 4)
        row += 1
        layout.addWidget(QLabel("Score"), row, 0)
        layout.addWidget(self.score_left, row, 1)
        layout.addWidget(self.score_right, row, 2)
        layout.addWidget(scoreboard, row, 3)
        row += 1
        layout.addWidget(QLabel("Effect"), row, 0)
        layout.addWidget(self.effect_style, row, 1)
        layout.addWidget(self.effect_speed, row, 2)
        layout.addWidget(self.effect_colors, row, 3, 1, 2)
        layout.addWidget(effect, row, 5)
        row += 1
        layout.addWidget(QLabel("ECO"), row, 0)
        layout.addWidget(self.eco_flag, row, 1)
        layout.addWidget(self.eco_start_h, row, 2)
        layout.addWidget(self.eco_start_m, row, 3)
        layout.addWidget(self.eco_end_h, row, 4)
        layout.addWidget(self.eco_end_m, row, 5)
        layout.addWidget(self.eco_brightness, row, 6)
        layout.addWidget(eco, row, 7)
        layout.setColumnStretch(8, 1)
        return tab

    def _tools_tab(self) -> QWidget:
        tab = QWidget()
        outer = QHBoxLayout(tab)
        left = QWidget()
        right = QGroupBox("Preview")
        outer.addWidget(left, stretch=2)
        outer.addWidget(right, stretch=1)
        layout = QGridLayout(left)
        preview_layout = QVBoxLayout(right)
        preview_layout.addWidget(self.preview_label)

        self.raw_hex = QLineEdit("05 00 07 01 01")
        send_raw = QPushButton("Send Raw")
        send_raw.clicked.connect(
            lambda: self._run_device("raw", lambda matrix: matrix.send(bytes.fromhex(self.raw_hex.text())))
        )
        decode = QPushButton("Decode")
        decode.clicked.connect(self.decode_hex)

        self.sim_text = QLineEdit("Hello")
        self.sim_packet = QLineEdit("07 00 02 02 ff 00 00")
        self.sim_gif = QLineEdit()
        sim_gif_browse = QPushButton("Browse")
        sim_gif_browse.clicked.connect(lambda: self._browse_open(self.sim_gif, "Select GIF or Image"))
        sim_fill_rgb, self.sim_fill_rgb = self._rgb_editor((255, 0, 0))
        self.sim_pixel_x = self._spin(0, 31, 0)
        self.sim_pixel_y = self._spin(0, 31, 0)
        sim_pixel_rgb, self.sim_pixel_rgb = self._rgb_editor((255, 255, 255))
        self.sim_offset = self._spin(0, 9999, 0)
        self.sim_frames = self._spin(1, 9999, 64)
        self.sim_scale = self._spin(1, 64, 16)
        self.sim_grid = QCheckBox("Grid")
        self.sim_grid.setChecked(True)
        self.sim_save = QLineEdit("out/simulation.png")
        sim_save_browse = QPushButton("Browse")
        sim_save_browse.clicked.connect(lambda: self._browse_save(self.sim_save, "Save Simulation"))

        render_text = QPushButton("Render Text")
        render_text.clicked.connect(self.simulate_text)
        render_animation = QPushButton("Text Animation")
        render_animation.clicked.connect(self.simulate_text_animation)
        render_packet = QPushButton("Apply Packet")
        render_packet.clicked.connect(self.simulate_packet)
        render_fill = QPushButton("Fill")
        render_fill.clicked.connect(self.simulate_fill)
        render_pixel = QPushButton("Pixel")
        render_pixel.clicked.connect(self.simulate_pixel)
        render_gif = QPushButton("GIF Frame")
        render_gif.clicked.connect(self.simulate_gif)

        layout.addWidget(QLabel("Hex"), 0, 0)
        layout.addWidget(self.raw_hex, 0, 1, 1, 3)
        layout.addWidget(send_raw, 0, 4)
        layout.addWidget(decode, 0, 5)
        layout.addWidget(QLabel("Text"), 1, 0)
        layout.addWidget(self.sim_text, 1, 1, 1, 3)
        layout.addWidget(render_text, 1, 4)
        layout.addWidget(render_animation, 1, 5)
        layout.addWidget(QLabel("Packet"), 2, 0)
        layout.addWidget(self.sim_packet, 2, 1, 1, 3)
        layout.addWidget(render_packet, 2, 4)
        layout.addWidget(QLabel("GIF"), 3, 0)
        layout.addWidget(self.sim_gif, 3, 1, 1, 2)
        layout.addWidget(sim_gif_browse, 3, 3)
        layout.addWidget(render_gif, 3, 4)
        layout.addWidget(QLabel("Fill RGB"), 4, 0)
        layout.addWidget(sim_fill_rgb, 4, 1)
        layout.addWidget(render_fill, 4, 2)
        layout.addWidget(QLabel("Pixel"), 5, 0)
        layout.addWidget(self.sim_pixel_x, 5, 1)
        layout.addWidget(self.sim_pixel_y, 5, 2)
        layout.addWidget(sim_pixel_rgb, 5, 3)
        layout.addWidget(render_pixel, 5, 4)
        layout.addWidget(QLabel("Offset"), 6, 0)
        layout.addWidget(self.sim_offset, 6, 1)
        layout.addWidget(QLabel("Frames"), 6, 2)
        layout.addWidget(self.sim_frames, 6, 3)
        layout.addWidget(QLabel("Scale"), 7, 0)
        layout.addWidget(self.sim_scale, 7, 1)
        layout.addWidget(self.sim_grid, 7, 2)
        layout.addWidget(QLabel("Save"), 8, 0)
        layout.addWidget(self.sim_save, 8, 1, 1, 3)
        layout.addWidget(sim_save_browse, 8, 4)
        return tab

    def _danger_tab(self) -> QWidget:
        tab = QWidget()
        layout = QGridLayout(tab)
        self.delete_confirm = QCheckBox("Confirm delete-device-data")
        delete = QPushButton("Delete Device Data")
        delete.clicked.connect(self.delete_device_data)
        layout.addWidget(self.delete_confirm, 0, 0)
        layout.addWidget(delete, 0, 1)
        layout.setColumnStretch(2, 1)
        return tab

    def scan_devices(self) -> None:
        timeout = self.scan_timeout.value()

        async def job() -> list[dict[str, Any]]:
            devices = await OpenIDotMatrix.scan(timeout=timeout)
            return [device.__dict__ for device in devices]

        self._run_async("scan", job, on_success=self._populate_devices)

    def send_text(self) -> None:
        text = self.text_value.text()
        font_path = self.font_path.text().strip() or None
        self._run_device(
            "text",
            lambda matrix: matrix.text(
                text,
                mode=self.text_mode.currentData(),
                speed=self.text_speed.value(),
                color_mode=self.text_color_mode.currentData(),
                color=self._rgb(self.text_rgb),
                background_mode=self.text_background_mode.currentData(),
                background=self._rgb(self.text_bg_rgb),
                font_path=font_path,
                font_size=self.font_size.value(),
            ),
        )

    def upload_gif(self) -> None:
        path = self.gif_path.text().strip()
        self._run_device(
            "gif",
            lambda matrix: matrix.gif(
                path,
                process=not self.gif_raw.isChecked(),
                total_length_mode=self.gif_total_length.currentData(),
                wait_for_ack=not self.gif_no_ack.isChecked(),
                response=not self.gif_no_response.isChecked(),
                ack_timeout=self.gif_ack_timeout.value(),
                sleep_between_chunks=self.gif_sleep.value(),
            ),
        )

    def export_gif_preview(self) -> None:
        try:
            paths = save_gif_preview_frames(
                self.gif_path.text().strip(),
                self.gif_preview_out.text().strip(),
                max_frames=self.gif_preview_max.value(),
            )
        except Exception as exc:
            self._append_error("gif preview", exc)
            return
        self._append_result("gif preview", [str(path) for path in paths])
        if paths:
            self._show_preview(paths[0])

    def send_effect(self) -> None:
        colors = self._parse_effect_colors(self.effect_colors.text())
        self._run_device(
            "effect",
            lambda matrix: matrix.effect(colors=colors, style=self.effect_style.value(), speed=self.effect_speed.value()),
        )

    def delete_device_data(self) -> None:
        if not self.delete_confirm.isChecked():
            QMessageBox.warning(self, "Confirmation Required", "Enable the confirmation checkbox first.")
            return
        self._run_device("delete-device-data", lambda matrix: matrix.delete_device_data())

    def decode_hex(self) -> None:
        try:
            self._append_result("decode", parse_packet(bytes.fromhex(self.raw_hex.text())))
        except Exception as exc:
            self._append_error("decode", exc)

    def simulate_text(self) -> None:
        try:
            sim = simulate_text_frame(
                self.sim_text.text(),
                offset=self.sim_offset.value(),
                color=self._rgb(self.text_rgb),
                font_path=self.font_path.text().strip() or None,
                font_size=self.font_size.value(),
            )
            self._save_sim(sim)
        except Exception as exc:
            self._append_error("simulate text", exc)

    def simulate_text_animation(self) -> None:
        try:
            path = Path(self.sim_save.text()).with_suffix(".gif")
            saved = save_text_animation(
                self.sim_text.text(),
                path,
                frames=self.sim_frames.value(),
                scale=self.sim_scale.value(),
                color=self._rgb(self.text_rgb),
                font_path=self.font_path.text().strip() or None,
                font_size=self.font_size.value(),
            )
        except Exception as exc:
            self._append_error("text animation", exc)
            return
        self._append_result("text animation", str(saved))

    def simulate_packet(self) -> None:
        try:
            sim = MatrixSimulator()
            info = sim.apply_packet(bytes.fromhex(self.sim_packet.text()), text_scroll_offset=self.sim_offset.value())
            self._save_sim(sim, info=info)
        except Exception as exc:
            self._append_error("simulate packet", exc)

    def simulate_fill(self) -> None:
        try:
            sim = MatrixSimulator()
            sim.fill(self._rgb(self.sim_fill_rgb))
            self._save_sim(sim)
        except Exception as exc:
            self._append_error("simulate fill", exc)

    def simulate_pixel(self) -> None:
        try:
            sim = MatrixSimulator()
            sim.set_pixel(self.sim_pixel_x.value(), self.sim_pixel_y.value(), self._rgb(self.sim_pixel_rgb))
            self._save_sim(sim)
        except Exception as exc:
            self._append_error("simulate pixel", exc)

    def simulate_gif(self) -> None:
        try:
            sim = MatrixSimulator()
            sim.load_gif_preview(self.sim_gif.text().strip())
            self._save_sim(sim)
        except Exception as exc:
            self._append_error("simulate gif", exc)

    def _save_sim(self, sim: MatrixSimulator, *, info: Any | None = None) -> None:
        path = sim.save(self.sim_save.text(), scale=self.sim_scale.value(), grid=self.sim_grid.isChecked())
        self._append_result("simulate", {"path": str(path), "packet": info})
        self._show_preview(path)

    def _run_device(self, title: str, operation: Callable[[OpenIDotMatrix], Awaitable[Any]]) -> None:
        address = self.address_edit.text().strip() or None

        async def job() -> Any:
            async with OpenIDotMatrix(address=address) as matrix:
                return await operation(matrix)

        self._run_async(title, job)

    def _run_async(
        self,
        title: str,
        job: AsyncJob,
        *,
        on_success: Callable[[Any], None] | None = None,
    ) -> None:
        self._append_text(f"> {title}")
        thread = QThread(self)
        worker = AsyncWorker(job)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(lambda result: self._append_result(title, result))
        if on_success is not None:
            worker.finished.connect(on_success)
        worker.failed.connect(lambda message: self._append_text(f"error: {message}"))
        worker.done.connect(thread.quit)
        worker.done.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda: self._forget_thread(thread))
        self._threads.append(thread)
        thread.start()

    def _populate_devices(self, devices: list[dict[str, Any]]) -> None:
        self.device_combo.blockSignals(True)
        self.device_combo.clear()
        for device in devices:
            label = f"{device.get('name', '')}  {device.get('address', '')}"
            self.device_combo.addItem(label.strip(), device.get("address", ""))
        self.device_combo.blockSignals(False)
        if devices:
            self.device_combo.setCurrentIndex(0)
            self.address_edit.setText(str(devices[0]["address"]))

    def _select_scanned_device(self) -> None:
        address = self.device_combo.currentData()
        if address:
            self.address_edit.setText(str(address))

    def _append_result(self, title: str, result: Any) -> None:
        self._append_text(f"{title} ok\n{_json(result)}")

    def _append_error(self, title: str, exc: Exception) -> None:
        self._append_text(f"{title} error: {type(exc).__name__}: {exc}")

    def _append_text(self, text: str) -> None:
        self.log.append(text)

    def _show_preview(self, path: str | Path) -> None:
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            return
        scaled = pixmap.scaled(
            self.preview_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )
        self.preview_label.setPixmap(scaled)

    def _forget_thread(self, thread: QThread) -> None:
        if thread in self._threads:
            self._threads.remove(thread)

    def _browse_open(self, line_edit: QLineEdit, title: str) -> None:
        path, _selected = QFileDialog.getOpenFileName(self, title)
        if path:
            line_edit.setText(path)

    def _browse_save(self, line_edit: QLineEdit, title: str) -> None:
        path, _selected = QFileDialog.getSaveFileName(self, title, line_edit.text())
        if path:
            line_edit.setText(path)

    def _browse_dir(self, line_edit: QLineEdit, title: str) -> None:
        path = QFileDialog.getExistingDirectory(self, title, line_edit.text() or ".")
        if path:
            line_edit.setText(path)

    def _spin(self, minimum: int, maximum: int, value: int) -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(minimum, maximum)
        spin.setValue(value)
        return spin

    def _float_spin(
        self,
        minimum: float,
        maximum: float,
        value: float,
        step: float,
        *,
        decimals: int = 2,
    ) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(minimum, maximum)
        spin.setSingleStep(step)
        spin.setDecimals(decimals)
        spin.setValue(value)
        return spin

    def _rgb_editor(self, default: tuple[int, int, int]) -> tuple[QWidget, tuple[QSpinBox, QSpinBox, QSpinBox]]:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        spins = tuple(self._spin(0, 255, component) for component in default)
        for spin in spins:
            layout.addWidget(spin)
        return container, spins

    def _enum_combo(self, enum_type: type[Any]) -> QComboBox:
        combo = QComboBox()
        for item in enum_type:
            label = f"{int(item)} - {item.name.lower().replace('_', ' ')}"
            combo.addItem(label, item)
        return combo

    def _rgb(self, spins: tuple[QSpinBox, QSpinBox, QSpinBox]) -> tuple[int, int, int]:
        return spins[0].value(), spins[1].value(), spins[2].value()

    def _parse_effect_colors(self, value: str) -> list[tuple[int, int, int]]:
        colors = []
        for chunk in value.split(";"):
            parts = [int(part.strip()) for part in chunk.split(",")]
            if len(parts) != 3:
                raise ProtocolError("effect colors must look like '255,0,0;0,255,0'")
            colors.append((parts[0], parts[1], parts[2]))
        return colors


def run(argv: list[str] | None = None) -> int:
    app = QApplication(sys.argv if argv is None else [sys.argv[0], *argv])
    app.setApplicationName("open-idotmatrix")
    window = MainWindow()
    window.show()
    try:
        return int(app.exec())
    except OpenIDotMatrixError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
