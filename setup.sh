#!/bin/bash
# ===========================================
# ImmiAssist AI — Quick Setup Script
# ===========================================

set -e

echo "🇺🇸 ImmiAssist AI — Setting up project..."
echo "============================================"

# 1. Check prerequisites
echo ""
echo "📋 Checking prerequisites..."

command -v python3 >/dev/null 2>&1 || { echo "❌ Python 3.11+ required. Install from python.org"; exit 1; }
command -v node >/dev/null 2>&1 || { echo "❌ Node.js 18+ required. Install from nodejs.org"; exit 1; }

PYTHON_VERSION=$(python3 --version | awk '{print $2}')
NODE_VERSION=$(node --version)
echo "  ✅ Python $PYTHON_VERSION"
echo "  ✅ Node.js $NODE_VERSION"

# 2. Setup environment file
echo ""
if [ ! -f .env ]; then
    cp .env.example .env
    echo "📝 Created .env file from template"
    echo "   ⚠️  IMPORTANT: Add your API keys to .env before running!"
    echo "   Required keys: OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY"
else
    echo "📝 .env file already exists"
fi

# 3. Backend setup
echo ""
echo "🐍 Setting up backend..."
cd backend

if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "  ✅ Created virtual environment"
fi

source venv/bin/activate
pip install -r requirements.txt --quiet
echo "  ✅ Installed Python dependencies"

# Create data directories
mkdir -p data/chroma_db data/raw
echo "  ✅ Created data directories"

cd ..

# 4. Frontend setup
echo ""
echo "⚛️  Setting up frontend..."
cd frontend
npm install --silent
echo "  ✅ Installed Node.js dependencies"
cd ..

# 5. Done!
echo ""
echo "============================================"
echo "✅ Setup complete!"
echo ""
echo "📌 Next steps:"
echo "   1. Add your API keys to .env"
echo "   2. Ingest knowledge base (from repo root):"
echo "      python scripts/ingest_uscis_data.py --yes"
echo "   3. Start backend:"
echo "      uvicorn app.main:app --reload --port 8000"
echo "   4. Start frontend (new terminal):"
echo "      cd frontend && npm run dev"
echo ""
echo "   API docs: http://localhost:8000/docs"
echo "   Frontend:  http://localhost:3000"
echo "============================================"
