@echo off
chcp 65001 > nul
echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo   研修生チェックリスト 翻訳ウォッチャー
echo   EXEファイル作成スクリプト
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.

REM ── Pythonの確認 ────────────────────────────────
python --version > nul 2>&1
if errorlevel 1 (
    echo [エラー] Python が見つかりません。
    echo   https://www.python.org からインストールしてください。
    echo   インストール時に「Add Python to PATH」にチェックを入れてください。
    pause
    exit /b 1
)

echo [1/3] 必要なライブラリをインストール中...
pip install deep-translator watchdog pyinstaller --quiet
if errorlevel 1 (
    echo [エラー] ライブラリのインストールに失敗しました。
    pause
    exit /b 1
)
echo       完了
echo.

echo [2/3] EXEファイルを作成中（数分かかります）...
pyinstaller ^
  --onedir ^
  --windowed ^
  --name "翻訳ウォッチャー" ^
  --clean ^
  翻訳ウォッチャー.py

if errorlevel 1 (
    echo [エラー] EXEの作成に失敗しました。
    pause
    exit /b 1
)
echo       完了
echo.

echo [3/3] 配布用フォルダを整理中...

REM inputとoutputフォルダをEXEと同じ場所に作成
if not exist "dist\翻訳ウォッチャー\input"  mkdir "dist\翻訳ウォッチャー\input"
if not exist "dist\翻訳ウォッチャー\output" mkdir "dist\翻訳ウォッチャー\output"

REM サンプルテキストをコピー
if exist "input\サンプル.txt" (
    copy "input\サンプル.txt" "dist\翻訳ウォッチャー\input\" > nul
)

REM 使い方テキストを作成
(
echo 【研修生チェックリスト 翻訳ウォッチャー 使い方】
echo.
echo 1. 翻訳ウォッチャー.exe をダブルクリックして起動
echo 2. 「監視を開始する」ボタンを押す
echo 3. input フォルダにテキストファイル（.txt）を入れる
echo 4. 自動でGoogle翻訳され、output フォルダに保存される
echo.
echo 【ファイル名のルール】
echo   入力: 作業指示.txt
echo   出力: 作業指示_vi.txt  （ベトナム語）
echo        作業指示_zh-CN.txt（中国語）
echo.
echo 【注意】
echo   インターネット接続が必要です（Google翻訳を使用）
echo   テキストファイルはUTF-8またはShift-JIS形式に対応
) > "dist\翻訳ウォッチャー\使い方.txt"

echo       完了
echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo   完成しました！
echo.
echo   配布するフォルダ:
echo   dist\翻訳ウォッチャー\
echo.
echo   このフォルダをZIPに圧縮して配布してください。
echo   受け取った側はZIPを展開して
echo   翻訳ウォッチャー.exe をダブルクリックするだけです。
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
pause
