# Compatibility wrapper redirecting uvicorn to root main.py app instance
import sys
import os

# Add root backend directory to sys.path so it can locate main.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
