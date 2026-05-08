"""
UNH/CCOM-JHC Backscatter Correction Plotter.

Copyright (c) 2025, UNH/CCOM-JHC.
BSD 3-Clause License (see BSD-3-Clause-UNH-CCOM-JHC.txt).
"""

from pathlib import Path
import re
import argparse
import sys
import os
from datetime import datetime

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from PyQt6 import QtCore, QtWidgets, QtGui

__version__ = "2026.1"


def _slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", text.strip()).strip("_")


def _project_root() -> Path:
    return Path(__file__).resolve().parent


def _sat_icon_candidates() -> list[Path]:
    icon_dir = _project_root() / "BS_corr_plotter" / "media"
    return sorted(icon_dir.glob("*.ico"))


def _apply_sat_icons(window: QtWidgets.QWidget):
    # Use only .ico files in BS_corr_plotter/media.
    for candidate in _sat_icon_candidates():
        icon = QtGui.QIcon(str(candidate))
        if not icon.isNull():
            app = QtWidgets.QApplication.instance()
            if app is not None:
                app.setWindowIcon(icon)
            window.setWindowIcon(icon)
            return


def swath_label(swath_id: int) -> str:
    if swath_id == 0:
        return "Single Swath"
    if swath_id == 1:
        return "Dual Swath 1"
    if swath_id == 2:
        return "Dual Swath 2"
    return f"Swath {swath_id}"


def _parse_pairs(tokens, ignore_first_value):
    vals = list(tokens)
    if ignore_first_value and vals:
        vals = vals[1:]
        ignore_first_value = False

    pairs = []
    for i in range(0, len(vals) - 1, 2):
        try:
            x = float(vals[i])
            y = float(vals[i + 1])
            pairs.append((x, y))
        except ValueError:
            continue

    return pairs, ignore_first_value


