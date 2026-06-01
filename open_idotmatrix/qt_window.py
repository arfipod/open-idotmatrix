"""PySide6 desktop app for open-idotmatrix."""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from PIL import Image
from PySide6.QtCore import QProcess, Qt, QTimer
from PySide6.QtGui import QImage, QPixmap
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

from .exceptions import OpenIDotMatrixError, ProtocolError
from .game_of_life import GameOfLife, render_life_preview
from .gif import save_matrix_image_preview
from .playable_games import MatrixGame, available_game_names, create_game
from .protocol import parse_packet
from .runtime import MatrixRuntime
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


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("open-idotmatrix")
        self.resize(1120, 820)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._processes: list[QProcess] = []
        self._game: MatrixGame | None = None
        self._game_runtime: MatrixRuntime | None = None
        self._game_timer = QTimer(self)
        self._game_timer.timeout.connect(self._game_tick)
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
        tabs.addTab(self._games_tab(), "Games")
        tabs.addTab(self._demos_tab(), "Demos")
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
        self.idm_only = QCheckBox("IDM only")
        self.idm_only.setChecked(True)
        self.status_label = QLabel("Idle")

        scan = QPushButton("Scan")
        scan.clicked.connect(self.scan_devices)
        connect = QPushButton("Test Connect")
        connect.clicked.connect(self.test_connection)
        clear = QPushButton("Clear Log")
        clear.clicked.connect(self.log.clear)

        layout.addWidget(QLabel("Address"), 0, 0)
        layout.addWidget(self.address_edit, 0, 1)
        layout.addWidget(QLabel("Scanned"), 0, 2)
        layout.addWidget(self.device_combo, 0, 3)
        layout.addWidget(QLabel("Timeout"), 0, 4)
        layout.addWidget(self.scan_timeout, 0, 5)
        layout.addWidget(self.idm_only, 0, 6)
        layout.addWidget(scan, 0, 7)
        layout.addWidget(connect, 0, 8)
        layout.addWidget(clear, 0, 9)
        layout.addWidget(QLabel("Status"), 1, 0)
        layout.addWidget(self.status_label, 1, 1, 1, 9)
        layout.setColumnStretch(1, 2)
        layout.setColumnStretch(3, 2)
        return panel

    def _basic_tab(self) -> QWidget:
        tab = QWidget()
        layout = QGridLayout(tab)

        on = QPushButton("On")
        on.clicked.connect(lambda: self._run_device("on", ["on"]))
        off = QPushButton("Off")
        off.clicked.connect(lambda: self._run_device("off", ["off"]))
        freeze = QPushButton("Freeze")
        freeze.clicked.connect(lambda: self._run_device("freeze", ["freeze"]))
        reset = QPushButton("Reset")
        reset.clicked.connect(lambda: self._run_device("reset", ["reset"]))

        self.brightness = self._spin(5, 100, 80)
        brightness = QPushButton("Set Brightness")
        brightness.clicked.connect(
            lambda: self._run_device("brightness", ["brightness", str(self.brightness.value())])
        )

        flip_on = QPushButton("Flip On")
        flip_on.clicked.connect(lambda: self._run_device("flip on", ["flip"]))
        flip_off = QPushButton("Flip Off")
        flip_off.clicked.connect(lambda: self._run_device("flip off", ["flip", "--disable"]))

        self.year_mode = QComboBox()
        for mode in YearByteMode:
            self.year_mode.addItem(mode.value, mode)
        sync = QPushButton("Sync Time")
        sync.clicked.connect(
            lambda: self._run_device("sync time", ["sync-time", "--year-mode", self._combo_value(self.year_mode)])
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
            lambda: self._run_device("fill", ["fill", *self._rgb_args(self.fill_rgb)])
        )

        self.pixel_x = self._spin(0, 31, 0)
        self.pixel_y = self._spin(0, 31, 0)
        pixel_rgb, self.pixel_rgb = self._rgb_editor((255, 255, 255))
        pixel = QPushButton("Set Pixel")
        pixel.clicked.connect(
            lambda: self._run_device(
                "pixel",
                ["pixel", str(self.pixel_x.value()), str(self.pixel_y.value()), *self._rgb_args(self.pixel_rgb)],
            )
        )

        spiral_rgb, self.spiral_rgb = self._rgb_editor((255, 0, 0))
        self.spiral_delay = self._float_spin(0.0, 5.0, 0.0, 0.01, decimals=3)
        spiral = QPushButton("Spiral")
        spiral.clicked.connect(
            lambda: self._run_device(
                "spiral",
                ["spiral", *self._rgb_args(self.spiral_rgb), "--delay", str(self.spiral_delay.value())],
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
        self.media_path = QLineEdit()
        media_browse = QPushButton("Browse")
        media_browse.clicked.connect(lambda: self._browse_open(self.media_path, "Select Image or GIF"))
        preview_media = QPushButton("Preview 32x32")
        preview_media.clicked.connect(self.preview_media_32x32)
        send_media = QPushButton("Send to Display")
        send_media.clicked.connect(self.send_media)
        self.gif_raw = QCheckBox("Raw")
        self.gif_no_ack = QCheckBox("No ACK")
        self.gif_no_response = QCheckBox("No Response")
        self.gif_no_ack.setChecked(True)
        self.gif_no_response.setChecked(True)
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

        self.image_path = QLineEdit()
        image_browse = QPushButton("Browse")
        image_browse.clicked.connect(lambda: self._browse_open(self.image_path, "Select Image"))
        self.image_preview_path = QLineEdit("out/image_32x32.png")
        image_preview_browse = QPushButton("Browse")
        image_preview_browse.clicked.connect(lambda: self._browse_save(self.image_preview_path, "Save 32x32 Preview"))
        self.image_no_ack = QCheckBox("No ACK")
        self.image_no_ack.setChecked(True)
        self.image_no_response = QCheckBox("No Response")
        self.image_no_response.setChecked(True)
        preview_image = QPushButton("Preview 32x32")
        preview_image.clicked.connect(self.preview_image_32x32)
        send_image = QPushButton("Send Image")
        send_image.clicked.connect(self.send_image)

        gif_layout.addWidget(QLabel("File"), 0, 0)
        gif_layout.addWidget(self.media_path, 0, 1, 1, 2)
        gif_layout.addWidget(media_browse, 0, 3)
        gif_layout.addWidget(preview_media, 1, 2)
        gif_layout.addWidget(send_media, 1, 3)
        gif_layout.addWidget(QLabel("GIF Path"), 3, 0)
        gif_layout.addWidget(self.gif_path, 3, 1, 1, 2)
        gif_layout.addWidget(gif_browse, 3, 3)
        gif_layout.addWidget(self.gif_raw, 4, 0)
        gif_layout.addWidget(self.gif_no_ack, 4, 1)
        gif_layout.addWidget(self.gif_no_response, 4, 2)
        gif_layout.addWidget(QLabel("Length Mode"), 5, 0)
        gif_layout.addWidget(self.gif_total_length, 5, 1)
        gif_layout.addWidget(QLabel("ACK Timeout"), 6, 0)
        gif_layout.addWidget(self.gif_ack_timeout, 6, 1)
        gif_layout.addWidget(QLabel("Sleep"), 6, 2)
        gif_layout.addWidget(self.gif_sleep, 6, 3)
        gif_layout.addWidget(upload_gif, 7, 0)
        gif_layout.addWidget(QLabel("Preview Out"), 8, 0)
        gif_layout.addWidget(self.gif_preview_out, 8, 1, 1, 2)
        gif_layout.addWidget(preview_browse, 8, 3)
        gif_layout.addWidget(QLabel("Frames"), 9, 0)
        gif_layout.addWidget(self.gif_preview_max, 9, 1)
        gif_layout.addWidget(make_preview, 9, 2)
        gif_layout.addWidget(QLabel("Image Path"), 11, 0)
        gif_layout.addWidget(self.image_path, 11, 1, 1, 2)
        gif_layout.addWidget(image_browse, 11, 3)
        gif_layout.addWidget(QLabel("32x32 Preview"), 12, 0)
        gif_layout.addWidget(self.image_preview_path, 12, 1, 1, 2)
        gif_layout.addWidget(image_preview_browse, 12, 3)
        gif_layout.addWidget(self.image_no_ack, 13, 0)
        gif_layout.addWidget(self.image_no_response, 13, 1)
        gif_layout.addWidget(preview_image, 13, 2)
        gif_layout.addWidget(send_image, 13, 3)
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
                self._clock_args(),
            )
        )

        self.chrono_mode = self._spin(0, 3, 0)
        chrono = QPushButton("Chronograph")
        chrono.clicked.connect(
            lambda: self._run_device("chronograph", ["chronograph", str(self.chrono_mode.value())])
        )

        self.countdown_mode = self._spin(0, 3, 0)
        self.countdown_minutes = self._spin(0, 255, 1)
        self.countdown_seconds = self._spin(0, 59, 0)
        countdown = QPushButton("Countdown")
        countdown.clicked.connect(
            lambda: self._run_device(
                "countdown",
                [
                    "countdown",
                    str(self.countdown_mode.value()),
                    str(self.countdown_minutes.value()),
                    str(self.countdown_seconds.value()),
                ],
            )
        )

        self.score_left = self._spin(0, 999, 0)
        self.score_right = self._spin(0, 999, 0)
        scoreboard = QPushButton("Scoreboard")
        scoreboard.clicked.connect(
            lambda: self._run_device(
                "scoreboard",
                ["scoreboard", str(self.score_left.value()), str(self.score_right.value())],
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
                [
                    "eco",
                    str(self.eco_flag.value()),
                    str(self.eco_start_h.value()),
                    str(self.eco_start_m.value()),
                    str(self.eco_end_h.value()),
                    str(self.eco_end_m.value()),
                    str(self.eco_brightness.value()),
                ],
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
            lambda: self._run_device("raw", ["raw", self.raw_hex.text()])
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

    def _demos_tab(self) -> QWidget:
        tab = QWidget()
        layout = QGridLayout(tab)

        self.life_seed = QComboBox()
        for name in GameOfLife.pattern_names():
            self.life_seed.addItem(name, name)
        self.life_random_seed = QSpinBox()
        self.life_random_seed.setRange(-1, 2_147_483_647)
        self.life_random_seed.setValue(-1)
        self.life_generations = self._spin(0, 10000, 200)
        self.life_fps = self._float_spin(0.1, 60.0, 12.0, 1.0)
        self.life_density = self._float_spin(0.0, 1.0, 0.28, 0.01, decimals=2)
        self.life_wrap = QCheckBox("Wrap edges")
        self.life_wrap.setChecked(True)
        life_alive_rgb, self.life_alive_rgb = self._rgb_editor((0, 255, 80))
        life_dead_rgb, self.life_dead_rgb = self._rgb_editor((0, 0, 0))
        self.life_preview_path = QLineEdit("out/life.gif")
        life_preview_browse = QPushButton("Browse")
        life_preview_browse.clicked.connect(lambda: self._browse_save(self.life_preview_path, "Save Life Preview"))
        run_life = QPushButton("Run on Matrix")
        run_life.clicked.connect(self.run_life)
        preview_life = QPushButton("Preview GIF")
        preview_life.clicked.connect(self.preview_life)

        layout.addWidget(QLabel("Conway Life"), 0, 0)
        layout.addWidget(QLabel("Seed"), 1, 0)
        layout.addWidget(self.life_seed, 1, 1)
        layout.addWidget(QLabel("Random Seed"), 1, 2)
        layout.addWidget(self.life_random_seed, 1, 3)
        layout.addWidget(QLabel("Generations"), 2, 0)
        layout.addWidget(self.life_generations, 2, 1)
        layout.addWidget(QLabel("FPS"), 2, 2)
        layout.addWidget(self.life_fps, 2, 3)
        layout.addWidget(QLabel("Density"), 3, 0)
        layout.addWidget(self.life_density, 3, 1)
        layout.addWidget(self.life_wrap, 3, 2)
        layout.addWidget(QLabel("Alive RGB"), 4, 0)
        layout.addWidget(life_alive_rgb, 4, 1)
        layout.addWidget(QLabel("Dead RGB"), 5, 0)
        layout.addWidget(life_dead_rgb, 5, 1)
        layout.addWidget(QLabel("Preview"), 6, 0)
        layout.addWidget(self.life_preview_path, 6, 1, 1, 2)
        layout.addWidget(life_preview_browse, 6, 3)
        layout.addWidget(run_life, 7, 0)
        layout.addWidget(preview_life, 7, 1)
        layout.setColumnStretch(4, 1)
        return tab

    def _games_tab(self) -> QWidget:
        tab = QWidget()
        layout = QGridLayout(tab)

        self.game_name = QComboBox()
        for name in available_game_names():
            self.game_name.addItem(name.replace("_", " ").title(), name)
        self.game_fps = self._float_spin(1.0, 30.0, 12.0, 1.0)
        self.game_preview_only = QCheckBox("Preview only")
        self.game_preview_only.setChecked(False)
        self.game_seed = QSpinBox()
        self.game_seed.setRange(-1, 2_147_483_647)
        self.game_seed.setValue(-1)
        start_game = QPushButton("Start")
        start_game.clicked.connect(self.start_game)
        stop_game = QPushButton("Stop")
        stop_game.clicked.connect(self.stop_game)

        layout.addWidget(QLabel("Game"), 0, 0)
        layout.addWidget(self.game_name, 0, 1)
        layout.addWidget(QLabel("FPS"), 0, 2)
        layout.addWidget(self.game_fps, 0, 3)
        layout.addWidget(QLabel("Seed"), 1, 0)
        layout.addWidget(self.game_seed, 1, 1)
        layout.addWidget(self.game_preview_only, 1, 2)
        layout.addWidget(start_game, 2, 0)
        layout.addWidget(stop_game, 2, 1)
        layout.setColumnStretch(4, 1)
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
        args = ["-m", "open_idotmatrix.cli", "scan", "--timeout", str(timeout)]
        if not self.idm_only.isChecked():
            args.append("--all")
        self._run_process_json("scan", args, on_success=self._populate_devices)

    def test_connection(self) -> None:
        self._run_device("test connection", ["status"])

    def send_text(self) -> None:
        text = self.text_value.text()
        args = [
            "text",
            text,
            "--mode",
            str(int(self.text_mode.currentData())),
            "--speed",
            str(self.text_speed.value()),
            "--color-mode",
            str(int(self.text_color_mode.currentData())),
            "--rgb",
            *self._rgb_args(self.text_rgb),
            "--background-mode",
            str(int(self.text_background_mode.currentData())),
            "--background-rgb",
            *self._rgb_args(self.text_bg_rgb),
            "--font-size",
            str(self.font_size.value()),
        ]
        font_path = self.font_path.text().strip()
        if font_path:
            args.extend(["--font-path", font_path])
        self._run_device("text", args)

    def upload_gif(self) -> None:
        path = self._selected_file(self.gif_path, "GIF")
        if path is None:
            return
        args = ["gif", path]
        if self.gif_raw.isChecked():
            args.append("--raw")
        args.extend(self._upload_args(self.gif_no_ack.isChecked(), self.gif_no_response.isChecked()))
        self._run_device("gif", args)

    def export_gif_preview(self) -> None:
        path = self._selected_file(self.gif_path, "GIF")
        if path is None:
            return
        try:
            paths = save_gif_preview_frames(
                path,
                self.gif_preview_out.text().strip(),
                max_frames=self.gif_preview_max.value(),
            )
        except Exception as exc:
            self._append_error("gif preview", exc)
            return
        self._append_result("gif preview", [str(path) for path in paths])
        if paths:
            self._show_preview(paths[0])

    def preview_media_32x32(self) -> None:
        path = self._selected_file(self.media_path, "media")
        if path is None:
            return
        self.image_path.setText(path)
        self.preview_image_32x32()

    def send_media(self) -> None:
        path = self._selected_file(self.media_path, "media")
        if path is None:
            return
        if Path(path).suffix.lower() == ".gif":
            self.gif_path.setText(path)
            self.upload_gif()
            return
        self.image_path.setText(path)
        self.send_image()

    def preview_image_32x32(self) -> None:
        path = self._selected_file(self.image_path, "image")
        if path is None:
            return
        try:
            path = save_matrix_image_preview(
                path,
                self.image_preview_path.text().strip(),
                scale=16,
                grid=True,
            )
        except Exception as exc:
            self._append_error("image preview", exc)
            return
        self._append_result(
            "image preview",
            {
                "path": str(path),
                "conversion": "stretched to 1:1, nearest-neighbor sampled to 32x32",
            },
        )
        self._show_preview(path)

    def send_image(self) -> None:
        path = self._selected_file(self.image_path, "image")
        if path is None:
            return
        self._run_device(
            "image",
            ["image", path, *self._upload_args(self.image_no_ack.isChecked(), self.image_no_response.isChecked())],
        )

    def send_effect(self) -> None:
        colors = self._parse_effect_colors(self.effect_colors.text())
        self._run_device(
            "effect",
            [
                "effect",
                str(self.effect_style.value()),
                self._format_colors(colors),
                "--speed",
                str(self.effect_speed.value()),
            ],
        )

    def run_life(self) -> None:
        self._run_device("life", ["life", *self._life_args()])

    def start_game(self) -> None:
        self.stop_game()
        seed = None if self.game_seed.value() < 0 else self.game_seed.value()
        try:
            self._game = create_game(self._combo_value(self.game_name), seed=seed)
            if not self.game_preview_only.isChecked():
                address = self.address_edit.text().strip() or None
                self._game_runtime = MatrixRuntime(
                    address=address,
                    renderer_kwargs={"strategy": "pixels"},
                    clear_first=(0, 0, 0),
                )
                self._game_runtime.start(timeout=10.0)
        except Exception as exc:
            self._game = None
            self._game_runtime = None
            self._append_error("game", exc)
            self._set_status("Game error")
            return
        interval = max(1, int(1000 / self.game_fps.value()))
        self._game_timer.start(interval)
        self._set_status(f"Game running: {self._combo_value(self.game_name)}")
        self.setFocus(Qt.FocusReason.OtherFocusReason)

    def stop_game(self) -> None:
        self._game_timer.stop()
        if self._game_runtime is not None:
            try:
                self._game_runtime.close(timeout=3.0)
            except Exception as exc:
                self._append_error("game stop", exc)
        self._game_runtime = None
        self._game = None

    def _game_tick(self) -> None:
        if self._game is None:
            return
        frame = self._game.tick()
        self._show_frame_preview(frame)
        if self._game_runtime is not None:
            self._game_runtime.submit_frame(frame)

    def preview_life(self) -> None:
        try:
            path = render_life_preview(
                self.life_preview_path.text().strip(),
                seed=self._combo_value(self.life_seed),
                generations=max(1, self.life_generations.value()),
                fps=self.life_fps.value(),
                density=self.life_density.value(),
                random_seed=self._life_random_seed(),
                wrap=self.life_wrap.isChecked(),
                alive_color=self._rgb(self.life_alive_rgb),
                dead_color=self._rgb(self.life_dead_rgb),
            )
        except Exception as exc:
            self._append_error("life preview", exc)
            return
        self._append_result("life preview", {"path": str(path)})
        self._show_preview(path)

    def keyPressEvent(self, event) -> None:  # noqa: N802 - Qt API
        if self._game is None:
            super().keyPressEvent(event)
            return
        action = self._game_action_for_key(event.key())
        if action is None:
            super().keyPressEvent(event)
            return
        self._game.control(action)
        event.accept()

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt API
        self.stop_game()
        super().closeEvent(event)

    def _game_action_for_key(self, key: int) -> str | None:
        if key == Qt.Key.Key_Left:
            return "left"
        if key == Qt.Key.Key_Right:
            return "right"
        if key == Qt.Key.Key_Down:
            return "down"
        if key in (Qt.Key.Key_R,):
            return "reset"
        if key in (Qt.Key.Key_Up, Qt.Key.Key_Z, Qt.Key.Key_X):
            return "flap" if self._game is not None and self._game.name == "flappy" else "rotate"
        if key == Qt.Key.Key_Space:
            if self._game is None:
                return None
            if self._game.name == "flappy":
                return "flap"
            if self._game.name == "tetris":
                return "drop"
            if self._game.name == "space_invaders":
                return "fire"
        return None

    def delete_device_data(self) -> None:
        if not self.delete_confirm.isChecked():
            QMessageBox.warning(self, "Confirmation Required", "Enable the confirmation checkbox first.")
            return
        self._run_device("delete-device-data", ["delete-device-data", "--yes"])

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
        path = self._selected_file(self.sim_gif, "GIF")
        if path is None:
            return
        try:
            sim = MatrixSimulator()
            sim.load_gif_preview(path)
            self._save_sim(sim)
        except Exception as exc:
            self._append_error("simulate gif", exc)

    def _save_sim(self, sim: MatrixSimulator, *, info: Any | None = None) -> None:
        path = sim.save(self.sim_save.text(), scale=self.sim_scale.value(), grid=self.sim_grid.isChecked())
        self._append_result("simulate", {"path": str(path), "packet": info})
        self._show_preview(path)

    def _run_device(self, title: str, command_args: list[str]) -> None:
        args = ["-m", "open_idotmatrix.cli"]
        address = self.address_edit.text().strip()
        if address:
            args.extend(["--address", address])
        args.extend(command_args)
        self._run_process_json(title, args)

    def _clock_args(self) -> list[str]:
        args = ["clock", str(self.clock_style.value()), "--rgb", *self._rgb_args(self.clock_rgb)]
        if not self.clock_date.isChecked():
            args.append("--hide-date")
        if not self.clock_24h.isChecked():
            args.append("--hour12")
        return args

    def _upload_args(self, no_ack: bool, no_response: bool) -> list[str]:
        args = [
            "--ack-timeout",
            str(self.gif_ack_timeout.value()),
            "--sleep-between-chunks",
            str(self.gif_sleep.value()),
            "--total-length-mode",
            self._combo_value(self.gif_total_length),
        ]
        if no_ack:
            args.append("--no-ack")
        if no_response:
            args.append("--no-response")
        return args

    def _life_args(self) -> list[str]:
        args = [
            "--seed",
            self._combo_value(self.life_seed),
            "--density",
            str(self.life_density.value()),
            "--generations",
            str(self.life_generations.value()),
            "--fps",
            str(self.life_fps.value()),
            "--alive-rgb",
            *self._rgb_args(self.life_alive_rgb),
            "--dead-rgb",
            *self._rgb_args(self.life_dead_rgb),
        ]
        random_seed = self._life_random_seed()
        if random_seed is not None:
            args.extend(["--random-seed", str(random_seed)])
        if not self.life_wrap.isChecked():
            args.append("--no-wrap")
        return args

    def _life_random_seed(self) -> int | None:
        value = self.life_random_seed.value()
        return None if value < 0 else value

    def _rgb_args(self, spins: tuple[QSpinBox, QSpinBox, QSpinBox]) -> list[str]:
        return [str(value) for value in self._rgb(spins)]

    def _format_colors(self, colors: list[tuple[int, int, int]]) -> str:
        return ";".join(f"{r},{g},{b}" for r, g, b in colors)

    def _combo_value(self, combo: QComboBox) -> str:
        data = combo.currentData()
        return str(getattr(data, "value", data))

    def _selected_file(self, line_edit: QLineEdit, label: str) -> str | None:
        value = line_edit.text().strip()
        if not value:
            self._append_text(f"error: choose a {label} file first")
            self._set_status(f"Missing {label} file")
            return None
        path = Path(value).expanduser()
        if not path.exists():
            self._append_text(f"error: {label} file does not exist: {value}")
            self._set_status(f"Missing {label} file")
            return None
        if path.is_dir():
            self._append_text(f"error: choose a {label} file, not a directory: {value}")
            self._set_status(f"Invalid {label} path")
            return None
        return str(path)

    def _run_process_json(
        self,
        title: str,
        args: list[str],
        *,
        on_success: Callable[[Any], None] | None = None,
    ) -> None:
        if self._processes:
            self._append_text("error: wait for the current device command to finish")
            self._set_status("Busy")
            return
        self._append_text(f"> {title}")
        self._set_status(f"Running: {title}")
        process = QProcess(self)
        process.setProgram(sys.executable)
        process.setArguments(args)
        process.setProcessChannelMode(QProcess.ProcessChannelMode.SeparateChannels)
        process.finished.connect(
            lambda exit_code, exit_status, current=process: self._finish_process_json(
                title,
                current,
                exit_code,
                exit_status,
                on_success=on_success,
            )
        )
        process.errorOccurred.connect(
            lambda error, current=process: self._fail_process_start(title, current, error)
        )
        self._processes.append(process)
        process.start()

    def _finish_process_json(
        self,
        title: str,
        process: QProcess,
        exit_code: int,
        exit_status: QProcess.ExitStatus,
        *,
        on_success: Callable[[Any], None] | None = None,
    ) -> None:
        stdout = bytes(process.readAllStandardOutput()).decode(errors="replace").strip()
        stderr = bytes(process.readAllStandardError()).decode(errors="replace").strip()
        self._forget_process(process)
        process.deleteLater()
        if exit_status != QProcess.ExitStatus.NormalExit or exit_code != 0:
            message = stderr or stdout or f"process exited with code {exit_code}"
            self._append_text(f"error: {message}")
            self._set_status(f"Error: {title}")
            return
        try:
            result = json.loads(stdout or "null")
        except json.JSONDecodeError as exc:
            self._append_text(f"error: could not decode {title} output: {exc}\n{stdout}")
            self._set_status(f"Error: {title}")
            return
        self._append_result(title, result)
        self._set_status(f"OK: {title}")
        if on_success is not None:
            on_success(result)

    def _fail_process_start(self, title: str, process: QProcess, error: QProcess.ProcessError) -> None:
        message = process.errorString() or str(error)
        self._forget_process(process)
        process.deleteLater()
        self._append_text(f"error: {message}")
        self._set_status(f"Error: {title}")

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
            self._set_status(f"Scan found {len(devices)} device(s)")
        else:
            self._set_status("Scan found 0 devices")

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

    def _set_status(self, text: str) -> None:
        self.status_label.setText(text)

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

    def _show_frame_preview(self, frame) -> None:
        image = frame.to_image().resize((256, 256), Image.Resampling.NEAREST)
        data = image.tobytes()
        qimage = QImage(data, image.width, image.height, image.width * 3, QImage.Format.Format_RGB888).copy()
        pixmap = QPixmap.fromImage(qimage)
        scaled = pixmap.scaled(
            self.preview_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )
        self.preview_label.setPixmap(scaled)

    def _forget_process(self, process: QProcess) -> None:
        if process in self._processes:
            self._processes.remove(process)

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
