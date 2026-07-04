@echo off
chcp 65001 > nul
echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo   翻訳ウォッチャー Pro
echo   EXEファイル作成スクリプト
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.

python --version > nul 2>&1
if errorlevel 1 (
    echo [エラー] Python が見つかりません。
    echo   https://www.python.org からインストールしてください。
    pause & exit /b 1
)

echo [1/3] 必要なライブラリをインストール中...
pip install deep-translator openpyxl python-docx watchdog pyinstaller --quiet
if errorlevel 1 ( echo インストール失敗 & pause & exit /b 1 )
echo       完了

echo.
echo [2/3] EXEファイルを作成中（数分かかります）...
pyinstaller --onedir --windowed --name "翻訳ウォッチャーPro" --clean 翻訳ウォッチャー.py
if errorlevel 1 ( echo EXE作成失敗 & pause & exit /b 1 )
echo       完了

echo.
echo [3/3] 配布用フォルダを整理中...
if not exist "dist\翻訳ウォッチャーPro\input"  mkdir "dist\翻訳ウォッチャーPro\input"
if not exist "dist\翻訳ウォッチャーPro\output" mkdir "dist\翻訳ウォッチャーPro\output"

(
echo 【翻訳ウォッチャー Pro  使い方】
echo.
echo ■ 対応ファイル形式
echo   テキスト (.txt) / Excel (.xlsx .xls) / Word (.docx .doc)
echo.
echo ■ 基本の使い方
echo   1. 翻訳ウォッチャーPro.exe を起動
echo   2. 「監視 開始」ボタンを押す
echo   3. input フォルダにファイルを入れる
echo   4. output フォルダに翻訳済みファイルが自動保存される
echo.
echo ■ 注意
echo   Google翻訳はインターネット接続が必要です。
) > "dist\翻訳ウォッチャーPro\使い方.txt"

echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo   完成！  dist\翻訳ウォッチャーPro\ を配布してください。
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
pause
