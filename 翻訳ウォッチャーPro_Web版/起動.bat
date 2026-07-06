@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================
echo   翻訳ウォッチャー Pro（ブラウザ版）を起動します
echo ============================================
echo.

where python >nul 2>nul
if %errorlevel%==0 (
    python server.py
    goto :end
)

where py >nul 2>nul
if %errorlevel%==0 (
    py server.py
    goto :end
)

echo [エラー] Python が見つかりませんでした。
echo Python 3 をインストールしてから、もう一度実行してください。
echo https://www.python.org/downloads/windows/
pause
exit /b 1

:end
pause
