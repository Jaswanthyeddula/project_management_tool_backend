#!/usr/bin/env python3
"""Test TiDB Cloud connection with SSL"""
from dotenv import load_dotenv
import os
load_dotenv()

from app.config import Config
cfg = Config()

print(f"DB_URI: {cfg.SQLALCHEMY_DATABASE_URI}")
print(f"Engine Options: {cfg.SQLALCHEMY_ENGINE_OPTIONS}")

try:
    from sqlalchemy import create_engine, text
    engine = create_engine(cfg.SQLALCHEMY_DATABASE_URI, **cfg.SQLALCHEMY_ENGINE_OPTIONS)
    
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print("✓ TiDB Connection: SUCCESS")
        print(f"✓ Query result: {result.fetchone()}")
except Exception as e:
    print(f"✗ TiDB Connection FAILED: {e}")
    import traceback
    traceback.print_exc()
