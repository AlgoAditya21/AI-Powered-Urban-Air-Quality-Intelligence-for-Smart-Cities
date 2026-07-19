#!/usr/bin/env bash
set -euo pipefail

echo "==> Creating virtual environment (.venv)..."
python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate

echo "==> Upgrading pip..."
pip install --quiet --upgrade pip

echo "==> Installing requirements..."
pip install --quiet -r requirements.txt

echo "==> Generating data + training models..."
python generate_and_train.py

echo ""
echo "======================================================================"
echo " AirIQ setup complete."
echo " Run the app with:"
echo "     source .venv/bin/activate && streamlit run app.py"
echo "======================================================================"
