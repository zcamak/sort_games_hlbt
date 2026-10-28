# Sort Games by HowLongToBeat

This application reads a text file containing a list of games. It retrieves playtime data and cover art from [HowLongToBeat.com](https://howlongtobeat.com/) and displays the results in an interactive table.

---

## Features

- Retrieves completion times: Main Story, Main + Extra, and Completionist.
- Formats playtime in hours and minutes (for example: `3h 15m`, `5h`, `55m`).
- Sorts games by Main + Extra playtime by default (shortest to longest).
- Interactive table: sort by any column, filter by text, and search by year.
- Caches data locally to reduce network requests.
- Exports a standalone HTML report.

---

## Input File Format

Create a text file (`.txt`) with one game per line. Put the title first and the 4-digit release year at the end:

```text
Ad Infinitum 2023
Adios 2021
Agony 2018
Amnesia: The Bunker 2023
Apsulov: End of Gods 2019
```

Lines with trailing spaces or blank lines are ignored. If you omit the release year, the application searches by title only.

### Exporting from Playnite

You can export a list of games directly from [Playnite](https://playnite.link/) ([GitHub](https://github.com/JosefNemec/Playnite)):

1. Open Playnite.
2. Select **Main menu > Extensions > Interactive SDK PowerShell**.
3. Run the export script:
   ```powershell
   . .\examples\export_games_with_tags_ex.ps1 -Tags "Horror" -OutputFile "$HOME\Documents\games_list.txt"
   ```
4. The script exports unplayed games in the required `Title ReleaseYear` format. You can adjust tag filters and the output path in the command.

---

## Installation

### Prerequisites

- Windows 10 or Windows 11
- Python 3.10 or newer

### Setup Steps

1. Clone the repository:
   ```bash
   git clone https://github.com/zcamak/sort_games_hlbt.git
   cd sort_games_hlbt
   ```

2. Create and activate a Python virtual environment:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. Install required packages:
   ```powershell
   pip install -r requirements.txt
   ```

---

## Usage

### 1. Run the Desktop Application

Run the application with Python:

```powershell
python scripts/main.py
```

1. Click **Load games list**.
2. Select your games text file (for example: `examples/games_list_with_tags_ex.txt`).
3. Click column headers to change sort order.
4. Click **Export HTML** to save a standalone report to `html/games.html`.

### 2. Run in Command-Line Mode

You can process a file directly from the terminal:

```powershell
python scripts/main.py examples/games_list_with_tags_ex.txt
```

This generates `html/games.html` and opens it in your default web browser.

### 3. Build the Standalone Executable

To create a standalone `.exe` that runs without a Python installation:

- **Using PowerShell**:
  ```powershell
  powershell -ExecutionPolicy Bypass -File build\build_exe.ps1
  ```
- **Or double-click**: `build\build_exe.bat` in Windows Explorer.

The build script compiles `app\GameSorter.exe`.

### 4. Run the Standalone Executable

After you build the application, run:

```text
app\GameSorter.exe
```

---

## Cache

Retrieved data is stored in `app/cache.json`. Delete this file if you want to refresh all game data from HowLongToBeat.

---

## License

This project is licensed under the [MIT License](LICENSE).
