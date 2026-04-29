import pygame
import requests
import json
import os
import threading
from pathlib import Path
from urllib.parse import quote

# --- DYNAMIC PATH DETECTION ---
SCRIPT_DIR = Path(__file__).parent.absolute()
AUTO_ROMS_ROOT = SCRIPT_DIR.parent.parent

CONFIG_PATH = SCRIPT_DIR / 'config.json'
with open(CONFIG_PATH) as f:
    config = json.load(f)

BASE_URL = config['romm_url'].rstrip('/') + '/api'
AUTH = (config['username'], config['password'])

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "X-Requested-With": "XMLHttpRequest"
}

RETROBAT_ROOT = AUTO_ROMS_ROOT

COLORS = {
    "bg": (20, 20, 25), "panel": (40, 40, 50), "text": (240, 240, 240),
    "accent": (0, 150, 255), "success": (50, 200, 50), "error": (255, 50, 50),
    "highlight": (255, 255, 0)
}

KB_LAYOUT = [
    "ABCDEFGHIJ", "KLMNOPQRST", "UVWXYZ1234", "567890._- ",
    ["BACKSPACE", "SEARCH", "CLEAR"]
]

class RommDropGUI:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        self.screen_width, self.screen_height = self.screen.get_size()
        self.clock = pygame.time.Clock()
        self.font_main = pygame.font.SysFont("Arial", 36, bold=True)
        self.font_small = pygame.font.SysFont("Arial", 26)
        self.font_legend = pygame.font.SysFont("Arial", 22, italic=True)

        pygame.joystick.init()
        self.joystick = pygame.joystick.Joystick(0) if pygame.joystick.get_count() > 0 else None
        if self.joystick: self.joystick.init()

        self.state = "PLATFORMS"
        self.search_focus = "keyboard"
        self.cached_platforms = []
        self.items = []
        self.selected_index = 0
        self.scroll_offset = 0
        self.query = ""
        self.kb_x, self.kb_y = 0, 0
        self.status_msg = "Initializing..."
        self.is_downloading = False
        self.progress = 0
        self.running = True

        # Store rects for mouse hit-testing
        self.list_item_rects = []   # [(rect, global_idx), ...]
        self.kb_key_rects = []      # [(rect, char), ...]

        self.fetch_platforms()

    def fetch_platforms(self):
        self.status_msg = "Fetching systems..."
        try:
            r = requests.get(f"{BASE_URL}/platforms", auth=AUTH, headers=HEADERS, timeout=10)
            if r.status_code == 200:
                raw = sorted(r.json(), key=lambda x: x['name'])
                self.cached_platforms = [{"name": "🔍 [ SEARCH / MANUAL ENTRY ]", "type": "SEARCH_MODE"}] + \
                                        [{"name": p['name'], "type": "PLATFORM", "id": p['id'], "slug": p['slug']} for p in raw]
                self.show_platforms()
            else:
                self.status_msg = f"API Error: {r.status_code}"
        except:
            self.status_msg = "Connection Failed"

    def show_platforms(self):
        self.state = "PLATFORMS"
        self.search_focus = "keyboard"
        self.items = self.cached_platforms
        self.selected_index = 0
        self.scroll_offset = 0
        self.status_msg = "Select a System"

    def fetch_games_by_platform(self, p_id, p_name):
        self.status_msg = f"Loading {p_name}..."
        self.items = []
        try:
            params = {'platform_ids': p_id, 'limit': 1000}
            r = requests.get(f"{BASE_URL}/roms", auth=AUTH, params=params, headers=HEADERS, timeout=20)
            if r.status_code == 200:
                raw_games = r.json().get('items', [])
                sorted_games = sorted(raw_games, key=lambda x: x['name'].lower())
                self.items = [{"name": "cd.. [ Back to Systems ]", "type": "BACK_ACTION"}] + \
                             [{"name": g['name'], "type": "GAME", "data": g} for g in sorted_games]
                self.selected_index = 0
                self.scroll_offset = 0
                self.status_msg = f"Found {len(sorted_games)} games in {p_name}."
            else:
                self.status_msg = f"Filter Error: {r.status_code}"
        except:
            self.status_msg = "Server Timeout."

    def draw(self):
        self.screen.fill(COLORS["bg"])
        header_text = f"RomM_Drop | {self.state}"
        if self.state == "SEARCH":
            header_text = f"SEARCH: {self.query}_"
        self.screen.blit(self.font_main.render(header_text, True, COLORS["accent"]), (50, 30))

        list_width = int(self.screen_width * 0.55) if self.state == "SEARCH" else self.screen_width - 100

        # Rebuild list item rects each frame for mouse hit-testing
        self.list_item_rects = []
        for i in range(12):
            idx = self.scroll_offset + i
            if idx >= len(self.items): break
            y = 100 + (i * 45)

            is_active_item = False
            if self.state != "SEARCH" or self.search_focus == "results":
                if idx == self.selected_index:
                    is_active_item = True

            color = COLORS["accent"] if is_active_item else COLORS["panel"]
            rect = pygame.Rect(50, y, list_width, 40)
            pygame.draw.rect(self.screen, color, rect, border_radius=5)
            self.screen.blit(self.font_small.render(self.items[idx]['name'], True, COLORS["text"]), (65, y + 5))
            self.list_item_rects.append((rect, idx))

        if self.state == "SEARCH":
            self.draw_keyboard(list_width + 80)

        bar_y = self.screen_height - 90
        if self.is_downloading:
            pygame.draw.rect(self.screen, COLORS["panel"], (50, bar_y, self.screen_width - 100, 25), border_radius=12)
            pygame.draw.rect(self.screen, COLORS["success"], (50, bar_y, int((self.screen_width - 100) * self.progress), 25), border_radius=12)
        else:
            self.screen.blit(self.font_small.render(self.status_msg, True, COLORS["text"]), (50, bar_y))

        legend_txt = "[A]/Click Select  [B] Back  [X] Backspace  [Y] Search  [LB/RB] Page  [STA+SEL] Exit"
        self.screen.blit(self.font_legend.render(legend_txt, True, (120, 120, 120)), (50, self.screen_height - 40))
        pygame.display.flip()

    def draw_keyboard(self, start_x):
        # Rebuild kb rects each frame for mouse hit-testing
        self.kb_key_rects = []
        for r_idx, row in enumerate(KB_LAYOUT):
            for c_idx, char in enumerate(row):
                y = 100 + (r_idx * 50)
                is_sel = (self.kb_x == c_idx and self.kb_y == r_idx and self.search_focus == "keyboard")
                color = COLORS["highlight"] if is_sel else COLORS["panel"]

                if isinstance(char, str) and len(char) == 1:
                    x = start_x + (c_idx * 45)
                    rect = pygame.Rect(x, y, 40, 40)
                    pygame.draw.rect(self.screen, color, rect, border_radius=5)
                    self.screen.blit(self.font_small.render(char, True, COLORS["text"]), (x + 10, y + 5))
                    self.kb_key_rects.append((rect, char))
                else:
                    btn_w = 125
                    x_wide = start_x + (c_idx * 140)
                    rect = pygame.Rect(x_wide, y, btn_w, 40)
                    pygame.draw.rect(self.screen, color, rect, border_radius=5)
                    text_surf = self.font_small.render(char, True, COLORS["text"])
                    text_x = x_wide + (btn_w // 2) - (text_surf.get_width() // 2)
                    self.screen.blit(text_surf, (text_x, y + 5))
                    self.kb_key_rects.append((rect, char))

    def handle_selection(self):
        if not self.items: return
        item = self.items[self.selected_index]
        if item['type'] == "PLATFORM":
            self.state = "GAMES"
            self.fetch_games_by_platform(item['id'], item['name'])
        elif item['type'] == "SEARCH_MODE":
            self.state = "SEARCH"
            self.search_focus = "keyboard"
            self.items = []
            self.query = ""
            self.status_msg = "Enter a game title..."
        elif item['type'] == "GAME":
            self.start_download(item['data'])
        elif item['type'] == "BACK_ACTION":
            self.show_platforms()

    def handle_kb_char(self, char):
        """Shared logic for typing a KB character, whether from controller or mouse."""
        if len(str(char)) == 1:
            self.query += char
        elif char == "BACKSPACE":
            self.query = self.query[:-1]
        elif char == "SEARCH":
            self.handle_search()
        elif char == "CLEAR":
            self.query = ""

    def handle_search(self):
        if not self.query: return
        self.status_msg = "Searching library..."
        try:
            r = requests.get(f"{BASE_URL}/roms", auth=AUTH, params={'search_term': self.query, 'limit': 100}, headers=HEADERS)
            if r.status_code == 200:
                results = r.json().get('items', [])
                self.items = [{"name": "cd.. [ Clear Search ]", "type": "BACK_ACTION"}] + \
                             [{"name": f"{g['name']} [{g.get('platform_display_name')}]", "type": "GAME", "data": g} for g in results]
                self.selected_index = 1
                self.scroll_offset = 0
                self.search_focus = "results"
                self.status_msg = f"Found {len(results)} matches."
        except:
            self.status_msg = "Search failed."

    def start_download(self, game):
        if self.is_downloading: return
        self.is_downloading = True
        threading.Thread(target=self.download_worker, args=(game,), daemon=True).start()

    def download_worker(self, game):
        try:
            folder = game.get('platform_fs_slug', 'downloads')
            files = game.get('files', [])

            if not files:
                self.status_msg = "No files found for this game."
                self.is_downloading = False
                return

            use_subfolder = len(files) > 1
            game_subfolder = game.get('fs_name') or game.get('name', 'unknown')

            for i, file_entry in enumerate(files):
                filename = file_entry.get('file_name')
                if not filename:
                    continue

                if use_subfolder:
                    save_path = RETROBAT_ROOT / folder / game_subfolder / filename
                else:
                    save_path = RETROBAT_ROOT / folder / filename

                save_path.parent.mkdir(parents=True, exist_ok=True)
                self.status_msg = f"Downloading {i+1}/{len(files)}: {filename}"

                url = f"{BASE_URL}/roms/{game['id']}/content/{quote(filename)}"
                with requests.get(url, auth=AUTH, headers=HEADERS, stream=True) as r:
                    total = int(r.headers.get('content-length', 0))
                    current = 0
                    with open(save_path, 'wb') as f:
                        for chunk in r.iter_content(8192):
                            f.write(chunk)
                            current += len(chunk)
                            if total > 0:
                                self.progress = (i + current / total) / len(files)

            game_label = game.get('name', 'Game')
            self.status_msg = f"DROPPED: {game_label} ({len(files)} file{'s' if len(files) > 1 else ''})"

        except Exception as e:
            self.status_msg = f"Error: {str(e)}"

        self.is_downloading = False

    def handle_mouse_click(self, pos):
        """Check if mouse click hit a list item or keyboard key."""
        # Check list items first
        for rect, idx in self.list_item_rects:
            if rect.collidepoint(pos):
                self.selected_index = idx
                self.handle_selection()
                return

        # Check on-screen keyboard keys (only visible in SEARCH state)
        if self.state == "SEARCH":
            for rect, char in self.kb_key_rects:
                if rect.collidepoint(pos):
                    self.search_focus = "keyboard"
                    self.handle_kb_char(char)
                    return

    def handle_mouse_scroll(self, direction):
        """Scroll the list up (-1) or down (+1) with the mouse wheel."""
        if not self.items: return
        self.selected_index = max(0, min(len(self.items) - 1, self.selected_index + direction))
        if self.selected_index < self.scroll_offset:
            self.scroll_offset = self.selected_index
        elif self.selected_index >= self.scroll_offset + 12:
            self.scroll_offset = self.selected_index - 11

    def run(self):
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False

                # --- MOUSE EVENTS ---
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:   # Left click
                        self.handle_mouse_click(event.pos)
                    elif event.button == 4: # Scroll wheel up
                        self.handle_mouse_scroll(-1)
                    elif event.button == 5: # Scroll wheel down
                        self.handle_mouse_scroll(1)

                # --- PHYSICAL KEYBOARD EVENTS ---
                if event.type == pygame.KEYDOWN:
                    if self.state == "SEARCH":
                        if event.key == pygame.K_ESCAPE:
                            self.show_platforms()
                        elif event.key == pygame.K_RETURN:
                            self.handle_search()
                        elif event.key == pygame.K_BACKSPACE:
                            self.query = self.query[:-1]
                        else:
                            # Accept printable characters
                            char = event.unicode
                            if char and char.isprintable():
                                self.query += char.upper()
                    else:
                        if event.key == pygame.K_ESCAPE:
                            self.show_platforms()
                        elif event.key == pygame.K_RETURN:
                            self.handle_selection()
                        elif event.key == pygame.K_UP:
                            self.selected_index = max(0, self.selected_index - 1)
                        elif event.key == pygame.K_DOWN:
                            self.selected_index = min(len(self.items) - 1, self.selected_index + 1)
                        elif event.key == pygame.K_PAGEUP:
                            self.selected_index = max(0, self.selected_index - 10)
                        elif event.key == pygame.K_PAGEDOWN:
                            self.selected_index = min(len(self.items) - 1, self.selected_index + 10)

                # --- CONTROLLER EVENTS ---
                if event.type == pygame.JOYBUTTONDOWN:
                    if self.joystick and self.joystick.get_button(6) and self.joystick.get_button(7):
                        self.running = False

                    if event.button == 0:  # A Button
                        if self.state == "SEARCH" and self.search_focus == "keyboard":
                            row = KB_LAYOUT[self.kb_y]
                            char = row[self.kb_x]
                            self.handle_kb_char(char)
                        else:
                            self.handle_selection()

                    if event.button == 1:  # B Button
                        if self.state != "PLATFORMS":
                            self.show_platforms()

                    if event.button == 2:  # X Button
                        if self.state == "SEARCH" and self.search_focus == "keyboard":
                            self.query = self.query[:-1]

                    if event.button == 3:  # Y Button
                        self.state = "SEARCH"
                        self.search_focus = "keyboard"
                        self.items = []
                        self.query = ""

                    if event.button == 4:
                        self.selected_index = max(0, self.selected_index - 10)
                    if event.button == 5:
                        self.selected_index = min(len(self.items) - 1, self.selected_index + 10)

                if event.type == pygame.JOYHATMOTION:
                    dx, dy = event.value
                    if self.state == "SEARCH" and self.search_focus == "keyboard":
                        if dx != 0:
                            self.kb_x = (self.kb_x + dx) % len(KB_LAYOUT[self.kb_y])
                        if dy != 0:
                            self.kb_y = (self.kb_y - dy) % len(KB_LAYOUT)
                            self.kb_x = min(self.kb_x, len(KB_LAYOUT[self.kb_y]) - 1)
                    else:
                        if dy != 0:
                            self.selected_index = max(0, min(len(self.items) - 1, self.selected_index - dy))

                # Keep scroll window tracking selected item (controller + keyboard nav)
                if self.selected_index < self.scroll_offset:
                    self.scroll_offset = self.selected_index
                elif self.selected_index >= self.scroll_offset + 12:
                    self.scroll_offset = self.selected_index - 11

            self.draw()
            self.clock.tick(60)
        pygame.quit()

if __name__ == "__main__":
    app = RommDropGUI()
    app.run()