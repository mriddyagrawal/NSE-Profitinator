#!/bin/bash

# Navigate to the script directory
cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Launch Streamlit app
streamlit run streamlit_app.py

# Keep terminal open on error
read -p "Press Enter to close..."
