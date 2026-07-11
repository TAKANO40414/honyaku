#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
研修生チェックリスト 多言語翻訳システム
Oracle/FileMaker から出力された CSV を自動翻訳し、
多言語チェックリストを生成する。
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import threading
import time
import json
from datetime import datetime

try:
    import pandas as pd
    PANDAS_OK = True
except ImportError:
    PANDAS_OK = False

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_OK = True
except ImportError:
    WATCHDOG_OK = False

try:
    from deep_translator import GoogleTranslator
    TRANSLATOR_OK = True
except ImportError:
    TRANSLATOR_OK = False

LANG_OPTIONS = {
    "ベトナム語":     "vi",
    "中国語（簡体）": "zh-CN",
    "中国語（繁体）": "zh-TW",
    "英語":          "en",
    "翻訳しない":    None,
}

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

# ─────────────────────────────────────────
#  メインアプリ
# ─────────────────────────────────────────
class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("研修生チェックリスト 多言語翻訳システム")
        self.root.geometry("740x640")
        self.root.resizable(True, True)
        self.root.configure(bg="#fdf8f0")

        self.observer = None
        self.watching = False
        self.cfg = self._load_config()
        self._build_ui()
        self._check_deps()

    # ── 設定 ──────────────────────────────
    def _load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "input_folder":       "",
            "output_folder":      "",
            "lang1":              "ベトナム語",
            "lang2":              "中国語（簡体）",
            "translate_columns":  "注意点,作業手順,品名",
        }

    def _save_config(self):
        self.cfg.update({
            "input_folder":      self.v_input.get(),
            "output_folder":     self.v_output.get(),
            "lang1":             self.v_lang1.get(),
            "lang2":             self.v_lang2.get(),
            "translate_columns": self.v_cols.get(),
        })
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.cfg, f, ensure_ascii=False, indent=2)
        self._log("設定を保存しました")

    # ── UI構築 ────────────────────────────
    def _build_ui(self):
        # タイトルバー
        title_bar = tk.Frame(self.root, bg="#b91c1c", pady=14)
        title_bar.pack(fill="x")
        tk.Label(title_bar, text="研修生チェックリスト  多言語翻訳システム",
                 font=("Hiragino Mincho ProN", 17, "bold"),
                 fg="white", bg="#b91c1c").pack()
        tk.Label(title_bar, text="FileMaker CSV → 自動翻訳 → ベトナム語・中国語 チェックリスト生成",
                 font=("Hiragino Kaku Gothic ProN", 10),
                 fg="#fca5a5", bg="#b91c1c").pack(pady=(2, 0))

        main = tk.Frame(self.root, bg="#fdf8f0", padx=24, pady=18)
        main.pack(fill="both", expand=True)
        main.columnconfigure(1, weight=1)

        # ── フォルダ設定 ──
        self._section(main, "📁  フォルダ設定", row=0)

        self.v_input  = self._folder_row(main, "入力フォルダ",  self.cfg["input_folder"],  row=1)
        self.v_output = self._folder_row(main, "出力フォルダ", self.cfg["output_folder"], row=2)

        ttk.Separator(main).grid(row=3, column=0, columnspan=3, sticky="ew", pady=14)

        # ── 翻訳設定 ──
        self._section(main, "🌐  翻訳設定", row=4)

        lang_frame = tk.Frame(main, bg="#fdf8f0")
        lang_frame.grid(row=5, column=0, columnspan=3, sticky="w", pady=(0, 6))
        for i, (lbl, attr, default) in enumerate([
            ("言語①", "v_lang1", self.cfg["lang1"]),
            ("言語②", "v_lang2", self.cfg["lang2"]),
        ]):
            tk.Label(lang_frame, text=lbl, bg="#fdf8f0", fg="#2c1810",
                     font=("Hiragino Kaku Gothic ProN", 12)).grid(row=0, column=i*2, padx=(0 if i==0 else 24, 6))
            var = tk.StringVar(value=default)
            setattr(self, attr, var)
            ttk.Combobox(lang_frame, textvariable=var,
                         values=list(LANG_OPTIONS.keys()),
                         state="readonly", width=18,
                         font=("Hiragino Kaku Gothic ProN", 11)).grid(row=0, column=i*2+1)

        tk.Label(main, text="翻訳する列名", bg="#fdf8f0", fg="#2c1810",
                 font=("Hiragino Kaku Gothic ProN", 12)).grid(row=6, column=0, sticky="e", padx=(0, 8))
        self.v_cols = tk.StringVar(value=self.cfg["translate_columns"])
        tk.Entry(main, textvariable=self.v_cols, font=("Hiragino Kaku Gothic ProN", 11)
                 ).grid(row=6, column=1, sticky="ew")
        tk.Label(main, text="※ カンマ区切り", bg="#fdf8f0", fg="#9ca3af",
                 font=("Hiragino Kaku Gothic ProN", 10)).grid(row=6, column=2, padx=(8, 0))

        ttk.Separator(main).grid(row=7, column=0, columnspan=3, sticky="ew", pady=14)

        # ── 操作ボタン ──
        btn_frame = tk.Frame(main, bg="#fdf8f0")
        btn_frame.grid(row=8, column=0, columnspan=3)

        self.watch_btn = self._btn(btn_frame, "▶  自動監視 開始", self._toggle_watch, "#166534")
        self._btn(btn_frame, "📂  手動処理",        self._manual_process,  "#1e40af")
        self._btn(btn_frame, "👁  出力を開く",       self._open_output,     "#78350f")
        self._btn(btn_frame, "💾  設定保存",        self._save_config,     "#4b5563", small=True)

        ttk.Separator(main).grid(row=9, column=0, columnspan=3, sticky="ew", pady=(14, 6))

        # ── ログ ──
        self._section(main, "📋  処理ログ", row=10)
        self.log_box = scrolledtext.ScrolledText(
            main, height=9, font=("Courier", 11),
            bg="#fff9f0", fg="#2c1810", relief="solid", bd=1)
        self.log_box.grid(row=11, column=0, columnspan=3, sticky="nsew", pady=(4, 0))
        main.rowconfigure(11, weight=1)

    def _section(self, parent, text, row):
        tk.Label(parent, text=text,
                 font=("Hiragino Kaku Gothic ProN", 13, "bold"),
                 bg="#fdf8f0", fg="#7f1d1d"
                 ).grid(row=row, column=0, columnspan=3, sticky="w", pady=(0, 6))

    def _folder_row(self, parent, label, default, row):
        var = tk.StringVar(value=default)
        tk.Label(parent, text=label, bg="#fdf8f0", fg="#2c1810",
                 font=("Hiragino Kaku Gothic ProN", 12)
                 ).grid(row=row, column=0, sticky="e", padx=(0, 8), pady=3)
        tk.Entry(parent, textvariable=var,
                 font=("Hiragino Kaku Gothic ProN", 11)
                 ).grid(row=row, column=1, sticky="ew", pady=3)
        tk.Button(parent, text="参照", command=lambda v=var: self._browse(v),
                  bg="#b91c1c", fg="white", relief="flat", padx=10,
                  font=("Hiragino Kaku Gothic ProN", 11)
                  ).grid(row=row, column=2, padx=(6, 0), pady=3)
        return var

    def _btn(self, parent, text, cmd, color, small=False):
        b = tk.Button(parent, text=text, command=cmd,
                      bg=color, fg="white", relief="flat",
                      padx=14, pady=7 if not small else 5,
                      font=("Hiragino Kaku Gothic ProN", 13 if not small else 11))
        b.pack(side="left", padx=5)
        return b

    # ── ログ ──────────────────────────────
    def _log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_box.insert("end", f"[{ts}]  {msg}\n")
        self.log_box.see("end")

    # ── フォルダ参照 ──────────────────────
    def _browse(self, var):
        path = filedialog.askdirectory()
        if path:
            var.set(path)

    # ── 依存確認 ──────────────────────────
    def _check_deps(self):
        self._log("起動しました")
        missing = []
        if not PANDAS_OK:    missing.append("pandas")
        if not WATCHDOG_OK:  missing.append("watchdog")
        if not TRANSLATOR_OK: missing.append("deep-translator")
        if missing:
            self._log(f"⚠ 未インストール: {', '.join(missing)}")
            self._log("  → ターミナルで: pip install " + " ".join(missing))
        else:
            self._log("✅ 必要なライブラリはすべて揃っています")

    # ── 自動監視 ──────────────────────────
    def _toggle_watch(self):
        if self.watching:
            self._stop_watch()
        else:
            self._start_watch()

    def _start_watch(self):
        if not WATCHDOG_OK:
            messagebox.showerror("エラー", "watchdog が未インストールです。\npip install watchdog を実行してください。")
            return
        folder = self.v_input.get()
        if not folder or not os.path.isdir(folder):
            messagebox.showerror("エラー", "入力フォルダを正しく設定してください。")
            return
        handler = _CSVHandler(self)
        self.observer = Observer()
        self.observer.schedule(handler, folder, recursive=False)
        self.observer.start()
        self.watching = True
        self.watch_btn.config(text="■  自動監視 停止", bg="#991b1b")
        self._log(f"自動監視を開始: {folder}")

    def _stop_watch(self):
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None
        self.watching = False
        self.watch_btn.config(text="▶  自動監視 開始", bg="#166534")
        self._log("自動監視を停止しました")

    # ── 手動処理 ──────────────────────────
    def _manual_process(self):
        paths = filedialog.askopenfilenames(
            title="CSVファイルを選択",
            filetypes=[("CSV", "*.csv"), ("All", "*.*")])
        for p in paths:
            threading.Thread(target=self._process, args=(p,), daemon=True).start()

    # ── CSV処理・翻訳 ─────────────────────
    def _process(self, filepath: str):
        self.root.after(0, self._log, f"━━ 処理開始: {os.path.basename(filepath)}")

        if not PANDAS_OK:
            self.root.after(0, self._log, "❌ pandas が未インストールです")
            return

        try:
            # 読み込み（UTF-8 / Shift-JIS 自動判定）
            for enc in ("utf-8-sig", "shift-jis", "cp932", "utf-8"):
                try:
                    df = pd.read_csv(filepath, encoding=enc)
                    break
                except (UnicodeDecodeError, Exception):
                    continue
            else:
                self.root.after(0, self._log, "❌ ファイルを読み込めませんでした（文字コード不明）")
                return

            self.root.after(0, self._log, f"   列: {', '.join(df.columns.tolist())}")
            self.root.after(0, self._log, f"   {len(df)} 行を読み込みました")

            # 翻訳対象列
            target_cols = [c.strip() for c in self.v_cols.get().split(",") if c.strip()]

            # 出力先
            out_dir = self.v_output.get()
            if not out_dir:
                out_dir = os.path.dirname(filepath)
            os.makedirs(out_dir, exist_ok=True)

            base = os.path.splitext(os.path.basename(filepath))[0]
            ts   = datetime.now().strftime("%Y%m%d_%H%M%S")

            # 各言語で出力
            for lang_name, attr in [("言語①", "v_lang1"), ("言語②", "v_lang2")]:
                lang_label = getattr(self, attr).get()
                lang_code  = LANG_OPTIONS.get(lang_label)
                if not lang_code:
                    continue

                translated = df.copy()

                for col in target_cols:
                    if col not in df.columns:
                        self.root.after(0, self._log, f"   ⚠ 列 '{col}' はCSVに存在しません")
                        continue
                    if TRANSLATOR_OK:
                        tr = GoogleTranslator(source="ja", target=lang_code)
                        def _translate(cell, t=tr):
                            if pd.isna(cell) or str(cell).strip() == "":
                                return cell
                            try:
                                return t.translate(str(cell))
                            except Exception:
                                return cell
                        translated[col] = df[col].apply(_translate)
                        self.root.after(0, self._log, f"   ✓ '{col}' → {lang_label}")
                    else:
                        self.root.after(0, self._log, f"   ⚠ deep-translator 未インストール: '{col}' はそのまま出力")

                # CSV 出力
                csv_out = os.path.join(out_dir, f"{base}_{lang_code}_{ts}.csv")
                translated.to_csv(csv_out, index=False, encoding="utf-8-sig")
                self.root.after(0, self._log, f"   📄 CSV: {os.path.basename(csv_out)}")

                # HTML チェックリスト出力
                html_out = os.path.join(out_dir, f"{base}_{lang_code}_{ts}.html")
                self._write_html(translated, html_out, lang_label, os.path.basename(filepath))
                self.root.after(0, self._log, f"   📋 HTML: {os.path.basename(html_out)}")

            self.root.after(0, self._log, "✅ 完了")

        except Exception as e:
            self.root.after(0, self._log, f"❌ エラー: {e}")

    # ── HTML チェックリスト生成 ────────────
    def _write_html(self, df, out_path: str, lang_name: str, source: str):
        headers_html = "".join(f"<th>{c}</th>" for c in df.columns)
        rows_html = ""
        for i, row in df.iterrows():
            cells = "".join(f"<td>{'' if pd.isna(v) else v}</td>" for v in row.values)
            rows_html += (
                f'<tr><td class="num">{i+1}</td>{cells}'
                f'<td class="chk"><label class="cb"><input type="checkbox"></label></td></tr>\n'
            )
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>チェックリスト — {lang_name}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: "Hiragino Kaku Gothic ProN", "Meiryo", sans-serif;
          background: #fdf8f0; padding: 24px; color: #2c1810; }}
  .card {{ background: #fff; border-radius: 10px; overflow: hidden;
           box-shadow: 0 2px 12px rgba(0,0,0,.1); }}
  .head {{ background: #b91c1c; color: #fff; padding: 16px 24px; }}
  .head h1 {{ font-size: 20px; letter-spacing: .1em; }}
  .head p  {{ font-size: 12px; opacity: .75; margin-top: 4px; }}
  table {{ width: 100%; border-collapse: collapse; }}
  thead th {{ background: #7f1d1d; color: #fff; padding: 10px 12px;
              font-size: 13px; text-align: left; white-space: nowrap; }}
  tbody td {{ padding: 10px 12px; border-bottom: 1px solid #f4c7b0;
              font-size: 13px; vertical-align: top; }}
  tbody tr:hover td {{ background: #fdf3e7; }}
  .num {{ color: #92400e; font-weight: bold; width: 40px; text-align: center; }}
  .chk {{ width: 50px; text-align: center; }}
  .cb input {{ width: 20px; height: 20px; accent-color: #b91c1c; cursor: pointer; }}
  .progress {{ display: flex; align-items: center; gap: 12px;
               padding: 12px 24px; background: #fff9f0; border-top: 1px solid #f4c7b0; }}
  .progress-bar {{ flex: 1; height: 8px; background: #fde8d0; border-radius: 4px; overflow: hidden; }}
  .progress-fill {{ height: 100%; background: #b91c1c; border-radius: 4px;
                    transition: width .3s; width: 0%; }}
  .progress-label {{ font-size: 12px; color: #92400e; white-space: nowrap; }}
  .footer {{ padding: 8px 24px; font-size: 11px; color: #9ca3af; text-align: right;
             background: #fff9f0; }}
  @media print {{
    body {{ background: #fff; padding: 0; }}
    .progress, .footer {{ display: none; }}
    .card {{ box-shadow: none; }}
  }}
</style>
</head>
<body>
<div class="card">
  <div class="head">
    <h1>チェックリスト &mdash; {lang_name}</h1>
    <p>元ファイル: {source} &nbsp;／&nbsp; 出力日時: {now}</p>
  </div>
  <table>
    <thead><tr><th>No.</th>{headers_html}<th>確認</th></tr></thead>
    <tbody id="tbody">{rows_html}</tbody>
  </table>
  <div class="progress">
    <div class="progress-bar"><div class="progress-fill" id="bar"></div></div>
    <div class="progress-label" id="prog">0 / {len(df)} 完了</div>
  </div>
  <div class="footer">印刷: Ctrl+P &nbsp;｜&nbsp; チェック状態はこのページを開いている間のみ保持されます</div>
</div>
<script>
  const total = {len(df)};
  function update() {{
    const checked = document.querySelectorAll('input[type=checkbox]:checked').length;
    document.getElementById('bar').style.width = (checked/total*100)+'%';
    document.getElementById('prog').textContent = checked+' / '+total+' 完了';
  }}
  document.getElementById('tbody').addEventListener('change', update);
</script>
</body>
</html>"""
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)

    # ── 出力フォルダを開く ────────────────
    def _open_output(self):
        folder = self.v_output.get()
        if folder and os.path.isdir(folder):
            os.system(f'open "{folder}"')
        else:
            messagebox.showinfo("情報", "出力フォルダが設定されていません。")

    # ── 終了処理 ──────────────────────────
    def on_close(self):
        self._stop_watch()
        self._save_config()
        self.root.destroy()


# ─────────────────────────────────────────
#  フォルダ監視ハンドラ
# ─────────────────────────────────────────
class _CSVHandler(FileSystemEventHandler):
    def __init__(self, app: App):
        self.app = app
        self._seen: set = set()

    def on_created(self, event):
        if event.is_directory:
            return
        path = event.src_path
        if path.lower().endswith(".csv") and path not in self._seen:
            self._seen.add(path)
            time.sleep(0.8)  # 書き込み完了を待つ
            threading.Thread(target=self.app._process, args=(path,), daemon=True).start()


# ─────────────────────────────────────────
#  エントリポイント
# ─────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()
