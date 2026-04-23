import pygame
import requests
import json
import os
import time
import threading
from pathlib import Path
from urllib.parse import quote

# --- 1. SETTINGS & COLORS ---
with open('config.json') as f:
    config = json.load(f)

BASE_URL = config['romm_url'].rstrip('/') + '/api'
AUTH = (config['username'], config['password'])
RETROBAT_ROOT = Path(config['retrobat_root'])

COLORS = {
    "bg": (20, 20, 25),
    "panel": (40, 40, 50),
    "text": (240, 240, 240),
    "accent": (0, 150, 255),
    "success": (50, 200, 50),
    "error": (255, 50, 50)
}

# --- 2. THE UI ENGINE ---
class RommDropGUI:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((1280, 720))
        pygame.display.set_caption("RomM Drop: Arcade Edition")
        self.clock = pygame.time.Clock()
        self.font_main = pygame.font.SysFont("Arial", 32)
        self.font_small = pygame.font.SysFont("Arial", 22)
        
        # Controller Setup
        pygame.joystick.init()
        self.joystick = None
        if pygame.joystick.get_count() > 0:
            self.joystick = pygame.joystick.Joystick(0)
            self.joystick.init()

        # State Management
        self.query = ""
        self.results = []
        self.selected_index = 0
        self.status_msg = "Type to search..."
        self.is_downloading = False
        self.progress = 0
        self.running = True

    def draw(self):
        self.screen.fill(COLORS["bg"])
        
        # Header
        title = self.font_main.render("🎮 RomM Drop", True, COLORS["accent"])
        self.screen.blit(title, (50, 30))
        
        # Search Box
        pygame.draw.rect(self.screen, COLORS["panel"], (50, 80, 1180, 60), border_radius=10)
        search_txt = self.font_main.render(f"🔍 {self.query}|", True, COLORS["text"])
        self.screen.blit(search_txt, (70, 92))

        # Result List
        for i, res in enumerate(self.results):
            y = 160 + (i * 50)
            color = COLORS["accent"] if i == self.selected_index else COLORS["panel"]
            pygame.draw.rect(self.screen, color, (50, y, 1180, 45), border_radius=5)
            
            name = self.font_small.render(f"{res['name']} [{res.get('platform_display_name')}]", True, COLORS["text"])
            self.screen.blit(name, (70, y + 10))

        # Status Bar / Progress
        if self.is_downloading:
            pygame.draw.rect(self.screen, COLORS["panel"], (50, 650, 1180, 30), border_radius=15)
            pygame.draw.rect(self.screen, COLORS["success"], (50, 650, 1180 * self.progress, 30), border_radius=15)
        else:
            status = self.font_small.render(self.status_msg, True, COLORS["text"])
            self.screen.blit(status, (50, 650))

        pygame.display.flip()

    def handle_search(self):
        self.status_msg = f"Searching for '{self.query}'..."
        try:
            params = {'search_term': self.query, 'limit': 10}
            r = requests.get(f"{BASE_URL}/roms", auth=AUTH, params=params, timeout=5)
            if r.status_code == 200:
                self.results = r.json().get('items', [])
                self.status_msg = f"Found {len(self.results)} matches."
            else:
                self.status_msg = "Search failed."
        except:
            self.status_msg = "Connection error."

    def start_download(self):
        if not self.results: return
        game = self.results[self.selected_index]
        self.is_downloading = True
        self.progress = 0
        # Run download in a background thread so UI doesn't freeze
        threading.Thread(target=self.download_worker, args=(game,), daemon=True).start()

    def download_worker(self, game):
        try:
            folder = game.get('platform_fs_slug', 'downloads')
            file_info = game.get('files', [{}])[0]
            filename = file_info.get('file_name', 'game.bin')
            
            save_path = RETROBAT_ROOT / folder / filename
            save_path.parent.mkdir(parents=True, exist_ok=True)

            dl_url = f"{BASE_URL}/roms/{game['id']}/content/{quote(filename)}"
            
            with requests.get(dl_url, auth=AUTH, stream=True) as r:
                total_size = int(r.headers.get('content-length', 0))
                dl_size = 0
                with open(save_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                        dl_size += len(chunk)
                        if total_size > 0:
                            self.progress = dl_size / total_size
            
            self.status_msg = f"✅ Success: {filename}"
        except Exception as e:
            self.status_msg = f"❌ Error: {str(e)}"
        
        self.is_downloading = False

    def run(self):
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                
                # --- KEYBOARD INPUT ---
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_BACKSPACE:
                        self.query = self.query[:-1]
                    elif event.key == pygame.K_RETURN:
                        if self.query: self.handle_search()
                    elif event.key == pygame.K_UP:
                        self.selected_index = max(0, self.selected_index - 1)
                    elif event.key == pygame.K_DOWN:
                        self.selected_index = min(len(self.results)-1, self.selected_index + 1)
                    elif event.key == pygame.K_SPACE:
                        self.start_download()
                    else:
                        self.query += event.unicode

                # --- CONTROLLER INPUT (Joystick) ---
                if event.type == pygame.JOYBUTTONDOWN:
                    if event.button == 0: # A Button (Xbox)
                        self.start_download()
                    if event.button == 1: # B Button
                        self.results = []
                        self.query = ""

                if event.type == pygame.JOYHATMOTION:
                    # D-Pad Up/Down
                    if event.value[1] == 1:
                        self.selected_index = max(0, self.selected_index - 1)
                    if event.value[1] == -1:
                        self.selected_index = min(len(self.results)-1, self.selected_index + 1)

            self.draw()
            self.clock.tick(60)
        pygame.quit()

if __name__ == "__main__":
    app = RommDropGUI()
    app.run()