def _format_cal_time(cal_time):
    if not cal_time:
        return cal_time

    text = cal_time.strip()
    for fmt in ("%d-%b-%Y %H:%M:%S", "%d-%b-%Y %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            dt = datetime.strptime(text, fmt)
            return dt.strftime("%Y-%m-%d %H:%M")
        except ValueError:
            continue
    return text


def _format_export_timestamp(cal_time):
    if not cal_time:
        return "NA"

    text = str(cal_time).strip()
    for fmt in ("%d-%b-%Y %H:%M:%S", "%d-%b-%Y %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            dt = datetime.strptime(text, fmt)
            return dt.strftime("%Y%m%d_%H%M%S")
        except ValueError:
            continue

    # Last-resort fallback keeps only numeric/date separators.
    fallback = re.sub(r"[^0-9]", "", text)
    if len(fallback) >= 14:
        return f"{fallback[:8]}_{fallback[8:14]}"
    return "NA"


def parse_swath_sector_file(path: Path):
    data = {}
    kmall_name = None
    correction_file_name = None
    cal_time = None
    model_number = None
    parsing_table = False
    current_mode = None
    current_swath = None
    current_sector = None
    ignore_first_value_for_sector = False

    text = path.read_text(encoding="utf-8-sig", errors="replace")
    if len(text.splitlines()) <= 2 and "#" in text:
        text = text.replace(" # ", "\n# ").replace(" #", "\n#")
    lines = text.splitlines()
    for raw in lines:
        line = raw.strip()
        if not line:
            continue

        if not parsing_table:
            if model_number is None:
                model_match = re.search(r"\bEM\s*(2040|2042|710|712|304|124)\b", line, re.IGNORECASE)
                if model_match:
                    model_number = model_match.group(1)
            if kmall_name is None:
                kmall_match = re.search(r"([^\s\\/:*?\"<>|]+\.kmall)\b", line, re.IGNORECASE)
                if kmall_match:
                    kmall_name = kmall_match.group(1).strip()
            file_name_match = re.search(r"(?:^|#\s*)File name:\s*(.+)", line, re.IGNORECASE)
            if file_name_match and correction_file_name is None:
                correction_file_name = file_name_match.group(1).strip()
            cal_time_match = re.search(r"(?:^|#\s*)Calibration date=\s*(.+)", line, re.IGNORECASE)
            if cal_time_match and cal_time is None:
                cal_time = cal_time_match.group(1).strip()
            if line.endswith("Calibration table:"):
                parsing_table = True
            continue

        mode_swath_match = re.match(r"(.+?)\s*-\s*(dual|single)\s*swath(?:\s*(\d+))?", line, re.IGNORECASE)
        if mode_swath_match:
            current_mode = mode_swath_match.group(1).strip().lstrip("#").strip()
            swath_kind = mode_swath_match.group(2).lower()
            swath_num = mode_swath_match.group(3)
            current_swath = 0 if swath_kind == "single" else int(swath_num) if swath_num else 0
            data.setdefault(current_mode, {})
            data[current_mode].setdefault(current_swath, {})
            current_sector = None
            ignore_first_value_for_sector = False
            continue

        if line.lower() in {"shallow", "medium", "deep", "very deep", "deeper", "extra deep"}:
            current_mode = line
            data.setdefault(current_mode, {})
            current_swath = None
            current_sector = None
            ignore_first_value_for_sector = False
            continue

        swath_only_match = re.match(r"Dual\s*swath\s*(\d+)", line, re.IGNORECASE)
        if swath_only_match:
            if current_mode is None:
                current_mode = "Unknown mode"
                data.setdefault(current_mode, {})
            current_swath = int(swath_only_match.group(1))
            data[current_mode].setdefault(current_swath, {})
            current_sector = None
            ignore_first_value_for_sector = False
            continue

        if line.lower().startswith("mode, swath, ntx sectors"):
            continue

        sector_match = re.match(r"#\s*TX\s*sector\s*(\d+)\s*:\s*(.*)$", line, re.IGNORECASE)
        if sector_match:
            current_sector = int(sector_match.group(1))
            ignore_first_value_for_sector = True
            if current_mode is not None and current_swath is not None:
                data[current_mode].setdefault(current_swath, {})
                data[current_mode][current_swath].setdefault(current_sector, [])
                inline_vals = sector_match.group(2).split()
                inline_pairs, ignore_first_value_for_sector = _parse_pairs(
                    inline_vals, ignore_first_value_for_sector
                )
                if inline_pairs:
                    data[current_mode][current_swath][current_sector].extend(inline_pairs)
            continue

        if current_mode is None or current_swath is None or current_sector is None:
            continue

        vals = line.split()
        if len(vals) < 2:
            continue

        pairs, ignore_first_value_for_sector = _parse_pairs(vals, ignore_first_value_for_sector)
        if pairs:
            data[current_mode][current_swath][current_sector].extend(pairs)

    return data, kmall_name, correction_file_name, cal_time, model_number


def build_mode_figure(
    mode_name,
    mode_data,
    source_title,
    kmall_name=None,
    correction_file_name=None,
    cal_time=None,
    model_number=None,
):
    if not mode_data:
        raise ValueError("No plottable swath/sector data found.")

    n_swaths = len(mode_data)
    formatted_cal_time = _format_cal_time(cal_time) if cal_time else "NA"
    model_name = f"EM {model_number}" if model_number and str(model_number).upper() != "NA" else "NA"
    metadata_rows = [
        ("Source file:", kmall_name or source_title or "NA"),
        ("Calib. file:", correction_file_name or "NA"),
        ("Calib. date:", formatted_cal_time),
        ("Model:", model_name),
        ("Mode:", mode_name),
    ]
    # Build a compact two-column block with left-aligned labels and values.
    label_width = max(len(label) for label, _ in metadata_rows) + 2
    title_lines = [f"{label:<{label_width}}{value}" for label, value in metadata_rows]

    # Keep each subplot the same height and reserve compact room for multi-line titles.
    per_subplot_height = 3.6
    title_block_height = 0.72 + (0.28 * len(title_lines))
    fig, axes = plt.subplots(
        n_swaths,
        1,
        figsize=(12, (per_subplot_height * n_swaths) + title_block_height),
        sharex=True,
        sharey=True,
    )
    if n_swaths == 1:
        axes = [axes]

    y_vals = []
    for swath in mode_data.values():
        for sector_pts in swath.values():
            y_vals.extend([p[1] for p in sector_pts])

    y_min_mode = min(y_vals) if y_vals else -15
    y_max_mode = max(y_vals) if y_vals else 15
    y_lim_min = -15 if y_min_mode >= -15 else y_min_mode
    y_lim_max = 15 if y_max_mode <= 15 else y_max_mode

    for ax, swath in zip(axes, sorted(mode_data.keys())):
        sectors = mode_data[swath]
        for sector in sorted(sectors.keys()):
            pts = sectors[sector]
            pts = sorted(pts, key=lambda p: p[0])
            x = [p[0] for p in pts]
            y = [p[1] for p in pts]
            ax.plot(
                x,
                y,
                marker="o",
                linewidth=1,
                markersize=2,
                label=f"{swath_label(swath)} - TX sector {sector}",
            )

        ax.set_title(f"{mode_name} - {swath_label(swath)}", fontweight="bold")
        ax.set_xlabel("TX beam angle (deg)")
        ax.set_ylabel("BS corr. (dB)")
        ax.set_xlim(-85, 85)
        ax.set_ylim(y_lim_min, y_lim_max)
        ax.grid(True, alpha=0.3)
        ax.legend(
            ncol=2,
            fontsize=8,
            loc="upper right",
            framealpha=0.7,
            facecolor="white",
        )

    fig.suptitle(
        "\n".join(title_lines),
        fontsize=11,
        linespacing=1.15,
        x=0.55,
        ha="center",
        multialignment="left",
        fontfamily="DejaVu Sans Mono",
    )

    # Lock title area/gap in pixels so title size/spacing remain visually fixed on resize.
    _fixed_title_px = {"value": None}
    _fixed_gap_px = 60.0  # slightly larger fixed gap for extra title clearance

    def _refresh_subplot_spacing(_event=None):
        # Keep title layout unchanged; only shrink/grow subplot region as needed.
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        fig_bbox = fig.bbox
        if fig_bbox.height <= 0:
            return

        if _fixed_title_px["value"] is None:
            title_bbox = fig._suptitle.get_window_extent(renderer=renderer)
            _fixed_title_px["value"] = title_bbox.height

        top = 1.0 - ((_fixed_title_px["value"] + _fixed_gap_px) / fig_bbox.height)
        top = max(0.50, min(0.90, top))
        fig.subplots_adjust(hspace=0.42, top=top, bottom=0.08)

    # Initial spacing + automatic updates while the user resizes the window.
    _refresh_subplot_spacing()
    fig.canvas.mpl_connect("resize_event", _refresh_subplot_spacing)
    return fig


def export_all_mode_figures(
    parsed,
    source_path: Path,
    output_base: Path,
    kmall_name=None,
    correction_file_name=None,
    cal_time=None,
    model_number=None,
):
    model_part = str(model_number).strip() if model_number else "NA"
    timestamp_part = _format_export_timestamp(cal_time)
    export_prefix = f"EM_{model_part}_BS_corr_{timestamp_part}"
    export_dir = output_base.parent / export_prefix
    export_dir.mkdir(parents=True, exist_ok=True)

    for idx, mode_name in enumerate(parsed.keys(), start=1):
        fig = build_mode_figure(
            mode_name,
            parsed[mode_name],
            source_path.name,
            kmall_name,
            correction_file_name,
            cal_time,
            model_number,
        )
        base_stem = output_base.stem
        if base_stem.startswith("BS_corr_"):
            base_stem = base_stem[len("BS_corr_") :]
        if base_stem == "plot":
            base_stem = "mode"
        if not base_stem:
            base_stem = "mode"
        out_name = export_dir / (
            f"{export_prefix}_{base_stem}_{idx}_{_slug(mode_name)}{output_base.suffix or '.png'}"
        )
        fig.savefig(out_name, dpi=150)
        plt.close(fig)
        print(f"Saved plot: {out_name}")

    return export_dir


class BSCorrPlotterWindow(QtWidgets.QMainWindow):
    SETTINGS_ORG = "KJerramTools"
    SETTINGS_APP = "BSCorrPlotter"
    SETTINGS_KEY_OPEN_FOLDER = "open_export_folder"

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"BS Corr Plotter v.{__version__}")
        self.resize(1400, 900)
        _apply_sat_icons(self)

        self.current_file = None
        self.parsed_data = {}
        self.mode_figures = {}
        self.kmall_name = None
        self.correction_file_name = None
        self.cal_time = None
        self.model_number = None
        self.export_base = None

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)

        content_row = QtWidgets.QHBoxLayout()
        button_col = QtWidgets.QVBoxLayout()
        right_col = QtWidgets.QVBoxLayout()
        self.open_btn = QtWidgets.QPushButton("Open BS Corr Text File")
        self.remove_btn = QtWidgets.QPushButton("Remove File")
        self.remove_btn.setEnabled(False)
        self.select_export_btn = QtWidgets.QPushButton("Select Export Location")
        self.select_export_btn.setEnabled(False)
        self.open_export_folder_cb = QtWidgets.QCheckBox("Open export folder")
        self.export_btn = QtWidgets.QPushButton("Export All PNGs")
        self.export_btn.setEnabled(False)
        self.help_btn = QtWidgets.QPushButton("Help")
        self.file_label = QtWidgets.QLabel("No file selected")
        self.file_label.setWordWrap(True)
        button_col.addWidget(self.open_btn)
        button_col.addWidget(self.remove_btn)
        button_col.addWidget(self.export_btn)
        button_col.addWidget(self.select_export_btn)
        button_col.addWidget(self.open_export_folder_cb)
        button_col.addWidget(self.help_btn)
        button_col.addStretch(1)

        self.tabs = QtWidgets.QTabWidget()
        right_col.addWidget(self.file_label)
        right_col.addWidget(self.tabs)
        content_row.addLayout(button_col)
        content_row.addLayout(right_col, stretch=1)
        layout.addLayout(content_row)

        self.open_btn.clicked.connect(self.open_file)
        self.remove_btn.clicked.connect(self.remove_file)
        self.select_export_btn.clicked.connect(self.select_export_location)
        self.export_btn.clicked.connect(self.export_all)
        self.open_export_folder_cb.toggled.connect(self.save_settings)
        self.help_btn.clicked.connect(self.show_help)

        self.load_settings()
        self.show_placeholder_tab()

    def load_settings(self):
        settings = QtCore.QSettings(self.SETTINGS_ORG, self.SETTINGS_APP)
        open_folder = settings.value(self.SETTINGS_KEY_OPEN_FOLDER, True, type=bool)
        self.open_export_folder_cb.setChecked(open_folder)

    def save_settings(self):
        settings = QtCore.QSettings(self.SETTINGS_ORG, self.SETTINGS_APP)
        settings.setValue(self.SETTINGS_KEY_OPEN_FOLDER, self.open_export_folder_cb.isChecked())

    def clear_tabs(self):
        while self.tabs.count() > 0:
            widget = self.tabs.widget(0)
            self.tabs.removeTab(0)
            widget.deleteLater()

    def add_mode_tab(self, tab_name, fig):
        tab = QtWidgets.QWidget()
        tab_layout = QtWidgets.QVBoxLayout(tab)
        canvas = FigureCanvas(fig)
        tab_layout.addWidget(canvas)
        self.tabs.addTab(tab, tab_name)

    def show_placeholder_tab(self):
        self.clear_tabs()
        self.mode_figures = {}

        zero_line = [(-85.0, 0.0), (85.0, 0.0)]
        placeholder_mode_data = {
            0: {0: list(zero_line)},
            1: {0: list(zero_line)},
            2: {0: list(zero_line)},
        }
        placeholder_fig = build_mode_figure(
            "NA",
            placeholder_mode_data,
            "NA",
            kmall_name="NA",
            correction_file_name="NA",
            cal_time="NA",
            model_number="NA",
        )
        self.mode_figures["Placeholder"] = placeholder_fig
        self.add_mode_tab("Placeholder", placeholder_fig)

    def remove_file(self):
        # Release all loaded plotting state and reset UI to empty.
        for fig in self.mode_figures.values():
            plt.close(fig)
        self.current_file = None
        self.parsed_data = {}
        self.mode_figures = {}
        self.kmall_name = None
        self.correction_file_name = None
        self.cal_time = None
        self.model_number = None
        self.export_base = None
        self.file_label.setText("No file selected")
        self.show_placeholder_tab()
        self.export_btn.setEnabled(False)
        self.select_export_btn.setEnabled(False)
        self.remove_btn.setEnabled(False)

    def select_export_location(self):
        if self.current_file is None:
            return

        default_base = self.export_base or (self.current_file.parent / "BS_corr_plot.png")
        fname, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Select Export Base PNG File",
            str(default_base),
            "PNG files (*.png);;All files (*.*)",
        )
        if not fname:
            return

        chosen = Path(fname)
        if chosen.suffix == "":
            chosen = chosen.with_suffix(".png")
        self.export_base = chosen

    def open_file(self):
        fname, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Open BS Corr Text File",
            str(Path.cwd()),
            "Text files (*.txt);;All files (*.*)",
        )
        if not fname:
            return

        path = Path(fname)
        parsed, kmall_name, correction_file_name, cal_time, model_number = parse_swath_sector_file(path)
        if not parsed:
            QtWidgets.QMessageBox.warning(self, "Parse Error", "No depth mode/swath/sector data was parsed.")
            return

        self.current_file = path
        self.parsed_data = parsed
        self.kmall_name = kmall_name
        self.correction_file_name = correction_file_name
        self.cal_time = cal_time
        self.model_number = model_number
        self.mode_figures = {}
        if self.export_base is None:
            self.export_base = path.parent / "BS_corr_plot.png"
        self.file_label.setText(str(path))
        self.clear_tabs()

        for mode_name in parsed.keys():
            fig = build_mode_figure(
                mode_name,
                parsed[mode_name],
                path.name,
                self.kmall_name,
                self.correction_file_name,
                self.cal_time,
                self.model_number,
            )
            self.mode_figures[mode_name] = fig

            self.add_mode_tab(mode_name, fig)

        self.export_btn.setEnabled(True)
        self.select_export_btn.setEnabled(True)
        self.remove_btn.setEnabled(True)

    def export_all(self):
        if not self.current_file or not self.parsed_data:
            return

        base = self.export_base or (self.current_file.parent / "BS_corr_plot.png")
        out_dir = export_all_mode_figures(
            self.parsed_data,
            self.current_file,
            base,
            self.kmall_name,
            self.correction_file_name,
            self.cal_time,
            self.model_number,
        )
        if self.open_export_folder_cb.isChecked():
            try:
                os.startfile(out_dir)
            except OSError as exc:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Open Folder Failed",
                    f"Export completed, but could not open folder:\n{out_dir}\n\n{exc}",
                )
        QtWidgets.QMessageBox.information(self, "Export Complete", f"Exported PNGs to:\n{out_dir}")

    def show_help(self):
        help_text = (
            "The BS Corr Plotter helps to visualize backscatter calibration values applied in a .kmall file.\n\n"
            "To export backscatter calibration data for plotting:\n\n"
            "1. Load a .kmall file into Kongsberg Record Viewer\n"
            "   a. Record Viewer is available at "
            "<a href=\"https://www.kongsbergdiscovery.net/sis/sw.htm\">https://www.kongsbergdiscovery.net/sis/sw.htm</a>\n"
            "2. Select the 'Grouped' tab\n"
            "3. Select the 'Backscatter calibration #FCF' record type\n"
            "4. Highlight the #FCF datagram time of interest (e.g., first in file)\n"
            "5. Click 'Export to:' and 'TXT' in the upper right\n"
            "6. Save the text file\n\n"
            "This Record Viewer .txt export is the desired format for this plotter, as direct .kmall support is not yet available.\n\n"
            "License:\n"
            "This software is released for general use under the BSD 3-Clause License.\n"
            "See BSD-3-Clause-UNH-CCOM-JHC.txt for full terms."
        )
        help_text_html = help_text.replace("\n", "<br>")

        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Help")
        dialog.resize(820, 520)

        layout = QtWidgets.QVBoxLayout(dialog)
        text_label = QtWidgets.QLabel(help_text_html)
        text_label.setTextFormat(QtCore.Qt.TextFormat.RichText)
        text_label.setWordWrap(True)
        text_label.setOpenExternalLinks(True)
        text_label.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextBrowserInteraction)
        text_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop | QtCore.Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(text_label)

        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(dialog.accept)
        layout.addWidget(buttons)

        dialog.exec()


def run_gui():
    app = QtWidgets.QApplication(sys.argv)
    win = BSCorrPlotterWindow()
    win.show()
    sys.exit(app.exec())


def run_cli(file_path: Path, output_base: Path):
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    parsed, kmall_name, correction_file_name, cal_time, model_number = parse_swath_sector_file(file_path)
    if not parsed:
        raise ValueError("No depth mode/swath/sector data was parsed.")
    _ = kmall_name
    export_all_mode_figures(
        parsed, file_path, output_base, kmall_name, correction_file_name, cal_time, model_number
    )


def main():
    parser = argparse.ArgumentParser(description="BS correction plotter (GUI + CLI)")
    parser.add_argument("file", nargs="?", help="Optional input text file (CLI mode)")
    parser.add_argument("--output", default="BS_corr_plot.png", help="Base output PNG path (CLI mode)")
    parser.add_argument("--gui", action="store_true", help="Force GUI mode")
    args = parser.parse_args()

    if args.gui or not args.file:
        run_gui()
        return

    run_cli(Path(args.file), Path(args.output))


if __name__ == "__main__":
    main()
