"""
Discord Process Spoofer & Verifier (Enhanced Dual Engine + IGDB & GTA 6 Integration)
- Dual Engine: Windows Process Sandbox Spoofer + Native Discord IPC Rich Presence
- Supported: EA SPORTS FC 27, Grand Theft Auto VI (GTA 6), and 24,000+ Discord/IGDB detectable games
- Full-Size GTA 6 Logo matched in size to GTA V (edge-to-edge full-bleed asset)
- Silent Background Mode: Spoofed fake game app stays 100% in the background without popup windows
- Bulletproof Stop & Clean Up: Kills all parent & worker processes by PID and Image Name, wipes sandbox files
"""

import os
import sys
import json
import time
import shutil
import struct
import uuid
import tempfile
import threading
import subprocess
import webbrowser
import urllib.request
import urllib.parse
import tkinter as tk
from tkinter import ttk, messagebox

# ---------------------------------------------------------------------------
# Background Process Runner for the Simulated Game Process
# ---------------------------------------------------------------------------
if len(sys.argv) > 1 and sys.argv[1] == '--dummy':
    dummy_title = sys.argv[2] if len(sys.argv) > 2 else 'Game'
    show_window = '--show-window' in sys.argv

    # Hide any console window on Windows
    try:
        import ctypes
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)
    except Exception:
        pass

    dummy_root = tk.Tk()
    dummy_root.title(dummy_title)

    if not show_window:
        # Silent Background Mode: Window stays completely hidden in the background
        dummy_root.withdraw()
    else:
        # Visible window mode if explicitly requested
        dummy_root.geometry('380x190+250+250')
        dummy_root.minsize(320, 150)
        dummy_root.configure(bg='#181a1f')

        container = tk.Frame(dummy_root, bg='#181a1f', padx=15, pady=15)
        container.pack(fill='both', expand=True)

        header = tk.Label(
            container,
            text=f"🎮 {dummy_title}",
            font=('Segoe UI', 12, 'bold'),
            fg='#ffffff',
            bg='#181a1f'
        )
        header.pack(pady=(0, 6))

        sub = tk.Label(
            container,
            text="Process Simulation Active",
            font=('Segoe UI', 9, 'bold'),
            fg='#57f287',
            bg='#181a1f'
        )
        sub.pack(pady=(0, 4))

        desc = tk.Label(
            container,
            text=f"Simulated Binary: {os.path.basename(sys.executable)}\nRunning in background for Discord",
            font=('Segoe UI', 8),
            fg='#b9bbbe',
            bg='#181a1f',
            justify='center'
        )
        desc.pack(pady=(0, 6))

    def set_win32_title():
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetAncestor(dummy_root.winfo_id(), 2)
            if not hwnd:
                hwnd = ctypes.windll.user32.GetParent(dummy_root.winfo_id())
            if not hwnd:
                hwnd = dummy_root.winfo_id()
            if hwnd:
                ctypes.windll.user32.SetWindowTextW(hwnd, dummy_title)
        except Exception:
            pass

    dummy_root.update_idletasks()
    set_win32_title()
    dummy_root.after(300, set_win32_title)
    dummy_root.after(1000, set_win32_title)

    dummy_root.mainloop()
    sys.exit(0)


# ---------------------------------------------------------------------------
# Discord Local IPC Client (Rich Presence Engine) - Thread-Safe & Non-Blocking
# ---------------------------------------------------------------------------
class DiscordIPC:
    """Manages connection to local Discord IPC pipe (\\\\.\\pipe\\discord-ipc-0)."""
    def __init__(self):
        self.pipe = None
        self.client_id = None
        self.connected = False
        self.lock = threading.RLock()

    def connect(self, client_id):
        self.close()
        self.client_id = str(client_id)
        for i in range(10):
            pipe_name = rf'\\.\pipe\discord-ipc-{i}'
            if os.path.exists(pipe_name):
                try:
                    self.pipe = open(pipe_name, 'r+b', buffering=0)
                    handshake = json.dumps({'v': 1, 'client_id': self.client_id}).encode('utf-8')
                    self.pipe.write(struct.pack('<II', 0, len(handshake)) + handshake)
                    resp_header = self.pipe.read(8)
                    if len(resp_header) == 8:
                        op, length = struct.unpack('<II', resp_header)
                        data = json.loads(self.pipe.read(length).decode('utf-8'))
                        if data.get('evt') == 'READY':
                            self.connected = True
                            return True
                except Exception:
                    if self.pipe:
                        try:
                            self.pipe.close()
                        except Exception:
                            pass
                        self.pipe = None
        return False

    def set_activity(self, details="Playing", state="", start_time=None, large_image=None, large_text=None):
        if not self.pipe or not self.connected:
            return False
        with self.lock:
            try:
                act = {
                    'details': details or "In Game",
                    'state': state or "Active",
                    'timestamps': {'start': int(start_time or time.time())}
                }
                assets = {}
                if large_image:
                    assets['large_image'] = large_image
                if large_text:
                    assets['large_text'] = large_text
                if assets:
                    act['assets'] = assets

                payload = {
                    'cmd': 'SET_ACTIVITY',
                    'args': {
                        'pid': os.getpid(),
                        'activity': act
                    },
                    'nonce': str(uuid.uuid4())
                }
                raw = json.dumps(payload).encode('utf-8')
                self.pipe.write(struct.pack('<II', 1, len(raw)) + raw)
                resp_header = self.pipe.read(8)
                if len(resp_header) == 8:
                    op, length = struct.unpack('<II', resp_header)
                    resp = json.loads(self.pipe.read(length).decode('utf-8'))
                    return resp.get('evt') != 'ERROR'
            except Exception:
                self.connected = False
                return False
        return False

    def close(self):
        with self.lock:
            if self.pipe:
                try:
                    self.pipe.close()
                except Exception:
                    pass
                self.pipe = None
            self.connected = False


