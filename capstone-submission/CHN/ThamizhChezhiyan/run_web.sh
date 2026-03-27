#!/bin/bash
# Run script for EDPS Modern Web Interface (FastAPI + React)

echo "🚀 Starting EDPS Modern Web Interface..."
echo "📄 Enterprise Document Processing System"
echo "🌐 FastAPI Backend + React Frontend"
echo ""

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found. Please run setup first."
    exit 1
fi

# Activate virtual environment
source .venv/bin/activate

# Check if uvicorn is installed
if ! python -c "import uvicorn" 2>/dev/null; then
    echo "📦 Installing uvicorn..."
    pip install uvicorn
fi

# Start FastAPI backend in background
echo "🔧 Starting FastAPI backend on http://localhost:8000"
uvicorn src.api:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Wait a moment for backend to start
sleep 2

# Check if Node.js and npm are available
if ! command -v npm &> /dev/null; then
    echo "❌ npm not found. Please install Node.js and npm to run the React frontend."
    echo "Visit: https://nodejs.org/"
    echo ""
    echo "Backend is running at: http://localhost:8000"
    echo "API docs available at: http://localhost:8000/docs"
    echo ""
    echo "Press Ctrl+C to stop the backend"
    wait $BACKEND_PID
    exit 1
fi

# Check if frontend directory exists
if [ ! -d "frontend" ]; then
    echo "❌ Frontend directory not found."
    exit 1
fi

# Install frontend dependencies if node_modules doesn't exist
if [ ! -d "frontend/node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    cd frontend
    npm install
    cd ..
fi

# Start React frontend in background
echo "⚛️ Starting React frontend on http://localhost:5173"
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

# Wait for services to start
sleep 3

echo ""
echo "✅ Services started successfully!"
echo "🌐 Frontend: http://localhost:3000"
echo "🔧 Backend:  http://localhost:8000"
echo "📚 API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID