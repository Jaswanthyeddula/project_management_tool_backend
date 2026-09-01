#!/usr/bin/env python3
"""Initialize database schema with Flask migrations"""
import sys
from dotenv import load_dotenv

# Load environment variables from .env before importing app
load_dotenv()

from app import create_app
from flask_migrate import upgrade

try:
    app = create_app()
    with app.app_context():
        print("Applying database migrations...")
        upgrade()
        print("✓ Database migrations applied successfully!")
except Exception as e:
    print(f"✗ Migration failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
