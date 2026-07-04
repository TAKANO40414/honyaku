#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
研修生チェックリスト 翻訳ウォッチャー
input/ フォルダを監視 → 翻訳（Google翻訳 or LLM）→ output/ に保存
Windows / macOS 両対応
"""

import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk
import threading
import time
import os
import sys
import json
import platform
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
from datetime import datetime

# ── PyInstaller対応 ───────────────────────────────────
def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent

BASE_DIR   = get_base_dir()
INPUT_DIR  = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "output"
CONFIG_FILE = BASE_DIR / "config.json"
INPUT_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# ── 翻訳言語設定 ─────────────────────────────────────
TARGET_LANGS = {
    "vi":    "ベトナム語",
    "zh-CN": "中国語（簡体）",
}

# ── OS別フォント ──────────────────────────────────────
IS_WINDOWS = platform.system() == "Windows"
FONT_UI   = "Yu Gothic UI" if IS_WINDOWS else "Hiragino Kaku Gothic ProN"
FONT_MONO = "MS Gothic"    if IS_WINDOWS else "Courier"

def F(size=12, bold=False):
    return (FONT_UI, size, "bold" if bold else "normal")

# ── ライブラリ確認 ────────────────────────────────────
try:
    from deep_translator import GoogleTranslator
    GOOGLE_OK = True
except ImportError:
    GOOGLE_OK = False

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
        self.root.geometry("660x640")
        self.root.resizable(True, True)
        self.root.configure(bg="#fdf8f0")
        self.observer = None
        self.watching = False
        self.cfg = self._load_config()
        self._build_ui()
        self._startup_check()

    # ── 設定の読み書き ────────────────────────────────
    def _load_config(self):
        default = {
            "engine":     "google",
            "llm_url":    "http://localhost:11434",
            "llm_model":  "llama3.2",
            "llm_api":    "ollama",
        }
        if CONFIG_FILE.exists():
            try:
                saved = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
                default.update(saved)
            except Exception:
                pass
        return default

    def _save_config(self):
        self.cfg["engine"]    = self.engine_var.get()
        self.cfg["llm_url"]   = self.llm_url_var.get()
        self.cfg["llm_model"] = self.llm_model_var.get()
        self.cfg["llm_api"]   = self.llm_api_var.get()
        CONFIG_FILE.write_text(
            json.dumps(self.cfg, ensure_ascii=False, indent=2), encoding="utf-8")

    # ── UI構築 ────────────────────────────────────────
    def _build_ui(self):
        # ヘッダー
        tk.Frame(self.root, bg="#b91c1c", height=4).pack(fill="x")
        hdr = tk.Frame(self.root, bg="#b91c1c", pady=12)
        hdr.pack(fill="x")
        tk.Label(hdr, text="研修生チェックリスト  翻訳ウォッチャー",
                 font=F(16, bold=True), fg="white", bg="#b91c1c").pack()
        tk.Label(hdr, text="input/ にテキストを入れると自動翻訳 → output/ に保存",
                 font=F(10), fg="#fca5a5", bg="#b91c1c").pack(pady=(2, 0))

        body = tk.Frame(self.root, bg="#fdf8f0", padx=22, pady=14)
        body.pack(fill="both", expand=True)

        # ── フォルダ行 ──
        for icon, label, path in [
            ("📥", "入力フォルダ", INPUT_DIR),
            ("📤", "出力フォルダ", OUTPUT_DIR),
        ]:
            row = tk.Frame(body, bg="#fff9f0", bd=1, relief="solid")
            row.pack(fill="x", pady=3)
            tk.Label(row, text=f"{icon} {label}", bg="#fff9f0", fg="#7f1d1d",
                     font=F(11, bold=True), width=14, anchor="w",
                     padx=10, pady=7).pack(side="left")
            tk.Label(row, text=str(path), bg="#fff9f0", fg="#2c1810",
                     font=(FONT_MONO, 10), anchor="w", padx=4).pack(
                         side="left", fill="x", expand=True)
            tk.Button(row, text="開く", bg="#b91c1c", fg="white", relief="flat",
                      padx=10, font=F(11),
                      command=lambda p=path: open_folder(p)
                      ).pack(side="right", padx=6, pady=4)

        # 言語バッジ
        lang_f = tk.Frame(body, bg="#fdf8f0")
        lang_f.pack(fill="x", pady=(8, 2))
        tk.Label(lang_f, text="翻訳言語：", bg="#fdf8f0", fg="#92400e",
                 font=F(12)).pack(side="left")
        for _, name in TARGET_LANGS.items():
            tk.Label(lang_f, text=f"✓ {name}",
                     bg="#fde8d0", fg="#7f1d1d", font=F(11, bold=True),
                     padx=8, pady=2).pack(side="left", padx=4)

        ttk.Separator(body, orient="horizontal").pack(fill="x", pady=10)

        # ── 翻訳エンジン選択 ──
        tk.Label(body, text="翻訳エンジン", bg="#fdf8f0", fg="#7f1d1d",
                 font=F(12, bold=True), anchor="w").pack(fill="x")

        eng_f = tk.Frame(body, bg="#fdf8f0")
        eng_f.pack(fill="x", pady=(6, 0))

        self.engine_var = tk.StringVar(value=self.cfg["engine"])

        # Google翻訳ラジオ
        tk.Radiobutton(eng_f, text="🌐  Google翻訳（インターネット必要）",
                       variable=self.engine_var, value="google",
                       bg="#fdf8f0", fg="#2c1810", font=F(12),
                       activebackground="#fdf8f0",
                       command=self._on_engine_change).pack(anchor="w")

        # LLMラジオ
        tk.Radiobutton(eng_f, text="🤖  ローカルLLM（Ollama・インターネット不要）",
                       variable=self.engine_var, value="llm",
                       bg="#fdf8f0", fg="#2c1810", font=F(12),
                       activebackground="#fdf8f0",
                       command=self._on_engine_change).pack(anchor="w", pady=(4, 0))

        # ── LLM設定パネル ──
        self.llm_frame = tk.Frame(body, bg="#fff9f0", bd=1, relief="solid",
                                  padx=14, pady=10)
        self.llm_frame.pack(fill="x", pady=(6, 0))

        # API種別
        api_row = tk.Frame(self.llm_frame, bg="#fff9f0")
        api_row.pack(fill="x", pady=(0, 6))
        tk.Label(api_row, text="API種別", bg="#fff9f0", fg="#78350f",
                 font=F(11), width=10, anchor="w").pack(side="left")
        self.llm_api_var = tk.StringVar(value=self.cfg["llm_api"])
        ttk.Combobox(api_row, textvariable=self.llm_api_var,
                     values=["ollama", "openai互換（LM Studio等）"],
                     state="readonly", width=22,
                     font=F(11)).pack(side="left", padx=4)

        # URL
        url_row = tk.Frame(self.llm_frame, bg="#fff9f0")
        url_row.pack(fill="x", pady=3)
        tk.Label(url_row, text="URL", bg="#fff9f0", fg="#78350f",
                 font=F(11), width=10, anchor="w").pack(side="left")
        self.llm_url_var = tk.StringVar(value=self.cfg["llm_url"])
        tk.Entry(url_row, textvariable=self.llm_url_var,
                 font=F(11), width=32).pack(side="left", padx=4)

        # モデル名
        model_row = tk.Frame(self.llm_frame, bg="#fff9f0")
        model_row.pack(fill="x", pady=3)
        tk.Label(model_row, text="モデル名", bg="#fff9f0", fg="#78350f",
                 font=F(11), width=10, anchor="w").pack(side="left")
        self.llm_model_var = tk.StringVar(value=self.cfg["llm_model"])
        tk.Entry(model_row, textvariable=self.llm_model_var,
                 font=F(11), width=22).pack(side="left", padx=4)
        tk.Button(model_row, text="接続テスト", bg="#78350f", fg="white",
                  relief="flat", padx=8, font=F(10),
                  command=self._test_llm).pack(side="left", padx=6)
        self.llm_status = tk.Label(model_row, text="", bg="#fff9f0",
                                   fg="#166534", font=F(10))
        self.llm_status.pack(side="left")

        # 初期表示
        self._on_engine_change()

        ttk.Separator(body, orient="horizontal").pack(fill="x", pady=10)

        # ── 操作ボタン ──
        btn_f = tk.Frame(body, bg="#fdf8f0")
        btn_f.pack()
        self.watch_btn = tk.Button(
            btn_f, text="▶  監視を開始する",
            bg="#166534", fg="white", relief="flat",
            padx=18, pady=9, font=F(14, bold=True),
            command=self._toggle)
        self.watch_btn.pack(side="left", padx=6)

        tk.Button(btn_f, text="📂  今すぐ全処理",
                  bg="#1e40af", fg="white", relief="flat",
                  padx=14, pady=9, font=F(13),
                  command=self._process_all).pack(side="left", padx=6)

        # ステータス
        self.status_var = tk.StringVar(value="⏸  停止中")
        tk.Label(body, textvariable=self.status_var,
                 bg="#fdf8f0", fg="#6b7280", font=F(11)).pack(pady=(6, 0))

        # ── ログ ──
        tk.Label(body, text="処理ログ", bg="#fdf8f0", fg="#7f1d1d",
                 font=F(11, bold=True), anchor="w").pack(fill="x", pady=(8, 2))
        self.log_box = scrolledtext.ScrolledText(
            body, height=8, font=(FONT_MONO, 10),
            bg="#fff9f0", fg="#2c1810", relief="solid", bd=1)
        self.log_box.pack(fill="both", expand=True)

    # ── エンジン切替 ─────────────────────────────────
    def _on_engine_change(self):
        if self.engine_var.get() == "llm":
            self.llm_frame.pack(fill="x", pady=(6, 0))
        else:
            self.llm_frame.pack_forget()

    # ── LLM接続テスト ─────────────────────────────────
    def _test_llm(self):
        self.llm_status.config(text="接続中...", fg="#92400e")
        self.root.update()
        url   = self.llm_url_var.get().rstrip("/")
        api   = self.llm_api_var.get()
        try:
            if "openai" in api:
                endpoint = f"{url}/v1/models"
            else:
                endpoint = f"{url}/api/tags"
            req = urllib.request.Request(endpoint, method="GET")
            with urllib.request.urlopen(req, timeout=5) as res:
                data = json.loads(res.read())
            if "openai" in api:
                count = len(data.get("data", []))
            else:
                count = len(data.get("models", []))
            self.llm_status.config(
                text=f"✓ 接続OK（{count}モデル）", fg="#166534")
        except Exception as e:
            self.llm_status.config(text=f"✗ 失敗: {e}", fg="#991b1b")

    # ── 起動チェック ──────────────────────────────────
    def _startup_check(self):
        self._log(f"起動しました [{platform.system()} / Python {sys.version.split()[0]}]")
        if not WATCHDOG_OK:
            self._log("⚠ watchdog 未インストール → pip install watchdog")
        if not GOOGLE_OK:
            self._log("⚠ deep-translator 未インストール → pip install deep-translator")
        if WATCHDOG_OK:
            self._log("✅ 準備完了 — エンジンを選んで「監視を開始する」を押してください")
        self._log(f"   入力: {INPUT_DIR}")
        self._log(f"   出力: {OUTPUT_DIR}")

    def _log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_box.insert("end", f"[{ts}]  {msg}\n")
        self.log_box.see("end")

    # ── 監視 ─────────────────────────────────────────
    def _toggle(self):
        if self.watching:
            self._stop()
        else:
            self._start()

    def _start(self):
        if not WATCHDOG_OK:
            messagebox.showerror("エラー", "watchdog が未インストールです。\npip install watchdog を実行してください。")
            return
        if self.engine_var.get() == "google" and not GOOGLE_OK:
            messagebox.showerror("エラー", "deep-translator が未インストールです。\npip install deep-translator を実行してください。")
            return
        self._save_config()
        handler = _Handler(self)
        self.observer = Observer()
        self.observer.schedule(handler, str(INPUT_DIR), recursive=False)
        self.observer.start()
        self.watching = True
        engine_label = "Google翻訳" if self.engine_var.get() == "google" else f"LLM({self.llm_model_var.get()})"
        self.watch_btn.config(text="■  監視を停止する", bg="#991b1b")
        self.status_var.set(f"🟢  監視中 [{engine_label}]")
        self._log(f"監視開始 — 翻訳エンジン: {engine_label}")

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
        self._save_config()
        for f in files:
            threading.Thread(target=self.translate_file, args=(f,), daemon=True).start()

    # ── 翻訳処理 ─────────────────────────────────────
    def translate_file(self, path: Path):
        self.root.after(0, self._log, f"━━ 翻訳開始: {path.name}")
        try:
            text = _read_auto(path)
            if text is None:
                self.root.after(0, self._log, f"❌ 文字コード判定失敗: {path.name}")
                return

            lines = text.splitlines()
            self.root.after(0, self._log, f"   {len(lines)} 行を読み込みました")

            engine = self.cfg.get("engine", "google")

            for lang_code, lang_name in TARGET_LANGS.items():
                out_lines = []
                for line in lines:
                    if line.strip():
                        if engine == "google":
                            out_lines.append(self._google(line, lang_code))
                        else:
                            out_lines.append(self._llm(line, lang_name))
                    else:
                        out_lines.append("")

                out_name = f"{path.stem}_{lang_code}{path.suffix}"
                out_path = OUTPUT_DIR / out_name
                out_path.write_text("\n".join(out_lines), encoding="utf-8-sig")
                self.root.after(0, self._log, f"   ✓ {lang_name} → {out_name}")

            self.root.after(0, self._log, f"✅ 完了: {path.name}")

        except Exception as e:
            self.root.after(0, self._log, f"❌ エラー: {e}")

    # ── Google翻訳 ────────────────────────────────────
    def _google(self, text: str, lang_code: str) -> str:
        if not GOOGLE_OK:
            return text
        try:
            return GoogleTranslator(source="ja", target=lang_code).translate(text)
        except Exception:
            return text

    # ── LLM翻訳 ──────────────────────────────────────
    def _llm(self, text: str, lang_name: str) -> str:
        url   = self.cfg.get("llm_url", "http://localhost:11434").rstrip("/")
        model = self.cfg.get("llm_model", "llama3.2")
        api   = self.cfg.get("llm_api", "ollama")
        prompt = (f"以下の日本語テキストを{lang_name}に翻訳してください。"
                  f"翻訳文のみを返してください。説明・注釈は不要です。\n\n{text}")
        try:
            if "openai" in api:
                body = json.dumps({
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                }).encode()
                req = urllib.request.Request(
                    f"{url}/v1/chat/completions",
                    data=body,
                    headers={"Content-Type": "application/json"},
                    method="POST")
                with urllib.request.urlopen(req, timeout=60) as res:
                    data = json.loads(res.read())
                return data["choices"][0]["message"]["content"].strip()
            else:
                body = json.dumps({
                    "model": model, "prompt": prompt, "stream": False
                }).encode()
                req = urllib.request.Request(
                    f"{url}/api/generate",
                    data=body,
                    headers={"Content-Type": "application/json"},
                    method="POST")
                with urllib.request.urlopen(req, timeout=60) as res:
                    data = json.loads(res.read())
                return data.get("response", text).strip()
        except Exception as e:
            return text

    def on_close(self):
        self._stop()
        self._save_config()
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
