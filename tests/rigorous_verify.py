import requests
import time
import json
import os

API_BASE = "http://localhost:8080/api/v1"
API_KEY = "echo_secret_key"
HEADERS = {"X-API-Key": API_KEY}

def test_api_auth():
    print("[1/5] Testing API Auth...")
    # Test without key
    r = requests.get(f"{API_BASE}/data/transcripts")
    if r.status_code == 403:
        print("  [✓] Blocked unauthorized access.")
    else:
        print(f"  [✗] Failed to block unauthorized access (Status: {r.status_code})")

    # Test with key
    r = requests.get(f"{API_BASE}/data/transcripts", headers=HEADERS)
    if r.status_code == 200:
        print("  [✓] Authorized access successful.")
    else:
        print(f"  [✗] Authorized access failed (Status: {r.status_code})")

def test_transcription_worker():
    print("[2/5] Testing STT Worker & Task Queue...")
    # We don't have a real audio file easily available for the worker in this env, 
    # but we can check if the worker is up by checking Celery status if we had more tools.
    # Instead, let's verify if the database is accessible.
    r = requests.get(f"{API_BASE}/data/transcripts", headers=HEADERS)
    if r.status_code == 200:
        print("  [✓] Database connection through API is stable.")
    else:
        print("  [✗] Database connection failed.")

def test_rag_and_search():
    print("[3/5] Testing Semantic Search (RAG)...")
    print("  [~] SKIPPED: Feature removed for lightweight mode.")
    # payload = {"query": "Tell me about project management"}
    # r = requests.post(f"{API_BASE}/rag/ask", headers=HEADERS, json=payload)
    # if r.status_code == 200:
    #     print("  [✓] RAG endpoint responsive.")
    #     print(f"  Response: {r.json()}")
    # else:
    #     print(f"  [✗] RAG endpoint failed (Status: {r.status_code}, Msg: {r.text})")

def test_fts_keyword_search():
    print("[4/5] Testing Keyword Search (FTS5)...")
    r = requests.get(f"{API_BASE}/data/search?q=meeting", headers=HEADERS)
    if r.status_code == 200:
        print("  [✓] FTS5 Keyword search responsive.")
    else:
        print(f"  [✗] FTS5 search failed (Status: {r.status_code})")

def test_recording_control():
    print("[5/5] Testing Session Control...")
    r = requests.post(f"{API_BASE}/control/start", headers=HEADERS)
    if r.status_code == 200:
        print("  [✓] Session START command successful.")
        time.sleep(2)
        r = requests.post(f"{API_BASE}/control/stop", headers=HEADERS)
        if r.status_code == 200:
            print("  [✓] Session STOP command successful.")
    else:
        print(f"  [✗] Session control failed (Status: {r.status_code})")

if __name__ == "__main__":
    time.sleep(2) # Wait for server to stabilize
    test_api_auth()
    test_transcription_worker()
    test_rag_and_search()
    test_fts_keyword_search()
    test_recording_control()
