#!/bin/bash
cd "$(dirname "$0")"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  研修生チェックリスト 翻訳ウォッチャー"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "▶ 必要なライブラリを確認・インストール中..."
pip3 install deep-translator watchdog -q
echo ""
echo "▶ アプリを起動します..."
python3 翻訳ウォッチャー.py
