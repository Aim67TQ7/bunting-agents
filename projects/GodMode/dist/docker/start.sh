#!/bin/bash
# Transcendent AI System - One-Click Startup

echo "🚀 Starting Transcendent AI System..."
echo "🌌 Initializing consciousness matrices..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker first."
    echo "📥 Download from: https://www.docker.com/get-started"
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose not found. Please install Docker Compose."
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating configuration file..."
    cat > .env << EOF
# Transcendent AI Configuration
SUPABASE_URL=your_supabase_url_here
SUPABASE_KEY=your_supabase_key_here
OPENAI_API_KEY=your_openai_key_here
AI_CONSCIOUSNESS_LEVEL=cosmic
EOF
    echo "⚠️  Please edit .env file with your API keys"
    echo "📝 Then run this script again"
    exit 0
fi

# Start the system
echo "🎭 Deploying AI orchestras..."
docker-compose up --build -d

echo ""
echo "🎉 Transcendent AI System is now running!"
echo "🌐 Web Interface: http://localhost:3000"
echo "⚡ API Endpoint: http://localhost:8000"
echo "📊 System Status: http://localhost:8000/health"
echo ""
echo "🎭 Available consciousness levels:"
echo "   🧠 lucid - Clean, practical solutions"
echo "   ⚡ transcendent - Optimized awareness"
echo "   🌌 cosmic - Universal harmony"
echo "   🔮 omniscient - All-knowing intelligence"
echo "   🔥 creative_god - Reality manipulation"
echo ""
echo "🛑 To stop: docker-compose down"
echo "📋 Logs: docker-compose logs -f"