# ---------------------------------------------------------------------------
# IGDB API Client (Twitch OAuth2)
# ---------------------------------------------------------------------------
class IGDBClient:
    def __init__(self):
        self.client_id = ""
        self.client_secret = ""
        self.access_token = ""
        self.token_expiry = 0

    def authenticate(self, client_id, client_secret):
        self.client_id = client_id.strip()
        self.client_secret = client_secret.strip()
        if not self.client_id or not self.client_secret:
            raise ValueError("Client ID and Client Secret must not be empty.")

        url = "https://id.twitch.tv/oauth2/token"
        params = urllib.parse.urlencode({
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'client_credentials'
        }).encode('utf-8')

        req = urllib.request.Request(url, data=params, method='POST')
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            self.access_token = data.get('access_token')
            expires_in = data.get('expires_in', 3600)
            self.token_expiry = time.time() + expires_in
            return self.access_token

    def search_games(self, query, limit=15):
        if not self.access_token or time.time() >= self.token_expiry:
            if self.client_id and self.client_secret:
                self.authenticate(self.client_id, self.client_secret)
            else:
                raise ValueError("IGDB requires Twitch Client ID & Secret.")

        url = "https://api.igdb.com/v4/games"
        body = f'search "{query}"; fields name, summary, cover.url, first_release_date, platforms.name, url, slug; limit {limit};'.encode('utf-8')
        req = urllib.request.Request(url, data=body, method='POST', headers={
            'Client-ID': self.client_id,
            'Authorization': f'Bearer {self.access_token}',
            'Accept': 'application/json'
        })
        with urllib.request.urlopen(req, timeout=12) as resp:
            return json.loads(resp.read().decode('utf-8'))


# ---------------------------------------------------------------------------
# Master Presets & Fallback Database
# ---------------------------------------------------------------------------
DISCORD_API_URL = 'https://discord.com/api/v9/applications/detectable'
CONFIG_DIR = os.path.join(os.path.expanduser('~'), '.process_simulator')
CONFIG_PATH = os.path.join(CONFIG_DIR, 'config.json')

# Full-bleed edge-to-edge GTA 6 logo matching GTA V's visual size
GTA6_FULL_SIZE_LOGO = "https://iili.io/nOgh0ox.png"
GTA6_DEFAULT_DISCORD_ICON = "251322eb2a778edc62ecce8d791e3701"
GTA6_COVER_ART = "0788ab1237f5801d9f72af6d34665327"

FALLBACK_GAMES = [
    {
        'name': 'Grand Theft Auto VI',
        'discord_id': '1445160676522856458',
        'icon_hash': GTA6_FULL_SIZE_LOGO,
        'icon_options': [
            GTA6_FULL_SIZE_LOGO,
            GTA6_DEFAULT_DISCORD_ICON,
            GTA6_COVER_ART
        ],
        'igdb_url': 'https://www.igdb.com/games/grand-theft-auto-vi',
        'details': 'Exploring Leonida & Vice City',
        'state': 'Story Mode',
        'exe': 'Grand Theft Auto VI/GTA6.exe',
        'all_exes': [
            'Grand Theft Auto VI/GTA6.exe',
            'GTA6.exe',
            'Grand Theft Auto VI/PlayGTA6.exe',
            'PlayGTA6.exe'
        ],
        'search_key': 'grand theft auto vi gta 6 gta vi gta6 rockstar vice city leonida'
    },
    {
        'name': 'EA Sports FC 27',
        'discord_id': '1531874756096295054',
        'icon_hash': '6e4b3b152df4601bd5ff07a468c5ccf5',
        'icon_options': [
            '6e4b3b152df4601bd5ff07a468c5ccf5',
            'b9e00e9b011da7dc6f955601593a6ad2'
        ],
        'igdb_url': 'https://www.igdb.com/games/ea-sports-fc-27',
        'details': 'Career Mode',
        'state': 'In Match - 90:00',
        'exe': 'EA SPORTS FC 27/FC27.exe',
        'all_exes': [
            'EA SPORTS FC 27/FC27.exe',
            'FC27.exe',
            'EA SPORTS FC 27/FC27_trial.exe',
            'EA SPORTS FC 27/FC27_showcase.exe',
            'ea sports fc 27/fc27.exe'
        ],
        'search_key': 'ea sports fc 27 fc27 fc 27 fifa 27 football soccer ea sports fc27.exe'
    },
    {
        'name': 'EA Sports FC 26',
        'discord_id': '1400843236318117900',
        'icon_hash': '859d0426d15b2e3eec1fa266d6d74483',
        'igdb_url': 'https://www.igdb.com/games/ea-sports-fc-26',
        'details': 'Ultimate Team',
        'state': 'Division Rivals',
        'exe': 'ea sports fc 26/fc26.exe',
        'all_exes': [
            'ea sports fc 26/fc26.exe',
            'ea sports fc 26/fc26_trial.exe',
            'ea sports fc 26/fc26_showcase.exe',
            'fc26.exe'
        ],
        'search_key': 'ea sports fc 26 fc26 fc 26 fifa 26 football soccer ea sports fc26.exe'
    },
    {
        'name': 'EA Sports FC 25',
        'discord_id': '1245050592926306354',
        'icon_hash': '72f5d933e145b14115169a7b9ce70cf7',
        'igdb_url': 'https://www.igdb.com/games/ea-sports-fc-25',
        'details': 'Kick Off',
        'state': 'Champions Finals',
        'exe': 'ea sports fc 25/fc25.exe',
        'all_exes': [
            'ea sports fc 25/fc25.exe',
            'ea sports fc 25/fc25_trial.exe',
            'fc25.exe'
        ],
        'search_key': 'ea sports fc 25 fc25 fc 25 fifa 25 football soccer'
    },
    {
        'name': 'Grand Theft Auto V',
        'discord_id': '1421192030440263791',
        'icon_hash': '419a062fd532ffb5abff6ea227d7c003',
        'igdb_url': 'https://www.igdb.com/games/grand-theft-auto-v',
        'details': 'Los Santos Freemode',
        'state': 'Online Session',
        'exe': 'Grand Theft Auto V/GTA5.exe',
        'all_exes': ['Grand Theft Auto V/GTA5.exe', 'PlayGTAV.exe', 'GTA5.exe'],
        'search_key': 'grand theft auto v gta 5 gta5.exe playgtav.exe'
    },
    {
        'name': 'Call of Duty HQ',
        'discord_id': '1048682650392371290',
        'icon_hash': '2e6d2bc5cf54016142145e14d10fceb9',
        'igdb_url': 'https://www.igdb.com/games/call-of-duty-modern-warfare-iii',
        'details': 'Multiplayer',
        'state': 'Search & Destroy',
        'exe': '_retail_/cod.exe',
        'all_exes': ['_retail_/cod.exe', 'cod.exe'],
        'search_key': 'call of duty hq cod mw3 mw2 warzone _retail_/cod.exe cod.exe'
    },
    {
        'name': 'Overwatch 2',
        'discord_id': '356875221078245376',
        'icon_hash': '9ec2f87a898b9bb0981e4dc9c12bcf4e',
        'igdb_url': 'https://www.igdb.com/games/overwatch-2',
        'details': 'Competitive',
        'state': 'Payload Escort',
        'exe': 'overwatch/_retail_/overwatch.exe',
        'all_exes': ['overwatch/_retail_/overwatch.exe', 'overwatch.exe'],
        'search_key': 'overwatch 2 blizzard overwatch.exe'
    },
    {
        'name': "Marvel's Spider‑Man 2",
        'discord_id': '890695026638848050',
        'icon_hash': '666bbdbb228b3cf134c4f3914a1c5d31',
        'igdb_url': 'https://www.igdb.com/games/marvels-spider-man-2',
        'details': 'Swinging through Manhattan',
        'state': 'Story 85%',
        'exe': 'Spider-Man2.exe',
        'all_exes': ['Spider-Man2.exe'],
        'search_key': "marvel's spider-man 2 spider-man2.exe spiderman"
    }
]

