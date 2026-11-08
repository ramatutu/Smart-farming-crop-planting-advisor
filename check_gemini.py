"""Run this to see the REAL Gemini error:   python check_gemini.py

Tests your key, lists available Flash models, then tries both request methods
with a 20-second limit so it never hangs.
"""
import os
import time

from dotenv import load_dotenv

load_dotenv()
key = os.getenv("GEMINI_API_KEY")
print("Key found in .env:", bool(key), "| length:", len(key) if key else 0)
if not key:
    raise SystemExit("No GEMINI_API_KEY. Check that .env is next to this file.")

from google import genai
from google.genai import types

from services.gemini_client import DEFAULT_MODEL as MODEL_NAME

client = genai.Client(api_key=key)
print("\nModel the app uses:", MODEL_NAME)

print("\n1) Listing models available to your key (flash only)...")
try:
    names = [m.name for m in client.models.list() if "flash" in (m.name or "").lower()]
    for n in names[:15]:
        print("   ", n)
    if not any(MODEL_NAME in n for n in names):
        print(f"   !! '{MODEL_NAME}' is NOT in this list. Pick one above and change MODEL_NAME in services/gemini_client.py")
except Exception as e:
    print("   FAILED:", type(e).__name__, e)

print("\n2) Standard generateContent request...")
t = time.time()
try:
    r = client.models.generate_content(
        model=MODEL_NAME, contents="Say hello in five words.",
        config=types.GenerateContentConfig(
            max_output_tokens=50, http_options=types.HttpOptions(timeout=20000)),
    )
    print(f"   OK ({time.time()-t:.1f}s):", r.text)
except Exception as e:
    print(f"   FAILED after {time.time()-t:.1f}s:", type(e).__name__, e)

print("\n3) Interactions API request...")
t = time.time()
try:
    r = client.interactions.create(model=MODEL_NAME, input="Say hello in five words.", timeout=20)
    print(f"   OK ({time.time()-t:.1f}s):", r.output_text)
except Exception as e:
    print(f"   FAILED after {time.time()-t:.1f}s:", type(e).__name__, e)