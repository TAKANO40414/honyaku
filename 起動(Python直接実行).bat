@echo off
chcp 65001 > nul
cd /d "%~dp0"

echo ライブラリを確認中...
pip install deep-translator watchdog --quiet

echo 起動中...
python 翻訳ウォッチャー.py
pause
