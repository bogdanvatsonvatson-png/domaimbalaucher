import json
import os
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import webbrowser
import shutil
from tkinter import colorchooser, filedialog
from pathlib import Path

import minecraft_launcher_lib

APP_NAME = "doma_launcher"
CONFIG_DIR = Path.home() / ".doma_launcher"
CONFIG_FILE = CONFIG_DIR / "config.json"
MC_DIR = minecraft_launcher_lib.utils.get_minecraft_directory()

# Create a Microsoft/Azure app and place its Client ID here.
# Redirect URI must exactly match the URI configured in that app.
CLIENT_ID = "PASTE_YOUR_MICROSOFT_CLIENT_ID_HERE"
REDIRECT_URI = "http://localhost:8080"

class DomaLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("doma_launcher")
        self.root.geometry("760x500")
        self.root.minsize(680, 450)
        self.root.configure(bg="#10131d")
        self.account = None
        self.versions = []
        self.theme_color = "#8b5cf6"
        self.status = tk.StringVar(value="Готов к работе")
        self.account_label = tk.StringVar(value="Аккаунт не подключён")
        self.game_dir = Path.home() / "doma_launcher" / "game"
        self._ensure_dirs()
        self._build_ui()
        self.load_saved_account()
        self.create_game_folders(silent=True) if False else None
        self.refresh_versions()

    def _ensure_dirs(self):
        for name in ("mods", "resourcepacks", "shaderpacks", "screenshots", "saves", "config", "logs", "versions"):
            (self.game_dir / name).mkdir(parents=True, exist_ok=True)

    def _build_ui(self):
        from tkinter import colorchooser

        self.accent = "#8b5cf6"
        self.bg = "#10131d"
        self.panel = "#171b2b"
        self.text_color = "#f4f5ff"
        self.muted = "#aab2cf"
        self.pages = {}
        self.current_page = None
        self._animation_running = False

        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TCombobox", padding=7)
        style.configure("TProgressbar", troughcolor="#242a3b", background=self.accent)

        shell = tk.Frame(self.root, bg=self.bg)
        shell.pack(fill="both", expand=True)

        sidebar = tk.Frame(shell, bg=self.panel, width=190, padx=14, pady=18)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        tk.Label(sidebar, text="doma_", fg=self.text_color, bg=self.panel,
                 font=("Segoe UI", 21, "bold")).pack(anchor="w")
        tk.Label(sidebar, text="LAUNCHER", fg=self.accent, bg=self.panel,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 24))

        self.nav_buttons = {}
        for key, label in [
            ("play", "▶  Играть"),
            ("clients", "✦  Клиенты"),
            ("folders", "▣  Папки игры"),
            ("appearance", "◐  Оформление"),
        ]:
            btn = tk.Button(sidebar, text=label, anchor="w",
                            command=lambda k=key: self.show_page(k),
                            bg=self.panel, fg=self.text_color,
                            activebackground="#282f45", activeforeground="white",
                            relief="flat", bd=0, padx=12, pady=12,
                            font=("Segoe UI", 10))
            btn.pack(fill="x", pady=3)
            self.nav_buttons[key] = btn

        tk.Frame(sidebar, bg="#2a3045", height=1).pack(fill="x", pady=18)
        self.account_label = tk.StringVar(value="Аккаунт не подключён")
        tk.Label(sidebar, textvariable=self.account_label, fg=self.muted, bg=self.panel,
                 font=("Segoe UI", 8), wraplength=155, justify="left").pack(anchor="w")
        tk.Button(sidebar, text="Войти через Microsoft", command=self.login,
                  bg="#282f45", fg="white", activebackground="#343d59",
                  activeforeground="white", relief="flat", padx=8, pady=9,
                  font=("Segoe UI", 9)).pack(fill="x", pady=(10, 0))

        self.page_host = tk.Frame(shell, bg=self.bg)
        self.page_host.pack(side="left", fill="both", expand=True)
        self._make_play_page()
        self._make_clients_page()
        self._make_folders_page()
        self._make_appearance_page()

        footer = tk.Frame(self.root, bg=self.panel, padx=20, pady=8)
        footer.pack(fill="x")
        self.status = tk.StringVar(value="Готов к работе")
        self.progress = ttk.Progressbar(footer, mode="indeterminate", length=150)
        self.progress.pack(side="right", padx=(12, 0))
        tk.Label(footer, textvariable=self.status, fg=self.muted, bg=self.panel,
                 font=("Segoe UI", 9), anchor="w").pack(side="left", fill="x", expand=True)

        self.show_page("play")

    def _new_page(self, key, title, subtitle):
        page = tk.Frame(self.page_host, bg=self.bg, padx=28, pady=26)
        self.pages[key] = page
        tk.Label(page, text=title, fg=self.text_color, bg=self.bg,
                 font=("Segoe UI", 23, "bold")).pack(anchor="w")
        tk.Label(page, text=subtitle, fg=self.muted, bg=self.bg,
                 font=("Segoe UI", 10)).pack(anchor="w", pady=(4, 22))
        return page

    def _make_play_page(self):
        page = self._new_page("play", "Играть в Minecraft", "Выбери версию и запускай игру")
        tk.Label(page, text="ВЕРСИЯ ИГРЫ", fg=self.muted, bg=self.bg,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w")
        row = tk.Frame(page, bg=self.bg)
        row.pack(fill="x", pady=(8, 20))
        self.version_box = ttk.Combobox(row, state="readonly", font=("Segoe UI", 11))
        self.version_box.pack(side="left", fill="x", expand=True, ipady=4)
        tk.Button(row, text="Обновить", command=self.refresh_versions,
                  bg="#282f45", fg="white", activebackground="#343d59",
                  activeforeground="white", relief="flat", padx=15, pady=10).pack(side="left", padx=(10, 0))
        self.play_btn = tk.Button(page, text="УСТАНОВИТЬ И ИГРАТЬ",
                  command=self.play, bg=self.accent, fg="white",
                  activebackground=self.accent, activeforeground="white",
                  relief="flat", font=("Segoe UI", 11, "bold"), padx=22, pady=14)
        self.play_btn.pack(anchor="w", pady=(2, 18))
        tk.Label(page, text="doma_launcher устанавливает выбранную версию автоматически.",
                 fg=self.muted, bg=self.bg, font=("Segoe UI", 9), wraplength=520,
                 justify="left").pack(anchor="w")
        tk.Label(page, text=f"Папка игры: {MC_DIR}", fg="#737d9e", bg=self.bg,
                 font=("Segoe UI", 8), wraplength=520, justify="left").pack(anchor="w", pady=(12, 0))
        tk.Label(page, text="Для игры требуется лицензия Minecraft Java Edition.",
                 fg="#737d9e", bg=self.bg, font=("Segoe UI", 8)).pack(anchor="w", pady=(8, 0))

    def _make_clients_page(self):
        page = self._new_page("clients", "Клиенты и моды", "Проверенные страницы проектов — открывай только официальные сайты")
        clients = [
            ("Lunar Client", "HUD, Zoom, FPS-инструменты и другие клиентские моды.", "https://www.lunarclient.com/download"),
            ("Badlion Client", "Клиент с набором модов и настройками производительности.", "https://www.badlion.net/"),
            ("Modrinth", "Каталог модов, сборок, шейдеров и ресурспаков.", "https://modrinth.com/"),
            ("AxolotlClient", "Настраиваемый HUD и PvP-ориентированные удобства.", "https://modrinth.com/mod/axolotlclient"),
            ("Bewisclient", "Клиентские виджеты, Zoom, Fullbright и информация на экране.", "https://modrinth.com/mod/bewisclient"),
        ]
        for name, desc, url in clients:
            card = tk.Frame(page, bg=self.panel, padx=14, pady=11)
            card.pack(fill="x", pady=5)
            top = tk.Frame(card, bg=self.panel)
            top.pack(fill="x")
            tk.Label(top, text=name, fg=self.text_color, bg=self.panel,
                     font=("Segoe UI", 11, "bold")).pack(side="left")
            tk.Button(top, text="Открыть сайт ↗", command=lambda u=url: webbrowser.open(u),
                      bg=self.accent, fg="white", activebackground=self.accent,
                      activeforeground="white", relief="flat", padx=10, pady=5,
                      font=("Segoe UI", 8, "bold")).pack(side="right")
            tk.Label(card, text=desc, fg=self.muted, bg=self.panel,
                     font=("Segoe UI", 9), wraplength=460, justify="left").pack(anchor="w", pady=(6, 0))
        tk.Label(page, text="Здесь перечислены моды и игровые удобства, а не читы для нечестного преимущества на серверах.",
                 fg=self.muted, bg=self.bg, font=("Segoe UI", 8), wraplength=510,
                 justify="left").pack(anchor="w", pady=(10, 0))

    def _make_folders_page(self):
        page = self._new_page("folders", "Папки Minecraft", "Открывай папки игры и управляй файлами")
        self.game_folders = {
            "Корневая папка .minecraft": Path(MC_DIR),
            "mods": Path(MC_DIR) / "mods",
            "resourcepacks": Path(MC_DIR) / "resourcepacks",
            "shaderpacks": Path(MC_DIR) / "shaderpacks",
            "versions": Path(MC_DIR) / "versions",
            "saves": Path(MC_DIR) / "saves",
            "screenshots": Path(MC_DIR) / "screenshots",
            "config": Path(MC_DIR) / "config",
            "logs": Path(MC_DIR) / "logs",
            "crash-reports": Path(MC_DIR) / "crash-reports",
        }
        for label, path in self.game_folders.items():
            card = tk.Frame(page, bg=self.panel, padx=12, pady=8)
            card.pack(fill="x", pady=3)
            tk.Label(card, text=label, fg=self.text_color, bg=self.panel,
                     font=("Segoe UI", 10, "bold")).pack(side="left")
            tk.Button(card, text="Открыть", command=lambda p=path: self.open_folder(p),
                      bg="#282f45", fg="white", activebackground="#343d59",
                      activeforeground="white", relief="flat", padx=12, pady=5).pack(side="right")
        tk.Button(page, text="Создать отсутствующие папки", command=self.create_game_folders,
                  bg=self.accent, fg="white", activebackground=self.accent,
                  activeforeground="white", relief="flat", padx=14, pady=10).pack(anchor="w", pady=(12, 0))

    def _make_appearance_page(self):
        page = self._new_page("appearance", "Оформление", "Настрой цвет акцента меню")
        tk.Label(page, text="ЦВЕТ МЕНЮ", fg=self.muted, bg=self.bg,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w")
        presets = [
            ("Фиолетовый", "#8b5cf6"), ("Голубой", "#0ea5e9"),
            ("Зелёный", "#10b981"), ("Красный", "#ef4444"),
            ("Розовый", "#ec4899"), ("Оранжевый", "#f97316"),
        ]
        for i in range(0, len(presets), 2):
            row = tk.Frame(page, bg=self.bg)
            row.pack(anchor="w", fill="x", pady=5)
            for label, color in presets[i:i+2]:
                tk.Button(row, text=label, command=lambda c=color: self.set_accent(c),
                          bg=color, fg="white", activebackground=color,
                          activeforeground="white", relief="flat", padx=18, pady=10,
                          width=12).pack(side="left", padx=(0, 10))
        tk.Button(page, text="Выбрать свой цвет…", command=self.choose_accent,
                  bg="#282f45", fg="white", activebackground="#343d59",
                  activeforeground="white", relief="flat", padx=16, pady=10).pack(anchor="w", pady=(10, 0))
        tk.Label(page, text="Цвет применяется к кнопкам и активным элементам. Изменение сохраняется на время работы приложения.",
                 fg=self.muted, bg=self.bg, font=("Segoe UI", 9), wraplength=500,
                 justify="left").pack(anchor="w", pady=(18, 0))

    def show_page(self, key):
        if self._animation_running:
            return
        target = self.pages[key]
        if self.current_page == key:
            return
        for child in self.page_host.winfo_children():
            child.place_forget()
        for k, btn in self.nav_buttons.items():
            btn.configure(bg=self.accent if k == key else self.panel,
                          fg="white" if k == key else self.text_color)
        target.place(x=22, y=0, relwidth=1, relheight=1, width=-22)
        self.current_page = key
        # Small horizontal slide animation when switching pages.
        self._animation_running = True
        steps = 5
        def animate(i=0):
            if not target.winfo_exists():
                self._animation_running = False
                return
            if i >= steps:
                target.place_configure(x=0, width=0)
                self._animation_running = False
                return
            x = int(22 * (steps - i - 1) / steps)
            target.place_configure(x=x, width=-x)
            self.root.after(12, lambda: animate(i + 1))
        animate()

    def set_accent(self, color):
        self.accent = color
        for key, btn in self.nav_buttons.items():
            if key == self.current_page:
                btn.configure(bg=color)
        if hasattr(self, "play_btn"):
            self.play_btn.configure(bg=color, activebackground=color)
        # Refresh client and appearance page button accents without rebuilding pages.
        for page_key in ("clients", "appearance", "folders"):
            for widget in self.pages[page_key].winfo_children():
                self._recolor_buttons(widget, color)
        style = ttk.Style()
        style.configure("TProgressbar", background=color)
        self.set_status("Цвет меню изменён на " + color)

    def _recolor_buttons(self, widget, color):
        for child in widget.winfo_children():
            if isinstance(child, tk.Button) and child.cget("text") in ("Открыть сайт ↗", "Создать отсутствующие папки"):
                child.configure(bg=color, activebackground=color)
            self._recolor_buttons(child, color)

    def choose_accent(self):
        chosen = __import__("tkinter.colorchooser", fromlist=["askcolor"]).askcolor(
            self.accent, title="Цвет меню"
        )[1]
        if chosen:
            self.set_accent(chosen)

    def open_folder(self, path):
        try:
            path.mkdir(parents=True, exist_ok=True)
            if os.name == "nt":
                os.startfile(str(path))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except Exception as e:
            messagebox.showerror("Не удалось открыть папку", str(e))

    def create_game_folders(self):
        created = []
        for label, path in self.game_folders.items():
            try:
                path.mkdir(parents=True, exist_ok=True)
                created.append(label)
            except Exception:
                pass
        self.set_status(f"Проверено папок: {len(created)}")
        messagebox.showinfo("Папки Minecraft", f"Создано или проверено папок: {len(created)}")

    def set_status(self, text):
        self.root.after(0, self.status.set, text)

    def busy(self, yes):
        def update():
            if yes:
                self.progress.start(10)
            else:
                self.progress.stop()
        self.root.after(0, update)

    def load_saved_account(self):
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            if data.get("theme_color"):
                self.theme_color = data["theme_color"]
            # Tokens are intentionally not saved in this starter version.
            if data.get("name") and data.get("id") and data.get("access_token"):
                self.account = data
                self.account_label.set("Вошли как: " + data["name"])
        except Exception:
            pass

    def refresh_versions(self):
        def worker():
            self.busy(True)
            self.set_status("Получаю список версий с официального каталога...")
            try:
                versions = minecraft_launcher_lib.utils.get_version_list()
                releases = [v["id"] for v in versions if v.get("type") == "release"]
                snapshots = [v["id"] for v in versions if v.get("type") == "snapshot"]
                # Release versions first; snapshots are available at the bottom.
                ordered = releases + snapshots
                self.versions = ordered
                def done():
                    self.version_box["values"] = ordered
                    latest = minecraft_launcher_lib.utils.get_latest_version()["release"]
                    self.version_box.set(latest if latest in ordered else (ordered[0] if ordered else ""))
                    self.status.set(f"Найдено версий: {len(ordered)}")
                self.root.after(0, done)
            except Exception as e:
                self.set_status("Не удалось загрузить список версий. Проверьте интернет. " + str(e))
            finally:
                self.busy(False)
        threading.Thread(target=worker, daemon=True).start()

    def login(self):
        if CLIENT_ID == "PASTE_YOUR_MICROSOFT_CLIENT_ID_HERE":
            messagebox.showinfo(
                "Нужна настройка входа",
                "Для Microsoft-входа нужно создать приложение в Microsoft Entra/Azure, "
                "указать Client ID в app.py и настроить Redirect URI: " + REDIRECT_URI +
                "\\n\\nИнструкция находится в README.txt."
            )
            return
        try:
            login_url, state, verifier = minecraft_launcher_lib.microsoft_account.get_secure_login_data(
                CLIENT_ID, REDIRECT_URI
            )
            webbrowser.open(login_url)
            code_url = simpledialog.askstring(
                "Вход Microsoft",
                "Войдите в браузере. После перенаправления на localhost скопируйте полный адрес из адресной строки и вставьте сюда:"
            )
            if not code_url:
                return
            auth_code = minecraft_launcher_lib.microsoft_account.parse_auth_code_url(code_url, state)
            self.busy(True)
            self.set_status("Проверяю аккаунт Microsoft / Minecraft...")
            def worker():
                try:
                    data = minecraft_launcher_lib.microsoft_account.complete_login(
                        CLIENT_ID, None, REDIRECT_URI, auth_code, verifier
                    )
                    self.account = {
                        "name": data["name"], "id": data["id"],
                        "access_token": data["access_token"],
                        "refresh_token": data.get("refresh_token", "")
                    }
                    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
                    CONFIG_FILE.write_text(json.dumps(self.account), encoding="utf-8")
                    self.root.after(0, self.account_label.set, "Вошли как: " + data["name"])
                    self.set_status("Вход выполнен.")
                except Exception as e:
                    self.set_status("Ошибка входа: " + str(e))
                    self.root.after(0, messagebox.showerror, "Ошибка входа", str(e))
                finally:
                    self.busy(False)
            threading.Thread(target=worker, daemon=True).start()
        except Exception as e:
            messagebox.showerror("Ошибка входа", str(e))

    def play(self):
        if not self.account:
            messagebox.showwarning("Нужен аккаунт", "Сначала войдите через Microsoft.")
            return
        version = self.version_box.get().strip()
        if not version:
            messagebox.showwarning("Версия не выбрана", "Сначала выберите версию Minecraft.")
            return
        def worker():
            self.busy(True)
            try:
                self.set_status(f"Устанавливаю Minecraft {version} (если ещё не установлен)...")
                minecraft_launcher_lib.install.install_minecraft_version(version, str(self.game_dir))
                self.set_status("Запускаю Minecraft...")
                options = {
                    "username": self.account["name"],
                    "uuid": self.account["id"],
                    "token": self.account["access_token"],
                }
                command = minecraft_launcher_lib.command.get_minecraft_command(
                    version, str(self.game_dir), options
                )
                subprocess.Popen(command, cwd=str(self.game_dir))
                self.set_status("Команда запуска отправлена. Можно вернуться в игру.")
            except Exception as e:
                self.set_status("Ошибка запуска: " + str(e))
                self.root.after(0, messagebox.showerror, "Не удалось запустить Minecraft", str(e))
            finally:
                self.busy(False)
        threading.Thread(target=worker, daemon=True).start()

def main():
    root = tk.Tk()
    DomaLauncher(root)
    root.mainloop()

if __name__ == "__main__":
    main()
