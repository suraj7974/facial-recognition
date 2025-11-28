@echo off
title Face Recognition System Starter
echo 🚀 Starting Face Recognition System...
echo.

REM --- CHECK NODE MODULES ---
IF NOT EXIST "client\node_modules" (
    echo 📦 Installing Node.js dependencies...
    cd client
    npm install
    cd ..
    echo.
)

REM --- START FLASK API ---
echo 🐍 Starting Flask API server...
start "" /B python server/api_service.py
set API_PID=%!
echo.

REM --- START ADMIN SERVER ---
echo ⚙️ Starting Admin server...
start "" /B python server/admin/admin.py
set ADMIN_PID=%!
echo.

REM --- WAIT FOR API ---
echo ⏳ Waiting for API to initialize...
timeout /t 5 >nul
echo.

REM --- START WHATSAPP BOT ---
echo 📱 Starting WhatsApp Bot...
start "" /B node client/whatsapp_bot.js
set BOT_PID=%!
echo.

echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo ✨ System is running!
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo 📍 API:        http://localhost:5000
echo ⚙️ Admin:      http://localhost:5001/admin.html
echo 📱 WhatsApp:   Scan QR code above
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
echo Press Ctrl+C and CLOSE window to stop all services...
echo.

REM --- WAIT FOREVER ---
:waitloop
timeout /t 5 >nul
goto waitloop