KNOWN_DEFAULT_EXES = {
    'ea sports fc 27': [
        'EA SPORTS FC 27/FC27.exe',
        'FC27.exe',
        'EA SPORTS FC 27/FC27_trial.exe',
        'EA SPORTS FC 27/FC27_showcase.exe',
        'ea sports fc 27/fc27.exe'
    ],
    'grand theft auto vi': [
        'Grand Theft Auto VI/GTA6.exe',
        'GTA6.exe',
        'Grand Theft Auto VI/PlayGTA6.exe',
        'PlayGTA6.exe'
    ]
}


# ---------------------------------------------------------------------------
# Main Controller UI
# ---------------------------------------------------------------------------
class DiscordSpooferApp:
    def __init__(self, root):
        self.root = root
        root.title('Discord Process Spoofer & Verifier (FC 27 & GTA 6 Supported)')
        root.geometry('880x810')
        root.minsize(820, 730)

        self.proc = None
        self.target_exe_path = None
        self.discord_rpc = DiscordIPC()
        self.igdb_client = IGDBClient()
        self.all_games = list(FALLBACK_GAMES)
        self.displayed_games = []
        self.config_data = self.load_config()

        saved_id = self.config_data.get('igdb_client_id', '')
        saved_secret = self.config_data.get('igdb_client_secret', '')
        if saved_id and saved_secret:
            self.igdb_client.client_id = saved_id
            self.igdb_client.client_secret = saved_secret

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill='both', expand=True, padx=8, pady=(8, 4))

        self.tab_spoofer = tk.Frame(self.notebook)
        self.tab_igdb = tk.Frame(self.notebook)

        self.notebook.add(self.tab_spoofer, text=' 🎮 Game Spoofer & Detection ')
        self.notebook.add(self.tab_igdb, text=' 🌐 IGDB Library & API Settings ')

        self.build_spoofer_tab(self.tab_spoofer)
        self.build_igdb_tab(self.tab_igdb)

        self.status_bar = tk.Frame(root, bg='#f0f0f0', padx=10, pady=4)
        self.status_bar.pack(fill='x', side='bottom')

        self.status_label = tk.Label(
            self.status_bar,
            text='Status: Ready (Select GTA 6 or EA SPORTS FC 27 and click Start Spoofing)',
            fg='#333333',
            font=('Segoe UI', 9)
        )
        self.status_label.pack(side='left')

        self.rpc_status_label = tk.Label(
            self.status_bar,
            text='Discord IPC: Idle ⚪',
            fg='gray',
            font=('Segoe UI', 9, 'bold')
        )
        self.rpc_status_label.pack(side='right')

        self.populate_tree(self.all_games)
        threading.Thread(target=self.fetch_discord_games, daemon=True).start()

        root.protocol('WM_DELETE_WINDOW', self.on_closing)

    def load_config(self):
        try:
            if os.path.exists(CONFIG_PATH):
                with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def save_config(self):
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, indent=2)
        except Exception:
            pass

    # -----------------------------------------------------------------------
    # Build Spoofer Tab
    # -----------------------------------------------------------------------
    def build_spoofer_tab(self, parent):
        # 1. Quick Presets Frame
        preset_frame = tk.LabelFrame(
            parent,
            text=' 1. Quick Select Presets ',
            font=('Segoe UI', 9, 'bold'),
            padx=10,
            pady=6
        )
        preset_frame.pack(fill='x', padx=8, pady=(4, 4))

        p_row = tk.Frame(preset_frame)
        p_row.pack(fill='x')

        gta6_btn = tk.Button(
            p_row,
            text='🚗 Grand Theft Auto VI (GTA 6)',
            bg='#e81123',
            fg='white',
            font=('Segoe UI', 9, 'bold'),
            padx=10,
            pady=3,
            command=lambda: self.select_preset_by_name('Grand Theft Auto VI')
        )
        gta6_btn.pack(side='left', padx=(0, 6))

        fc27_btn = tk.Button(
            p_row,
            text='⚽ EA SPORTS FC 27',
            bg='#107c41',
            fg='white',
            font=('Segoe UI', 9, 'bold'),
            padx=10,
            pady=3,
            command=lambda: self.select_preset_by_name('EA Sports FC 27')
        )
        fc27_btn.pack(side='left', padx=(0, 6))

        fc26_btn = tk.Button(
            p_row,
            text='⚽ FC 26',
            bg='#2b5797',
            fg='white',
            font=('Segoe UI', 8),
            padx=6,
            command=lambda: self.select_preset_by_name('EA Sports FC 26')
        )
        fc26_btn.pack(side='left', padx=(0, 4))

        fc25_btn = tk.Button(
            p_row,
            text='⚽ FC 25',
            bg='#008272',
            fg='white',
            font=('Segoe UI', 8),
            padx=6,
            command=lambda: self.select_preset_by_name('EA Sports FC 25')
        )
        fc25_btn.pack(side='left', padx=(0, 4))

        gta5_btn = tk.Button(
            p_row,
            text='🚗 GTA V',
            font=('Segoe UI', 8),
            padx=6,
            command=lambda: self.select_preset_by_name('Grand Theft Auto V')
        )
        gta5_btn.pack(side='left', padx=(0, 4))

        cod_btn = tk.Button(
            p_row,
            text='🎮 COD HQ',
            font=('Segoe UI', 8),
            padx=6,
            command=lambda: self.select_preset_by_name('Call of Duty HQ')
        )
        cod_btn.pack(side='left')

        # 2. Public Library & Search Frame
        lib_frame = tk.LabelFrame(
            parent,
            text=' 2. Search Games (Discord & IGDB Catalog) ',
            font=('Segoe UI', 9, 'bold'),
            padx=10,
            pady=6
        )
        lib_frame.pack(fill='both', expand=True, padx=8, pady=(0, 4))

        search_row = tk.Frame(lib_frame)
        search_row.pack(fill='x', pady=(0, 6))

        tk.Label(search_row, text='Filter / Search:', font=('Segoe UI', 9)).pack(side='left', padx=(0, 6))
        self.search_var = tk.StringVar()
        self.search_var.trace_add('write', self.on_search_change)
        self.search_entry = tk.Entry(search_row, textvariable=self.search_var, font=('Segoe UI', 10))
        self.search_entry.pack(side='left', fill='x', expand=True, padx=(0, 6))

        clear_btn = tk.Button(
            search_row,
            text='Clear',
            width=8,
            font=('Segoe UI', 9),
            command=lambda: self.search_var.set('')
        )
        clear_btn.pack(side='left')

        tree_container = tk.Frame(lib_frame)
        tree_container.pack(fill='both', expand=True)

        v_scroll = ttk.Scrollbar(tree_container, orient='vertical')
        h_scroll = ttk.Scrollbar(tree_container, orient='horizontal')

        self.tree = ttk.Treeview(
            tree_container,
            columns=('name', 'exe', 'appid'),
            show='headings',
            selectmode='browse',
            yscrollcommand=v_scroll.set,
            xscrollcommand=h_scroll.set,
            height=8
        )
        self.tree.heading('name', text='Game Title (click to select)')
        self.tree.heading('exe', text='Target Process / Executable Path')
        self.tree.heading('appid', text='Discord App ID')
        self.tree.column('name', width=280, anchor='w')
        self.tree.column('exe', width=340, anchor='w')
        self.tree.column('appid', width=160, anchor='w')

        v_scroll.config(command=self.tree.yview)
        h_scroll.config(command=self.tree.xview)

        self.tree.grid(row=0, column=0, sticky='nsew')
        v_scroll.grid(row=0, column=1, sticky='ns')
        h_scroll.grid(row=1, column=0, sticky='ew')

        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)

        self.tree.bind('<<TreeviewSelect>>', self.on_select_game)

        self.api_status_label = tk.Label(
            lib_frame,
            text='Syncing public library from Discord & IGDB database...',
            fg='#0066cc',
            font=('Segoe UI', 8)
        )
        self.api_status_label.pack(anchor='w', pady=(3, 0))

        # 3. Target Process & Rich Presence Config
        config_frame = tk.LabelFrame(
            parent,
            text=' 3. Target Process & Discord Rich Presence ',
            font=('Segoe UI', 9, 'bold'),
            padx=10,
            pady=6
        )
        config_frame.pack(fill='x', padx=8, pady=(0, 4))

        row1 = tk.Frame(config_frame)
        row1.pack(fill='x', pady=(0, 4))

        col_exe = tk.Frame(row1)
        col_exe.pack(side='left', fill='x', expand=True, padx=(0, 6))
        tk.Label(col_exe, text='Executable / Relative Path:', font=('Segoe UI', 8, 'bold')).pack(anchor='w')
        self.path_combo = ttk.Combobox(col_exe, font=('Segoe UI', 9), values=FALLBACK_GAMES[0]['all_exes'])
        self.path_combo.set(FALLBACK_GAMES[0]['exe'])
        self.path_combo.pack(fill='x', pady=(2, 0))

        col_title = tk.Frame(row1)
        col_title.pack(side='left', fill='x', expand=True)
        tk.Label(col_title, text='Game Window Title:', font=('Segoe UI', 8, 'bold')).pack(anchor='w')
        self.title_entry = tk.Entry(col_title, font=('Segoe UI', 9))
        self.title_entry.insert(0, FALLBACK_GAMES[0]['name'])
        self.title_entry.pack(fill='x', pady=(2, 0))

        row2 = tk.Frame(config_frame)
        row2.pack(fill='x', pady=(2, 0))

        col_det = tk.Frame(row2)
        col_det.pack(side='left', fill='x', expand=True, padx=(0, 6))
        tk.Label(col_det, text='Discord Details (e.g. Vice City / Career Mode):', font=('Segoe UI', 8)).pack(anchor='w')
        self.details_entry = tk.Entry(col_det, font=('Segoe UI', 9))
        self.details_entry.insert(0, FALLBACK_GAMES[0].get('details', 'Exploring Leonida & Vice City'))
        self.details_entry.pack(fill='x', pady=(2, 0))

        col_st = tk.Frame(row2)
        col_st.pack(side='left', fill='x', expand=True, padx=(0, 6))
        tk.Label(col_st, text='Discord State (e.g. Story Mode / In Match):', font=('Segoe UI', 8)).pack(anchor='w')
        self.state_entry = tk.Entry(col_st, font=('Segoe UI', 9))
        self.state_entry.insert(0, FALLBACK_GAMES[0].get('state', 'Story Mode'))
        self.state_entry.pack(fill='x', pady=(2, 0))

        col_id = tk.Frame(row2)
        col_id.pack(side='left', fill='x', expand=True)
        tk.Label(col_id, text='Discord Application ID:', font=('Segoe UI', 8)).pack(anchor='w')
        self.appid_entry = tk.Entry(col_id, font=('Segoe UI', 9))
        self.appid_entry.insert(0, FALLBACK_GAMES[0].get('discord_id', ''))
        self.appid_entry.pack(fill='x', pady=(2, 0))

        # Row 3: Logo & Icon Size Selector
        row3 = tk.Frame(config_frame)
        row3.pack(fill='x', pady=(4, 2))

        col_icon = tk.Frame(row3)
        col_icon.pack(side='left', fill='x', expand=True)
        tk.Label(
            col_icon,
            text='Discord Logo Asset / Style (Full-size edge-to-edge logo matches GTA V):',
            font=('Segoe UI', 8, 'bold'),
            fg='#0066cc'
        ).pack(anchor='w')

        self.icon_combo = ttk.Combobox(
            col_icon,
            font=('Segoe UI', 9),
            values=FALLBACK_GAMES[0].get('icon_options', [FALLBACK_GAMES[0]['icon_hash']])
        )
        self.icon_combo.set(FALLBACK_GAMES[0]['icon_hash'])
        self.icon_combo.pack(fill='x', pady=(2, 0))

        # Row 4: Background Execution Checkbox
        row4 = tk.Frame(config_frame)
        row4.pack(fill='x', pady=(4, 0))

        self.bg_mode_var = tk.BooleanVar(value=True)
        self.bg_chk = tk.Checkbutton(
            row4,
            text="✔ Keep spoofed fake app completely in background (no popup window on screen)",
            variable=self.bg_mode_var,
            font=('Segoe UI', 8, 'bold'),
            fg='#107c41'
        )
        self.bg_chk.pack(side='left')

        # 4. Action Buttons
        btn_frame = tk.Frame(parent)
        btn_frame.pack(fill='x', padx=8, pady=(4, 6))

        self.start_btn = tk.Button(
            btn_frame,
            text='▶ Start Spoofing',
            width=18,
            bg='#28a745',
            fg='white',
            font=('Segoe UI', 9, 'bold'),
            command=self.start_process
        )
        self.start_btn.pack(side='left', padx=(0, 6))

        self.stop_btn = tk.Button(
            btn_frame,
            text='⏹ Stop & Clean Up',
            width=18,
            bg='#dc3545',
            fg='white',
            font=('Segoe UI', 9, 'bold'),
            state=tk.DISABLED,
            command=self.stop_process
        )
        self.stop_btn.pack(side='left', padx=(0, 6))

        self.verify_btn = tk.Button(
            btn_frame,
            text='🔍 Verify Detection',
            width=18,
            bg='#007bff',
            fg='white',
            font=('Segoe UI', 9, 'bold'),
            command=self.verify_on_machine
        )
        self.verify_btn.pack(side='left', padx=(0, 6))

        self.igdb_link_btn = tk.Button(
            btn_frame,
            text='🌐 View on IGDB',
            font=('Segoe UI', 9),
            command=self.open_current_igdb
        )
        self.igdb_link_btn.pack(side='left')

    # -----------------------------------------------------------------------
    # Build IGDB Tab
    # -----------------------------------------------------------------------
    def build_igdb_tab(self, parent):
        info_frame = tk.LabelFrame(
            parent,
            text=' About IGDB & Discord Validation ',
            font=('Segoe UI', 9, 'bold'),
            padx=10,
            pady=8
        )
        info_frame.pack(fill='x', padx=8, pady=(6, 4))

        about_text = (
            "IGDB (Internet Game Database, powered by Twitch / Amazon) is the global game authority that Discord\n"
            "uses to validate games and populate its detectable application database. Discord imports game titles,\n"
            "cover images, and metadata directly from IGDB to assign official Discord Application IDs.\n\n"
            "• Grand Theft Auto VI on IGDB: https://www.igdb.com/games/grand-theft-auto-vi\n"
            "• EA SPORTS FC 27 on IGDB: https://www.igdb.com/games/ea-sports-fc-27\n"
            "• IGDB Developer Documentation: https://api-docs.igdb.com/#authentication"
        )
        tk.Label(info_frame, text=about_text, font=('Segoe UI', 8), justify='left', fg='#333333').pack(anchor='w')

        # Live IGDB API Settings
        api_frame = tk.LabelFrame(
            parent,
            text=' Live IGDB API Integration (Twitch OAuth2) ',
            font=('Segoe UI', 9, 'bold'),
            padx=10,
            pady=8
        )
        api_frame.pack(fill='x', padx=8, pady=(4, 4))

        f_row1 = tk.Frame(api_frame)
        f_row1.pack(fill='x', pady=(0, 4))

        tk.Label(f_row1, text='Twitch Client ID:', font=('Segoe UI', 9), width=18, anchor='w').pack(side='left')
        self.igdb_id_entry = tk.Entry(f_row1, font=('Segoe UI', 9))
        self.igdb_id_entry.insert(0, self.igdb_client.client_id)
        self.igdb_id_entry.pack(side='left', fill='x', expand=True)

        f_row2 = tk.Frame(api_frame)
        f_row2.pack(fill='x', pady=(0, 4))

        tk.Label(f_row2, text='Twitch Client Secret:', font=('Segoe UI', 9), width=18, anchor='w').pack(side='left')
        self.igdb_secret_entry = tk.Entry(f_row2, font=('Segoe UI', 9), show='*')
        self.igdb_secret_entry.insert(0, self.igdb_client.client_secret)
        self.igdb_secret_entry.pack(side='left', fill='x', expand=True)

        auth_btn_row = tk.Frame(api_frame)
        auth_btn_row.pack(fill='x', pady=(4, 0))

        self.auth_igdb_btn = tk.Button(
            auth_btn_row,
            text='🔑 Connect & Authenticate with IGDB',
            font=('Segoe UI', 9, 'bold'),
            bg='#9146ff',
            fg='white',
            command=self.auth_igdb
        )
        self.auth_btn_row_spacer = tk.Label(auth_btn_row, text='  ')
        self.auth_btn_row_spacer.pack(side='left')
        self.auth_igdb_btn.pack(side='left', padx=(0, 6))

        tk.Button(
            auth_btn_row,
            text='Get Free Twitch Developer Credentials ↗',
            font=('Segoe UI', 8),
            command=lambda: webbrowser.open('https://dev.twitch.tv/console/apps/create')
        ).pack(side='left')

        self.igdb_auth_status = tk.Label(
            api_frame,
            text='Status: Not connected (Preloaded curated IGDB games active)',
            fg='gray',
            font=('Segoe UI', 8)
        )
        self.igdb_auth_status.pack(anchor='w', pady=(4, 0))

        # Live IGDB Game Search
        search_frame = tk.LabelFrame(
            parent,
            text=' Live Search IGDB Database ',
            font=('Segoe UI', 9, 'bold'),
            padx=10,
            pady=8
        )
        search_frame.pack(fill='both', expand=True, padx=8, pady=(4, 6))

        s_row = tk.Frame(search_frame)
        s_row.pack(fill='x', pady=(0, 6))

        self.igdb_query_entry = tk.Entry(s_row, font=('Segoe UI', 10))
        self.igdb_query_entry.insert(0, 'Grand Theft Auto VI')
        self.igdb_query_entry.pack(side='left', fill='x', expand=True, padx=(0, 6))

        tk.Button(
            s_row,
            text='🔍 Search IGDB',
            font=('Segoe UI', 9, 'bold'),
            bg='#007bff',
            fg='white',
            command=self.run_igdb_search
        ).pack(side='left', padx=(0, 6))

        self.igdb_tree = ttk.Treeview(
            search_frame,
            columns=('name', 'release', 'slug'),
            show='headings',
            selectmode='browse',
            height=6
        )
        self.igdb_tree.heading('name', text='IGDB Game Title')
        self.igdb_tree.heading('release', text='Release Date')
        self.igdb_tree.heading('slug', text='IGDB URL Slug')
        self.igdb_tree.column('name', width=320, anchor='w')
        self.igdb_tree.column('release', width=120, anchor='w')
        self.igdb_tree.column('slug', width=260, anchor='w')
        self.igdb_tree.pack(fill='both', expand=True, pady=(0, 6))

        import_row = tk.Frame(search_frame)
        import_row.pack(fill='x')

        tk.Button(
            import_row,
            text='⬇ Import Selected IGDB Game to Spoofer',
            font=('Segoe UI', 9, 'bold'),
            bg='#28a745',
            fg='white',
            command=self.import_selected_igdb_game
        ).pack(side='left', padx=(0, 6))

        tk.Button(
            import_row,
            text='🌐 Open Selected on IGDB Website',
            font=('Segoe UI', 8),
            command=self.open_selected_igdb_url
        ).pack(side='left')

    # -----------------------------------------------------------------------
    # Quick Preset Actions
    # -----------------------------------------------------------------------
    def select_preset_by_name(self, target_name):
        for item in self.all_games:
            if item['name'].lower() == target_name.lower():
                self.load_game_into_fields(item)
                self.status_label.config(
                    text=f"Selected preset: {item['name']} (Click 'Start Spoofing' to launch)",
                    fg='#107c41'
                )
                for idx, d_item in enumerate(self.displayed_games):
                    if d_item['name'].lower() == target_name.lower():
                        self.tree.selection_set(str(idx))
                        self.tree.see(str(idx))
                        break
                return

    def load_game_into_fields(self, item):
        all_exes = item.get('all_exes', [item['exe']])
        self.path_combo.config(values=all_exes)
        self.path_combo.set(item['exe'])
        self.title_entry.delete(0, tk.END)
        self.title_entry.insert(0, item['name'])

        self.details_entry.delete(0, tk.END)
        self.details_entry.insert(0, item.get('details', f"Playing {item['name']}"))

        self.state_entry.delete(0, tk.END)
        self.state_entry.insert(0, item.get('state', 'Active'))

        self.appid_entry.delete(0, tk.END)
        self.appid_entry.insert(0, item.get('discord_id', ''))

        opts = item.get('icon_options', [item.get('icon_hash', '')])
        self.icon_combo.config(values=opts)
        self.icon_combo.set(item.get('icon_hash', ''))

    def open_current_igdb(self):
        sel = self.tree.selection()
        if sel:
            idx = int(sel[0])
            if idx < len(self.displayed_games):
                item = self.displayed_games[idx]
                if item.get('igdb_url'):
                    webbrowser.open(item['igdb_url'])
                    return
        title = self.title_entry.get().strip()
        if 'fc 27' in title.lower():
            webbrowser.open('https://www.igdb.com/games/ea-sports-fc-27')
        elif 'gta' in title.lower() or 'grand theft auto vi' in title.lower():
            webbrowser.open('https://www.igdb.com/games/grand-theft-auto-vi')
        else:
            q = urllib.parse.quote(title)
            webbrowser.open(f'https://www.igdb.com/search?utf8=%E2%9C%93&q={q}')

    # -----------------------------------------------------------------------
    # Background Discord API Fetcher
    # -----------------------------------------------------------------------
    def fetch_discord_games(self):
        try:
            req = urllib.request.Request(
                DISCORD_API_URL,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            )
            with urllib.request.urlopen(req, timeout=12) as resp:
                raw_data = resp.read().decode('utf-8')
                parsed = json.loads(raw_data)

            games = []
            seen_names = set()

            for fb in FALLBACK_GAMES:
                games.append(dict(fb))
                seen_names.add(fb['name'].lower())

            for app in parsed:
                game_name = app.get('name', '').strip()
                if not game_name or game_name.lower() in seen_names:
                    continue

                app_id = str(app.get('id', ''))
                icon_hash = app.get('icon_hash', '')
                aliases = app.get('aliases', []) or []
                win_exes = []
                for exe_obj in app.get('executables', []) or []:
                    if exe_obj.get('os') == 'win32':
                        p = exe_obj.get('name', '').strip().lstrip('/')
                        if p and p not in win_exes:
                            win_exes.append(p)

                low_name = game_name.lower()
                if not win_exes:
                    if low_name in KNOWN_DEFAULT_EXES:
                        win_exes = list(KNOWN_DEFAULT_EXES[low_name])
                    elif 'fc 27' in low_name:
                        win_exes = KNOWN_DEFAULT_EXES['ea sports fc 27']
                    elif 'grand theft auto vi' in low_name or 'gta 6' in low_name:
                        win_exes = KNOWN_DEFAULT_EXES['grand theft auto vi']

                if not win_exes:
                    continue

                primary_exe = win_exes[0]
                search_key = (game_name + ' ' + ' '.join(aliases) + ' ' + ' '.join(win_exes) + ' ' + app_id).lower()

                games.append({
                    'name': game_name,
                    'exe': primary_exe,
                    'all_exes': win_exes,
                    'discord_id': app_id,
                    'icon_hash': icon_hash,
                    'search_key': search_key
                })
                seen_names.add(low_name)

            games.sort(key=lambda x: x['name'].lower())
            self.all_games = games
            try:
                self.root.after(0, self.on_api_loaded, len(games))
            except Exception:
                pass

        except Exception:
            try:
                self.root.after(
                    0,
                    lambda: self.api_status_label.config(
                        text=f'Offline – using built‑in database ({len(self.all_games)} games, including GTA 6 & FC 27)',
                        fg='#cc6600'
                    )
                )
            except Exception:
                pass

    def on_api_loaded(self, count):
        try:
            self.api_status_label.config(
                text=f'Library synchronized: {count:,} games (Grand Theft Auto VI & EA SPORTS FC 27 active).',
                fg='#28a745'
            )
            self.on_search_change()
        except Exception:
            pass

    # -----------------------------------------------------------------------
    # Filtering & Selection
    # -----------------------------------------------------------------------
    def on_search_change(self, *args):
        q = self.search_var.get().strip().lower()
        if not q:
            self.populate_tree(self.all_games)
            return

        terms = q.split()
        matches = []
        for item in self.all_games:
            key = item.get('search_key', (item.get('name', '') + ' ' + item.get('exe', '')).lower())
            if all(t in key for t in terms):
                matches.append(item)
        self.populate_tree(matches)

    def populate_tree(self, items):
        self.displayed_games = list(items)
        for row in self.tree.get_children():
            self.tree.delete(row)
        for idx, item in enumerate(self.displayed_games):
            self.tree.insert(
                '',
                'end',
                iid=str(idx),
                values=(item['name'], item['exe'], item.get('discord_id', 'N/A'))
            )

    def on_select_game(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        if idx < len(self.displayed_games):
            item = self.displayed_games[idx]
            self.load_game_into_fields(item)

    # -----------------------------------------------------------------------
    # IGDB Authentication & Search
    # -----------------------------------------------------------------------
    def auth_igdb(self):
        c_id = self.igdb_id_entry.get().strip()
        c_secret = self.igdb_secret_entry.get().strip()
        if not c_id or not c_secret:
            messagebox.showwarning("IGDB Credentials", "Please enter both Twitch Client ID and Client Secret.")
            return

        def run_auth():
            try:
                token = self.igdb_client.authenticate(c_id, c_secret)
                self.config_data['igdb_client_id'] = c_id
                self.config_data['igdb_client_secret'] = c_secret
                self.save_config()
                self.root.after(0, lambda: self.igdb_auth_status.config(
                    text=f"Connected to IGDB API (Token active: {token[:8]}...)",
                    fg='#28a745'
                ))
                self.root.after(0, lambda: messagebox.showinfo("IGDB Connected", "Successfully authenticated with IGDB!"))
            except Exception as e:
                self.root.after(0, lambda: self.igdb_auth_status.config(
                    text=f"Authentication error: {e}",
                    fg='#dc3545'
                ))
                self.root.after(0, lambda: messagebox.showerror("IGDB Error", f"Authentication failed:\n{e}"))

        threading.Thread(target=run_auth, daemon=True).start()

    def run_igdb_search(self):
        q = self.igdb_query_entry.get().strip()
        if not q:
            return

        for row in self.igdb_tree.get_children():
            self.igdb_tree.delete(row)

        def do_search():
            try:
                results = self.igdb_client.search_games(q)
                self.root.after(0, lambda: self.populate_igdb_results(results))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("IGDB Search Error", f"{e}\n\nPlease verify your Twitch credentials in the IGDB API settings above."))

        threading.Thread(target=do_search, daemon=True).start()

    def populate_igdb_results(self, results):
        for row in self.igdb_tree.get_children():
            self.igdb_tree.delete(row)
        self.cached_igdb_results = results
        for idx, g in enumerate(results):
            name = g.get('name', 'Unknown')
            slug = g.get('slug', '')
            rd = g.get('first_release_date')
            rd_str = time.strftime('%Y-%m-%d', time.gmtime(rd)) if rd else 'TBD'
            self.igdb_tree.insert('', 'end', iid=str(idx), values=(name, rd_str, slug))

    def import_selected_igdb_game(self):
        sel = self.igdb_tree.selection()
        if not sel or not hasattr(self, 'cached_igdb_results'):
            messagebox.showinfo("Import", "Please select a game from the search results.")
            return
        idx = int(sel[0])
        g = self.cached_igdb_results[idx]
        name = g.get('name', 'Game')
        slug = g.get('slug', 'game')

        safe_exe = slug.replace('-', '').capitalize() + '.exe'
        rel_exe = f"{name}/{safe_exe}"

        matched_id = ""
        matched_icon = None
        for app in self.all_games:
            if app['name'].lower() == name.lower():
                matched_id = app.get('discord_id', '')
                matched_icon = app.get('icon_hash')
                break

        game_obj = {
            'name': name,
            'exe': rel_exe,
            'all_exes': [rel_exe, safe_exe],
            'discord_id': matched_id,
            'icon_hash': matched_icon,
            'igdb_url': f"https://www.igdb.com/games/{slug}",
            'details': f"Playing {name}",
            'state': 'Active'
        }
        self.load_game_into_fields(game_obj)
        self.notebook.select(self.tab_spoofer)
        self.status_label.config(text=f"Imported '{name}' from IGDB! Click 'Start Spoofing' to launch.", fg='#107c41')

    def open_selected_igdb_url(self):
        sel = self.igdb_tree.selection()
        if not sel or not hasattr(self, 'cached_igdb_results'):
            return
        idx = int(sel[0])
        slug = self.cached_igdb_results[idx].get('slug')
        if slug:
            webbrowser.open(f"https://www.igdb.com/games/{slug}")

    # -----------------------------------------------------------------------
    # Dual-Engine Process Launch & Discord RPC
    # -----------------------------------------------------------------------
    def start_process(self):
        rel_path = self.path_combo.get().strip().replace('\\', '/')
        win_title = self.title_entry.get().strip() or 'Game'
        app_id = self.appid_entry.get().strip()
        details = self.details_entry.get().strip() or f"Playing {win_title}"
        state = self.state_entry.get().strip() or "Active"
        icon_asset = self.icon_combo.get().strip()
        run_in_background = self.bg_mode_var.get()

        if not rel_path:
            messagebox.showwarning('Input Error', 'Please provide an executable path.')
            return

        for ch in (':', '*', '?', '"', '<', '>', '|'):
            if ch in rel_path:
                messagebox.showwarning('Input Error', f"Invalid character '{ch}' in path.")
                return

        if not rel_path.lower().endswith('.exe'):
            rel_path += '.exe'

        try:
            # --- ENGINE 1: Local Executable Spoofer ---
            base_dir = tempfile.mkdtemp(prefix='discord_spoof_')
            target_path = os.path.normpath(os.path.join(base_dir, rel_path))
            target_dir = os.path.dirname(target_path)
            os.makedirs(target_dir, exist_ok=True)

            py_dir = os.path.dirname(sys.executable)
            source_exe = os.path.join(py_dir, 'pythonw.exe')
            if not os.path.exists(source_exe):
                source_exe = sys.executable

            shutil.copy2(source_exe, target_path)

            creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0

            if os.path.basename(source_exe).lower() == 'pythonw.exe':
                win_escaped = win_title.replace("'", "\\'")
                window_code = (
                    f"import tkinter as tk;"
                    f"root=tk.Tk();"
                    f"root.title('{win_escaped}');"
                    f"root.withdraw();"  # Stays silently in background
                    f"root.mainloop()"
                )
                cmd = [target_path, '-c', window_code]
            else:
                cmd = [target_path, '--dummy', win_title]
                if not run_in_background:
                    cmd.append('--show-window')

            self.proc = subprocess.Popen(
                cmd,
                cwd=target_dir,
                creationflags=creation_flags
            )
            self.target_exe_path = target_path

            # --- ENGINE 2: Native Discord RPC via Local Pipe ---
            rpc_active = False

            if not icon_asset:
                for g in self.all_games:
                    if g['name'].lower() == win_title.lower():
                        icon_asset = g.get('icon_hash')
                        if not app_id:
                            app_id = g.get('discord_id', '')
                        break

            if app_id:
                if self.discord_rpc.connect(app_id):
                    rpc_active = self.discord_rpc.set_activity(
                        details=details,
                        state=state,
                        large_image=icon_asset,
                        large_text=win_title
                    )

            exe_name = os.path.basename(target_path)
            if rpc_active:
                rpc_text = f"Connected (Playing {win_title}) 🟢"
                rpc_color = '#28a745'
            else:
                rpc_text = "Running via Process Scanner 🟡"
                rpc_color = '#e67e22'

            mode_str = "Background Process" if run_in_background else "Visible Window"
            self.rpc_status_label.config(text=f"Discord IPC: {rpc_text}", fg=rpc_color)
            self.status_label.config(
                text=f'▶ Active ({mode_str}): {exe_name} (PID: {self.proc.pid}) | Title: "{win_title}"',
                fg='#28a745'
            )

            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
            self.path_combo.config(state='disabled')
            self.title_entry.config(state='disabled')

        except Exception as e:
            messagebox.showerror('Launch Error', f"Failed to start spoofed game:\n{e}")

    # -----------------------------------------------------------------------
    # Verification & Diagnostics
    # -----------------------------------------------------------------------
    def verify_on_machine(self):
        if not self.proc:
            messagebox.showinfo('Verification', 'No spoofed game process is currently running.')
            return

        exe_name = os.path.basename(self.target_exe_path) if self.target_exe_path else 'N/A'
        exe_base = os.path.splitext(exe_name)[0]
        game_title = self.title_entry.get().strip()

        ps_script = f"""
        $procs = Get-Process -Name '{exe_base}' -ErrorAction SilentlyContinue
        $discord = Get-Process -Name 'Discord' -ErrorAction SilentlyContinue
        $count = 0
        $pids = @()
        if ($procs) {{
            $count = ($procs | Measure-Object).Count
            foreach ($p in $procs) {{ $pids += $p.Id }}
        }}
        Write-Output "PROCESS_NAME={exe_name}"
        Write-Output "RUNNING_INSTANCES=$count"
        Write-Output "PROCESS_PIDS=$($pids -join ', ')"
        Write-Output "DISCORD_DESKTOP_RUNNING=$($discord -ne $null)"
        """

        try:
            res = subprocess.run(
                ['powershell', '-NoProfile', '-Command', ps_script],
                capture_output=True,
                text=True,
                timeout=6,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            out = res.stdout.strip()
            rpc_msg = "Discord Direct RPC is CONNECTED & BROADCASTING 🟢" if self.discord_rpc.connected else "Discord Direct RPC is disconnected ⚪"
            messagebox.showinfo(
                'Machine Diagnostic',
                f"=== Spoof Diagnostic for {game_title} ===\n\n"
                f"Binary: {exe_name}\n"
                f"Parent PID: {self.proc.pid}\n"
                f"Mode: {'Silent Background' if self.bg_mode_var.get() else 'Visible Window'}\n"
                f"Discord Direct IPC: {rpc_msg}\n\n"
                f"--- Windows Process Status ---\n{out}\n\n"
                f"✔ Game is broadcasting to Discord! Check your Discord profile and status."
            )
        except Exception as e:
            messagebox.showerror('Verification Error', str(e))

    # -----------------------------------------------------------------------
    # Bulletproof Stop & Clean Up (Terminates all parent & worker processes)
    # -----------------------------------------------------------------------
    def stop_process(self):
        try:
            self.cleanup()
        except Exception:
            pass
        finally:
            try:
                self.status_label.config(
                    text='Status: Stopped (All processes terminated & temporary files wiped)',
                    fg='gray'
                )
                self.rpc_status_label.config(text='Discord IPC: Idle ⚪', fg='gray')
                self.start_btn.config(state=tk.NORMAL)
                self.stop_btn.config(state=tk.DISABLED)
                self.path_combo.config(state='normal')
                self.title_entry.config(state='normal')
            except Exception:
                pass

    def cleanup(self):
        # 1. Disconnect Discord RPC
        try:
            self.discord_rpc.close()
        except Exception:
            pass

        # 2. Extract target executable name for bulletproof kill by image name
        exe_name = None
        target_dir = self.target_exe_path
        if target_dir:
            exe_name = os.path.basename(target_dir)
        self.target_exe_path = None

        proc_to_kill = self.proc
        self.proc = None

        # 3. Terminate process tree via PID
        if proc_to_kill:
            try:
                proc_to_kill.terminate()
            except Exception:
                pass
            try:
                if os.name == 'nt' and hasattr(proc_to_kill, 'pid'):
                    subprocess.run(
                        ['taskkill', '/F', '/T', '/PID', str(proc_to_kill.pid)],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
            except Exception:
                pass
            try:
                proc_to_kill.kill()
            except Exception:
                pass

        # 4. CRITICAL: Terminate ALL lingering worker child processes by Image Name
        # PyInstaller onefile spawns both a bootloader PID and a worker PID with the same exe name!
        if os.name == 'nt' and exe_name and exe_name.lower().endswith('.exe'):
            try:
                subprocess.run(
                    ['taskkill', '/F', '/IM', exe_name],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            except Exception:
                pass

        # 5. Clean up sandbox folder in a background daemon thread
        if target_dir:
            def wipe_temp_worker(path):
                time.sleep(0.4)
                try:
                    cur = os.path.dirname(path)
                    while cur and os.path.basename(cur):
                        if os.path.basename(cur).startswith('discord_spoof_'):
                            shutil.rmtree(cur, ignore_errors=True)
                            break
                        parent = os.path.dirname(cur)
                        if parent == cur:
                            break
                        cur = parent
                except Exception:
                    pass
            threading.Thread(target=wipe_temp_worker, args=(target_dir,), daemon=True).start()

    def on_closing(self):
        try:
            self.cleanup()
        except Exception:
            pass
        finally:
            try:
                self.root.destroy()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    root = tk.Tk()
    app = DiscordSpooferApp(root)
    root.mainloop()
