#!/bin/bash
cd "$(dirname "$0")"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  研修生チェックリスト 翻訳システム"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "▶ ローカルサーバーを起動中..."
echo "  URL: http://localhost:8765/翻訳システム.html"
echo ""
echo "  ブラウザが自動で開きます。"
echo "  終了するには このウィンドウを閉じてください。"
echo ""

# ブラウザを自動で開く（1秒待ってから）
sleep 1 && open "http://localhost:8765/翻訳システム.html" &

# Pythonサーバー起動
python3 -m http.server 8765
