#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
翻訳ウォッチャー Pro（ブラウザ版）ローカルサーバー

- デスクトップに INPUT / OUTPUT フォルダを自動作成
- ブラウザ(翻訳ウォッチャーPro.html)を静的配信
- INPUTフォルダの一覧取得・ファイル取得、OUTPUTフォルダへの保存をAPIとして提供

Windowsサーバー上でも Python 3 が入っていれば追加インストール無しで動作する
（標準ライブラリのみ使用）。
"""
import http.server
import socketserver
import json
import os
import sys
import threading
import webbrowser
import urllib.parse

PORT = 8765
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DESKTOP = os.path.join(os.path.expanduser("~"), "Desktop")
INPUT_DIR = os.path.join(DESKTOP, "翻訳ウォッチャーPro_INPUT")
OUTPUT_DIR = os.path.join(DESKTOP, "翻訳ウォッチャーPro_OUTPUT")

os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _send_json(self, obj, status=200):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def _safe_path(self, base_dir, name):
        """フォルダの外に出るパス（../等）を弾く"""
        fp = os.path.abspath(os.path.join(base_dir, os.path.basename(name)))
        if not fp.startswith(os.path.abspath(base_dir)):
            return None
        return fp

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == "/api/input-files":
            files = []
            for name in sorted(os.listdir(INPUT_DIR)):
                fp = os.path.join(INPUT_DIR, name)
                if os.path.isfile(fp):
                    files.append({"name": name, "size": os.path.getsize(fp)})
            self._send_json({"files": files, "inputDir": INPUT_DIR, "outputDir": OUTPUT_DIR})
            return

        if parsed.path.startswith("/api/input-file/"):
            name = urllib.parse.unquote(parsed.path[len("/api/input-file/"):])
            fp = self._safe_path(INPUT_DIR, name)
            if not fp or not os.path.isfile(fp):
                self.send_error(404, "File not found")
                return
            with open(fp, "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(data)
            return

        super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path.startswith("/api/output-file/"):
            name = urllib.parse.unquote(parsed.path[len("/api/output-file/"):])
            fp = self._safe_path(OUTPUT_DIR, name)
            if not fp:
                self.send_error(400, "Invalid file name")
                return
            length = int(self.headers.get("Content-Length", 0))
            data = self.rfile.read(length)
            with open(fp, "wb") as f:
                f.write(data)
            self._send_json({"ok": True, "saved": fp})
            return

        if parsed.path.startswith("/api/delete-input/"):
            name = urllib.parse.unquote(parsed.path[len("/api/delete-input/"):])
            fp = self._safe_path(INPUT_DIR, name)
            if fp and os.path.isfile(fp):
                os.remove(fp)
            self._send_json({"ok": True})
            return

        self.send_error(404, "Not found")

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()


def main():
    print("=" * 56)
    print("  翻訳ウォッチャー Pro（ブラウザ版）サーバー")
    print("=" * 56)
    print(f"INPUTフォルダ : {INPUT_DIR}")
    print(f"OUTPUTフォルダ: {OUTPUT_DIR}")
    print(f"URL           : http://localhost:{PORT}/翻訳ウォッチャーPro.html")
    print("(このウィンドウを閉じるとサーバーが停止します)")
    print("=" * 56)

    httpd = socketserver.ThreadingTCPServer(("127.0.0.1", PORT), Handler)
    httpd.allow_reuse_address = True

    def open_browser():
        webbrowser.open(f"http://localhost:{PORT}/翻訳ウォッチャーPro.html")

    threading.Timer(1.0, open_browser).start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n停止しました。")


if __name__ == "__main__":
    main()
