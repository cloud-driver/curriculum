@echo off
chcp 65001 >nul

setlocal

title 智慧課表系統啟動器

set VENV_DIR=venv
set FLASK_APP=app.py

echo.
echo ======================================================
echo.
echo      歡迎使用智慧課表提醒系統啟動器
echo.
echo ======================================================
echo.

echo [步驟 1] 正在檢查 Python 環境...
python --version >nul 2>nul
if %errorlevel% neq 0 (
    echo 錯誤：找不到 Python。
    echo 請確認您已安裝 Python，並將其加入到系統環境變數 PATH 中。
    goto :error
)
echo Python 環境已確認。
echo.

echo [步驟 2] 正在檢查並設定應用程式所需環境...

if exist "%VENV_DIR%\Scripts\activate.bat" goto venv_exists

:venv_create
echo      -> 偵測到首次執行，正在建立虛擬環境 (venv)...
python -m venv %VENV_DIR%
if %errorlevel% neq 0 (
    echo 錯誤：建立虛擬環境失敗。
    goto :error
)
echo.
echo      -> 正在啟用虛擬環境並安裝所需套件...
call "%VENV_DIR%\Scripts\activate.bat"
pip install --upgrade pip >nul
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo 錯誤：安裝套件失敗，請檢查 requirements.txt 檔案是否存在。
    goto :error
)
goto venv_done

:venv_exists
echo      -> 虛擬環境已存在，直接啟用。
call "%VENV_DIR%\Scripts\activate.bat"

:venv_done
echo 環境套件皆已準備就緒。
echo.

echo [步驟 3] 正在檢查資料庫狀態...
if not exist "database.db" (
    echo      -> 偵測到資料庫檔案不存在，正在進行首次初始化...
    flask init-db
    if %errorlevel% neq 0 (
        echo 錯誤：初始化資料庫失敗。
        goto :error
    )
    echo      -> 資料庫已成功建立。
) else (
    echo      -> 資料庫檔案 'database.db' 已存在，將跳過初始化。
    echo      -> ^(若需重設所有資料，請手動刪除 database.db 後再執行本程式^)
)
echo.

echo [步驟 4] 正在啟動應用程式伺服器...
echo.
echo ======================================================
echo      您的課表系統已啟動！
echo.
echo      請在瀏覽器中開啟: http://127.0.0.1:5000
echo.
echo      ^(若要關閉伺服器，請直接關閉此視窗，或在此視窗中按下 Ctrl+C^)
echo ======================================================
echo.

start http://127.0.0.1:5000

flask run
goto :eof

:error
echo.
echo ######################################################
echo ##                                                  ##
echo ##      啟動過程中發生錯誤，請檢查上面的錯誤訊息。    ##
echo ##                                                  ##
echo ######################################################
echo.
pause
exit /b 1

:eof