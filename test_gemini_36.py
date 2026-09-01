#!/usr/bin/env python3
"""Test Gemini API with gemini-3.6-flash model"""
from dotenv import load_dotenv
import os
load_dotenv()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

try:
    from google import genai
    
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents="Extract task: Fix the login bug by Friday",
    )
    print("✓ Gemini 3.6 Flash API call successful!")
    print(f"Response: {response.text[:100]}...")
    
except Exception as e:
    print(f"✗ Gemini API call failed: {e}")
    import traceback
    traceback.print_exc()
