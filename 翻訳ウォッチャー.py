#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
研修生チェックリスト 翻訳ウォッチャー
input/ フォルダを監視 → Google翻訳 → output/ に保存
Windows / macOS 両対応
"""

import tkinter as tk
from tkinter import scrolledtext, messagebox
import threading
import time
import os
import sys
import platform
from pathlib import Path
from datetime import datetime

# ── PyInstaller対応: EXEの場所を基準にフォルダを作る ──
def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent

BASE_DIR   = get_base_dir()
INPUT_DIR  = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "output"
INPUT_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# ── 翻訳言語設定 ─────────────────────────────────────
TARGET_LANGS = {
    "vi":    "ベトナム語",
    "zh-CN": "中国語（簡体）",
}

# ── OS別フォント ──────────────────────────────────────
IS_WINDOWS = platform.system() == "Windows"
FONT_UI  = "Yu Gothic UI"   if IS_WINDOWS else "Hiragino Kaku Gothic ProN"
FONT_MONO = "MS Gothic"     if IS_WINDOWS else "Courier"

def F(size=12, bold=False):
    return (FONT_UI, size, "bold" if bold else "normal")

# ── ライブラリ確認 ────────────────────────────────────
try:
    from deep_translator import GoogleTranslator
    TRANSLATOR_OK = True
except ImportError:
    TRANSLATOR_OK = False

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_OK = True
except ImportError:
    WATCHDOG_OK = False


# ─────────────────────────────────────────────────────
class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("研修生チェックリスト 翻訳ウォッチャー")
        self.root.geometry("640x540")
        self.root.resizable(True, True)
        self.root.configure(bg="#fdf8f0")
        self.observer = None
        self.watching = False
        self._build_ui()
        self._startup_check()

    # ── UI ────────────────────────────────────────────
    def _build_ui(self):
        # ヘッダー
        tk.Frame(self.root, bg="#b91c1c", height=4).pack(fill="x")
        hdr = tk.Frame(self.root, bg="#b91c1c", pady=14)
        hdr.pack(fill="x")
        tk.Label(hdr, text="研修生チェックリスト  翻訳ウォッチャー",
                 font=F(16, bold=True), fg="white", bg="#b91c1c").pack()
        tk.Label(hdr, text="input/ にテキストを入れると自動でGoogle翻訳 → output/ に保存",
                 font=F(10), fg="#fca5a5", bg="#b91c1c").pack(pady=(3, 0))

        body = tk.Frame(self.root, bg="#fdf8f0", padx=22, pady=16)
        body.pack(fill="both", expand=True)

        # フォルダ行
        for icon, label, path in [
            ("📥", "入力フォルダ", INPUT_DIR),
            ("📤", "出力フォルダ", OUTPUT_DIR),
        ]:
            row = tk.Frame(body, bg="#fff9f0", bd=1, relief="solid")
            row.pack(fill="x", pady=4)
            tk.Label(row, text=f"{icon} {label}", bg="#fff9f0", fg="#7f1d1d",
                     font=F(11, bold=True), width=14, anchor="w",
                     padx=10, pady=8).pack(side="left")
            tk.Label(row, text=str(path), bg="#fff9f0", fg="#2c1810",
                     font=(FONT_MONO, 10), anchor="w", padx=4).pack(
                         side="left", fill="x", expand=True)
            tk.Button(row, text="開く", bg="#b91c1c", fg="white", relief="flat",
                      padx=10, font=F(11),
                      command=lambda p=path: open_folder(p)
                      ).pack(side="right", padx=6, pady=4)

        # 言語バッジ
        lang_f = tk.Frame(body, bg="#fdf8f0")
        lang_f.pack(fill="x", pady=(10, 2))
        tk.Label(lang_f, text="翻訳言語：", bg="#fdf8f0", fg="#92400e",
                 font=F(12)).pack(side="left")
        for code, name in TARGET_LANGS.items():
            tk.Label(lang_f, text=f"✓ {name}",
                     bg="#fde8d0", fg="#7f1d1d",
                     font=F(11, bold=True),
                     padx=8, pady=3,
                     relief="flat").pack(side="left", padx=4)

        # ボタン群
        btn_f = tk.Frame(body, bg="#fdf8f0")
        btn_f.pack(pady=12)
        self.watch_btn = tk.Button(
            btn_f, text="▶  監視を開始する",
            bg="#166534", fg="white", relief="flat",
            padx=18, pady=10, font=F(14, bold=True),
            command=self._toggle)
        self.watch_btn.pack(side="left", padx=6)

        tk.Button(btn_f, text="📂  今すぐ全処理",
                  bg="#1e40af", fg="white", relief="flat",
                  padx=14, pady=10, font=F(13),
                  command=self._process_all).pack(side="left", padx=6)

        # ステータス
        self.status_var = tk.StringVar(value="⏸  停止中")
        tk.Label(body, textvariable=self.status_var,
                 bg="#fdf8f0", fg="#6b7280", font=F(11)).pack()

        # ログ
        tk.Label(body, text="処理ログ", bg="#fdf8f0", fg="#7f1d1d",
                 font=F(11, bold=True), anchor="w").pack(fill="x", pady=(10, 3))
        self.log_box = scrolledtext.ScrolledText(
            body, height=10,
            font=(FONT_MONO, 10),
            bg="#fff9f0", fg="#2c1810",
            relief="solid", bd=1)
        self.log_box.pack(fill="both", expand=True)

    # ── 起動チェック ──────────────────────────────────
    def _startup_check(self):
        self._log(f"起動しました  [{platform.system()} / Python {sys.version.split()[0]}]")
        missing = []
        if not WATCHDOG_OK:   missing.append("watchdog")
        if not TRANSLATOR_OK: missing.append("deep-translator")
        if missing:
            self._log(f"⚠ 未インストール: {', '.join(missing)}")
            self._log("  → コマンドプロンプトで: pip install " + " ".join(missing))
        else:
            self._log("✅ 準備完了 — 「監視を開始する」を押してください")
        self._log(f"   入力: {INPUT_DIR}")
        self._log(f"   出力: {OUTPUT_DIR}")

    def _log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_box.insert("end", f"[{ts}]  {msg}\n")
        self.log_box.see("end")

    # ── 監視 ──────────────────────────────────────────
    def _toggle(self):
        if self.watching:
            self._stop()
        else:
            self._start()

    def _start(self):
        if not WATCHDOG_OK or not TRANSLATOR_OK:
            messagebox.showerror("エラー",
                "必要なライブラリが不足しています。\nログを確認してください。")
            return
        handler = _Handler(self)
        self.observer = Observer()
        self.observer.schedule(handler, str(INPUT_DIR), recursive=False)
        self.observer.start()
        self.watching = True
        self.watch_btn.config(text="■  監視を停止する", bg="#991b1b")
        self.status_var.set("🟢  監視中 — input フォルダを監視しています")
        self._log("監視を開始しました")

    def _stop(self):
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None
        self.watching = False
        self.watch_btn.config(text="▶  監視を開始する", bg="#166534")
        self.status_var.set("⏸  停止中")
        self._log("監視を停止しました")

    def _process_all(self):
        files = list(INPUT_DIR.glob("*.txt"))
        if not files:
            self._log("input フォルダにテキストファイルが見つかりません")
            return
        for f in files:
            threading.Thread(target=self.translate_file, args=(f,), daemon=True).start()

    # ── 翻訳処理 ──────────────────────────────────────
    def translate_file(self, path: Path):
        self.root.after(0, self._log, f"━━ 翻訳開始: {path.name}")
        try:
            text = _read_auto(path)
            if text is None:
                self.root.after(0, self._log, f"❌ 文字コード判定失敗: {path.name}")
                return

            lines = text.splitlines()
            self.root.after(0, self._log, f"   {len(lines)} 行を読み込みました")

            for lang_code, lang_name in TARGET_LANGS.items():
                tr = GoogleTranslator(source="ja", target=lang_code)
                out_lines = []
                for line in lines:
                    if line.strip():
                        try:
                            out_lines.append(tr.translate(line))
                        except Exception:
                            out_lines.append(line)
                    else:
                        out_lines.append("")

                out_name = f"{path.stem}_{lang_code}{path.suffix}"
                out_path = OUTPUT_DIR / out_name
                out_path.write_text("\n".join(out_lines), encoding="utf-8-sig")
                self.root.after(0, self._log, f"   ✓ {lang_name} → {out_name}")

            self.root.after(0, self._log, f"✅ 完了: {path.name}")

        except Exception as e:
            self.root.after(0, self._log, f"❌ エラー: {e}")

    def on_close(self):
        self._stop()
        self.root.destroy()


# ── フォルダ監視 ─────────────────────────────────────
class _Handler(FileSystemEventHandler):
    def __init__(self, app: App):
        self.app = app
        self._seen: set = set()

    def on_created(self, event):
        path = Path(event.src_path)
        if not event.is_directory and path.suffix.lower() == ".txt":
            key = str(path)
            if key not in self._seen:
                self._seen.add(key)
                time.sleep(0.5)
                threading.Thread(
                    target=self.app.translate_file, args=(path,), daemon=True
                ).start()


# ── ユーティリティ ────────────────────────────────────
def _read_auto(path: Path):
    for enc in ("utf-8-sig", "utf-8", "shift-jis", "cp932"):
        try:
            return path.read_text(encoding=enc)
        except (UnicodeDecodeError, Exception):
            continue
    return None

def open_folder(path: Path):
    if IS_WINDOWS:
        os.startfile(str(path))
    else:
        import subprocess
        subprocess.run(["open", str(path)])


# ─────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()
