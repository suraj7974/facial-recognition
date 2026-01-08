#!/bin/bash
# Startup script to run both API and WhatsApp bot

echo "Starting Face Recognition System..."
echo ""

# Check if Python virtual environment exists
# if [ ! -d ".venv" ]; then
#     echo "Virtual environment not found. Please create one first."
#     echo "Run: python -m venv .venv"
#     exit 1
# fi

# Check if Node modules are installed for WhatsApp bot
if [ ! -d "client/node_modules" ]; then
    echo "Installing WhatsApp Bot dependencies..."
    (cd client && npm install)
    echo ""
fi

# Check if Node modules are installed for Admin client
if [ ! -d "admin/client/node_modules" ]; then
    echo "Installing Admin Panel dependencies..."
    (cd admin/client && pnpm install)
    echo ""
fi

# Build Admin Panel if dist doesn't exist
if [ ! -d "admin/client/dist" ]; then
    echo "Building Admin Panel..."
    (cd admin/client && pnpm build)
    echo ""
fi

# Start the Flask API in background
echo "Starting Flask API server..."
# source .venv/bin/activate
python server/api_service.py &
API_PID=$!
echo "API started (PID: $API_PID)"
echo ""

# Start the Admin backend server in background
echo "Starting Admin backend server..."
python admin/server/admin.py &
ADMIN_PID=$!
echo "Admin backend started (PID: $ADMIN_PID)"
echo ""

# Start the Admin frontend dev server in background
echo "Starting Admin frontend..."
(cd admin/client && pnpm dev --host) &
ADMIN_CLIENT_PID=$!
echo "Admin frontend started (PID: $ADMIN_CLIENT_PID)"
echo ""

# Wait a bit for API to start
echo "Waiting for API to initialize..."
sleep 5
echo ""

# Start the WhatsApp bot
echo "Starting WhatsApp Bot..."
node client/whatsapp_bot.js &
BOT_PID=$!
echo "WhatsApp Bot started (PID: $BOT_PID)"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "System is running!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "API:           http://localhost:5000"
echo "Admin Backend: http://localhost:5001"
echo "Admin Panel:   http://localhost:5173"
echo "WhatsApp:      Scan QR code above"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Press Ctrl+C to stop all services..."
echo ""

# Function to handle Ctrl+C
cleanup() {
    echo ""
    echo "Stopping services..."
    kill $API_PID 2>/dev/null
    kill $ADMIN_PID 2>/dev/null
    kill $ADMIN_CLIENT_PID 2>/dev/null
    kill $BOT_PID 2>/dev/null
    echo "All services stopped"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Wait for processes
wait
