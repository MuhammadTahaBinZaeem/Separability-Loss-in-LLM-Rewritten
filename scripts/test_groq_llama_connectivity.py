"""Minimal Groq Llama connectivity check.

Reads GROQ_LLAMA_API_KEY from the environment and sends one tiny request.
Never prints the API key.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request


API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.3-70b-versatile"


def main() -> int:
    api_key = os.environ.get("GROQ_LLAMA_API_KEY")
    if not api_key:
        print("status_code: none")
        print("error_body: missing GROQ_LLAMA_API_KEY")
        print("failure")
        return 2

    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": "say hi"}],
        "max_tokens": 8,
        "temperature": 0,
    }
    request = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "litpaper-groq-connectivity-test/1.0",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            response.read()
            print(f"status_code: {response.status}")
            print("error_body:")
            print("success")
            return 0
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(f"status_code: {exc.code}")
        print(f"error_body: {body}")
        print("failure")
        return 1
    except Exception as exc:  # noqa: BLE001
        print("status_code: none")
        print(f"error_body: {type(exc).__name__}: {exc}")
        print("failure")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
