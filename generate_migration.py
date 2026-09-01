#!/usr/bin/env python3
"""Generate migration for password_hash column"""
from dotenv import load_dotenv
load_dotenv()

from app import create_app
from flask_migrate import migrate

app = create_app()
with app.app_context():
    migrate()
    print("✓ Migration generated successfully")
