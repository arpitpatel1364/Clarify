import sys, os
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault("QT_QPA_PLATFORM", "xcb")

print("=== Clarify Diagnostic ===\n")

# 1. Check settings
from config.settings import settings
print(f"Active provider: {settings.ai.active_provider}")
print(f"Model: {settings.ai.explain_style}")
print(f"Auto select: {settings.trigger.auto_on_select}")
print(f"Show tooltip: {settings.popup.show_tooltip}")

# 2. Check Ollama
import requests
try:
    r = requests.get("http://localhost:11434/api/tags", timeout=3)
    models = [m["name"] for m in r.json().get("models", [])]
    print(f"\nOllama: RUNNING")
    print(f"Installed models: {models}")
except Exception as e:
    print(f"\nOllama: NOT REACHABLE — {e}")

# 3. Check DB provider config
from db.database import get_db, get_or_create_provider
from core.crypto import decrypt
db = get_db()
for pname in ["ollama", "claude", "openai"]:
    cfg = get_or_create_provider(db, pname)
    key = decrypt(cfg.api_key or "")
    print(f"\n{pname}:")
    print(f"  model    = {cfg.model}")
    print(f"  base_url = {cfg.base_url}")
    print(f"  has_key  = {bool(key)}")
db.close()

# 4. Test Ollama streaming directly
print("\n=== Testing Ollama stream directly ===")
from db.database import get_db, get_or_create_provider
from core.crypto import decrypt
db = get_db()
cfg = get_or_create_provider(db, "ollama")
model = cfg.model or "llama3"
base_url = (cfg.base_url or "http://localhost:11434").rstrip("/")
db.close()

import json
try:
    resp = requests.post(
        base_url + "/api/chat",
        json={"model": model, "messages": [{"role": "user", "content": "Say hello in 5 words"}], "stream": True},
        stream=True,
        timeout=(5, 30),
    )
    resp.raise_for_status()
    print(f"Status: {resp.status_code}")
    tokens = []
    for line in resp.iter_lines():
        if line:
            data = json.loads(line)
            if "error" in data:
                print(f"ERROR from Ollama: {data['error']}")
                break
            t = data.get("message", {}).get("content", "")
            if t:
                tokens.append(t)
                print(t, end="", flush=True)
            if data.get("done"):
                break
    print(f"\nTotal tokens received: {len(tokens)}")
    if not tokens:
        print("WARNING: No tokens received — model may be wrong or Ollama returning error")
except Exception as e:
    print(f"FAILED: {e}")

print("\n=== Diagnostic complete ===")
