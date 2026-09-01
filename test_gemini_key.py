#!/usr/bin/env python3
"""Test Gemini API key and connection"""
from dotenv import load_dotenv
import os
load_dotenv()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
print(f"API Key loaded: {bool(GEMINI_API_KEY)}")
if GEMINI_API_KEY:
    print(f"API Key (first 20 chars): {GEMINI_API_KEY[:20]}...")

try:
    from google import genai
    from google.genai import types
    
    client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
    
    if not client:
        print("✗ Gemini client is None - API key is missing")
    else:
        print("✓ Gemini client initialized successfully")
        
        # Try a simple API call
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents="Test message",
            )
            print("✓ Gemini API call successful")
            print(f"Response: {response.text[:100]}...")
        except Exception as e:
            print(f"✗ Gemini API call failed: {e}")
            import traceback
            traceback.print_exc()
            
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
