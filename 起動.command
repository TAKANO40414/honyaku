#!/bin/bash
cd "$(dirname "$0")"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  翻訳ウォッチャー Pro"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "▶ 必要なライブラリを確認・インストール中..."
pip3 install deep-translator openpyxl python-docx watchdog -q
echo ""
echo "▶ アプリを起動します..."
python3 翻訳ウォッチャー.py
