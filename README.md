# BS Corr Plotter

![BS Corr Plotter Overview](build/BS_corr_plotter/media/BS%20Corr%20Plotter%20example.png)
*BS Corr Plotter overview*
Example backscatter calibration values for each swath in Deeper mode.

BS Corr Plotter is a PyQt6 + Matplotlib desktop app for visualizing Kongsberg backscatter calibration (`#FCF`) data exported from Record Viewer text files.

## Features

- Parse Record Viewer TXT exports containing calibration tables by mode/swath/TX sector.
- Display one tab per depth mode with synchronized subplot axes.
- Export all mode plots to PNG files with metadata-aware naming.
- GUI and CLI entry points in a single script.
- Built-in help dialog with clickable Record Viewer download link.

## Requirements

- Python 3.10+ (tested in local environment with Python 3.14)
- `PyQt6`
- `matplotlib`

## Run (GUI)

From this folder:

```bash
python BS_corr_plotter.py
```

Or force GUI mode:

```bash
python BS_corr_plotter.py --gui
```

## Run (CLI Export)

```bash
python BS_corr_plotter.py "path\to\record_viewer_export.txt" --output "BS_corr_plot.png"
```

This exports one PNG per parsed mode into an output folder named like:

`EM_<model>_BS_corr_<timestamp>`

## Build Executable

Use the included batch script from this folder:

```bat
build_exe.bat
```

The script:

- installs PyInstaller if needed
- builds from `BS_corr_plotter.spec`
- outputs executable to `dist\`

Expected output name:

`BS_corr_plotter_v<version>.exe`  
(version comes from `__version__` in `BS_corr_plotter.py`)

## Project Files

- `BS_corr_plotter.py` - main application (GUI + CLI)
- `BS_corr_plotter.spec` - PyInstaller spec
- `build_exe.bat` - Windows build script
- `BSD-3-Clause-UNH-CCOM-JHC.txt` - license text used by the app

## Input Data Notes

Use Kongsberg Record Viewer TXT export for `Backscatter calibration #FCF` records.

Record Viewer download page:  
[https://www.kongsbergdiscovery.net/sis/sw.htm](https://www.kongsbergdiscovery.net/sis/sw.htm)

## License

BSD 3-Clause License.  
See `BSD-3-Clause-UNH-CCOM-JHC.txt`.
