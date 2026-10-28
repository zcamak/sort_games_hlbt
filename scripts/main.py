"""
Main application logic for sort_games_hlbt.
Supports both Desktop Window mode (via pywebview) and CLI mode.
"""

import os
import sys
import json
import webbrowser
from typing import List, Dict, Any, Optional

import webview

if getattr(sys, "frozen", False):
    BUNDLE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    UI_DIR = os.path.join(BUNDLE_DIR, "ui")
    PROJECT_ROOT = os.path.dirname(sys.executable)
else:
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    UI_DIR = os.path.join(PROJECT_ROOT, "ui")

HTML_DIR = os.path.join(PROJECT_ROOT, "html")
os.makedirs(HTML_DIR, exist_ok=True)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    from scripts.parser import parse_games_file
    from scripts.hltb_service import HLTBService
except ImportError:
    from parser import parse_games_file
    from hltb_service import HLTBService


def build_standalone_html(games: List[Dict[str, Any]], output_path: str) -> str:
    """
    Builds a completely self-contained, standalone HTML file with inlined CSS,
    JavaScript, and preloaded game data.
    """
    with open(os.path.join(UI_DIR, "index.html"), "r", encoding="utf-8") as f:
        html_content = f.read()

    with open(os.path.join(UI_DIR, "style.css"), "r", encoding="utf-8") as f:
        css_content = f.read()

    with open(os.path.join(UI_DIR, "app.js"), "r", encoding="utf-8") as f:
        js_content = f.read()

    # Inline CSS
    html_content = html_content.replace(
        '<link rel="stylesheet" href="style.css">',
        f'<style>\n{css_content}\n</style>'
    )

    # Pre-inject data and inline JS
    serialized_games = json.dumps(games, ensure_ascii=False)
    inlined_script = (
        f'<script>\n'
        f'  window.PRELOADED_GAMES = {serialized_games};\n'
        f'  {js_content}\n'
        f'</script>'
    )
    html_content = html_content.replace(
        '<script src="app.js"></script>',
        inlined_script
    )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    return output_path


class AppApi:
    """
    API exposed to JavaScript inside pywebview.
    """
    def __init__(self, service: HLTBService):
        self.service = service
        self._window: Optional[webview.Window] = None
        self.current_games: List[Dict[str, Any]] = []

    def set_window(self, window: webview.Window):
        self._window = window

    def select_file(self) -> Dict[str, Any]:
        """
        Pops open a native file dialog to select a text file,
        then fetches games from HowLongToBeat with real-time UI updates.
        """
        if not self._window:
            return {"error": "Window not initialized"}

        file_types = ("Text Files (*.txt)", "All files (*.*)")
        selected = self._window.create_file_dialog(
            webview.OPEN_DIALOG,
            allow_multiple=False,
            file_types=file_types
        )

        if not selected or len(selected) == 0:
            return {"cancelled": True}

        file_path = selected[0]
        if not os.path.exists(file_path):
            return {"error": "File does not exist"}

        games_to_fetch = parse_games_file(file_path)
        if not games_to_fetch:
            return {"error": "No valid game entries found in file", "games": []}

        def on_progress(current: int, tot: int, game_data: Dict[str, Any]):
            name = game_data.get("game_name") or game_data.get("user_title") or ""
            safe_name = json.dumps(name)
            if self._window:
                self._window.evaluate_js(f"window.updateProgress({current}, {tot}, {safe_name});")

        processed = self.service.fetch_games_list(games_to_fetch, progress_callback=on_progress)
        self.current_games = processed
        return {"success": True, "games": processed, "filepath": file_path}

    def export_html(self, games: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Exports the current games table to a standalone HTML file.
        """
        games_to_export = games or self.current_games
        if not games_to_export:
            return {"error": "No games data to export"}

        default_name = "games.html"
        output_path = os.path.join(HTML_DIR, default_name)

        if self._window:
            file_types = ("HTML Files (*.html)", "All files (*.*)")
            save_path = self._window.create_file_dialog(
                webview.SAVE_DIALOG,
                directory=HTML_DIR,
                save_filename=default_name,
                file_types=file_types
            )
            if save_path:
                output_path = save_path if isinstance(save_path, str) else save_path[0]

        build_standalone_html(games_to_export, output_path)
        return {"success": True, "path": output_path}


def run_cli(file_path: str):
    """
    Headless CLI execution: parses file, queries HLTB, creates html/games.html, and opens browser.
    """
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        sys.exit(1)

    print(f"Parsing '{file_path}'...")
    games = parse_games_file(file_path)
    if not games:
        print("No games found in file.")
        sys.exit(1)

    print(f"Found {len(games)} games. Fetching data from HowLongToBeat...")
    service = HLTBService()

    def progress(cur, tot, data):
        name = data.get("game_name") or data.get("user_title")
        extra = data.get("main_extra", {}).get("display", "--")
        print(f"[{cur}/{tot}] {name} (Main+Extra: {extra})")

    results = service.fetch_games_list(games, progress_callback=progress)

    output_html = os.path.join(HTML_DIR, "games.html")
    build_standalone_html(results, output_html)
    print(f"\nReport generated successfully: {output_html}")
    webbrowser.open(f"file://{os.path.abspath(output_html)}")


def main():
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        run_cli(sys.argv[1])
        return

    service = HLTBService()
    api = AppApi(service)

    html_file = os.path.join(UI_DIR, "index.html")

    window = webview.create_window(
        title="Game Backlog Sorter (HowLongToBeat)",
        url=html_file,
        js_api=api,
        width=1100,
        height=750,
        min_size=(750, 500),
        background_color="#0b0f17"
    )
    api.set_window(window)

    webview.start()


if __name__ == "__main__":
    main()
