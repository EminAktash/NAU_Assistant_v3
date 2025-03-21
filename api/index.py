from flask import Flask, Response
import sys
import os

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the Flask app from app.py
from app import app as flask_app

# Create a handler function for serverless
def handler(request):
    """Wrapper for Flask app for serverless environments"""
    return Response(
        flask_app(request.environ, lambda s, h, e=None: [])
    )