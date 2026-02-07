#!/usr/bin/env bash
# -----------------------------------------------
#  BrainBurst Trivia – one-click launcher
#  Just double-click this or run: bash start.sh
# -----------------------------------------------
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "🧠  BrainBurst Trivia"
echo "====================="
echo ""

# check python
if command -v python3 &> /dev/null; then
    PYTHON=python3
elif command -v python &> /dev/null; then
    PYTHON=python
else
    echo "❌  Python 3 is required but not installed."
    echo "   Download it from https://www.python.org/downloads/"
    exit 1
fi

echo "   Using: $($PYTHON --version)"

# set up virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "📦  Creating virtual environment..."
    $PYTHON -m venv .venv
    echo "   ✅ Virtual environment created"
fi

# activate virtual environment
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
elif [ -f ".venv/Scripts/activate" ]; then
    source .venv/Scripts/activate
else
    echo "❌  Could not find venv activation script."
    exit 1
fi

# install deps
echo "📦  Installing dependencies..."
pip install --quiet --upgrade pip 2>/dev/null || true
pip install --quiet -r requirements.txt

echo ""
echo "🚀  Launching game in your browser..."
echo "   (Press Ctrl+C in this terminal to stop)"
echo ""
echo "   Pages available:"
echo "     🏠 Home        – Dashboard & stats"
echo "     ▶️  Play        – General trivia (OpenTDB)"
echo "     🌍 Diplomacy   – 539+ diplomatic trivia questions"
echo ""

streamlit run "🏠_Home.py" --server.headless true --browser.gatherUsageStats false
