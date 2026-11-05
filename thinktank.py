#!/usr/bin/env python3
"""
thinktank.py — ask free AI models anything. $0. No subscriptions.

THE THREE (verified working):
  1. z.ai GLM-4.7-Flash — free signup at z.ai, ~1,000 req/day — primary
  2. Nemotron 3 Ultra (NVIDIA, 550B) — via OpenRouter :free, 50 req/day — fallback
  3. openai-fast — via Pollinations — keyless, no signup, always available

Get a free z.ai key at https://z.ai (no card). Set it as ZAI_API_KEY env var
or save it to ~/.config/free-agent/zai_key.
Without any key, only Pollinations works.

Usage:
    from thinktank import ask, ask_panel
    ask("your question")                    # smartest available model
    ask("your question", model="nemotron")  # specific model
    ask_panel("your question")              # all available models in parallel

CLI:
    python3 thinktank.py "your question"
    python3 thinktank.py --panel "your question"
    python3 thinktank.py --status
"""
import json
import os
import sys
import urllib.request
import urllib.error
import concurrent.futures

ZAI_URL = "https://api.z.ai/api/paas/v4/chat/completions"
POLLINATIONS_URL = "https://text.pollinations.ai/openai"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

MODELS = {
    "zai": {
        "provider": "zai",
        "id": "glm-4.7-flash",
        "desc": "Fast, strong all-rounder — perpetual free tier, ~1,000 req/day",
    },
    "nemotron": {
        "provider": "openrouter",
        "id": "nvidia/nemotron-3-ultra-550b-a55b:free",
        "desc": "550B params, 1M context — best free reasoner, 50 req/day",
    },
    "pollinations": {
        "provider": "pollinations",
        "id": "openai-fast",
        "desc": "Keyless, no signup — always available fallback",
    },
}

def _read_key(env_var, key_file):
    key = os.environ.get(env_var, "").strip()
    if key:
        return key
    kf = os.path.expanduser(key_file)
    if os.path.exists(kf):
        with open(kf) as f:
            return f.read().strip()
    return None

def _get_zai_key():
    return _read_key("ZAI_API_KEY", "~/.config/free-agent/zai_key")

def _get_openrouter_key():
    return _read_key("OPENROUTER_API_KEY", "~/.config/free-agent/openrouter_key")

def _post_json(url, payload, headers=None, timeout=120):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json",
                 "User-Agent": "free-agent-thinktank/1.0",
                 **(headers or {})},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())

def _chat_completion(url, model_id, prompt, api_key, system=None,
                     timeout=120, extra_headers=None):
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    payload = {"model": model_id, "messages": messages}
    headers = {"Authorization": f"Bearer {api_key}"}
    headers.update(extra_headers or {})
    resp = _post_json(url, payload, headers, timeout)
    return resp["choices"][0]["message"]["content"].strip()

def _ask_zai(prompt, api_key, system=None, timeout=120):
    try:
        return _chat_completion(ZAI_URL, "glm-4.7-flash", prompt, api_key,
                                system, timeout)
    except Exception as e:
        return f"[ERROR z.ai: {e}]"

def _ask_openrouter(prompt, model_id, api_key, system=None, timeout=120):
    try:
        return _chat_completion(
            OPENROUTER_URL, model_id, prompt, api_key, system, timeout,
            extra_headers={"HTTP-Referer": "https://github.com",
                           "X-Title": "free-agent think tank"})
    except Exception as e:
        return f"[ERROR openrouter/{model_id}: {e}]"

def _ask_pollinations(prompt, system=None, timeout=120):
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    payload = {"model": "openai-fast", "messages": messages}
    try:
        resp = _post_json(POLLINATIONS_URL, payload, timeout=timeout)
        return resp["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"[ERROR pollinations: {e}]"

def ask(prompt, model="best", system=None, timeout=120):
    zai_key = _get_zai_key()
    or_key = _get_openrouter_key()
    if model == "best":
        if zai_key:
            model = "zai"
        elif or_key:
            model = "nemotron"
        else:
            model = "pollinations"
    info = MODELS.get(model)
    if not info:
        return f"[ERROR: unknown model '{model}']"
    if info["provider"] == "zai":
        if not zai_key:
            return _ask_pollinations(prompt, system, timeout)
        return _ask_zai(prompt, zai_key, system, timeout)
    if info["provider"] == "openrouter":
        if not or_key:
            return _ask_pollinations(prompt, system, timeout)
        return _ask_openrouter(prompt, info["id"], or_key, system, timeout)
    return _ask_pollinations(prompt, system, timeout)

def ask_panel(prompt, system=None, timeout=120):
    targets = ["pollinations"]
    if _get_zai_key():
        targets.insert(0, "zai")
    if _get_openrouter_key():
        targets.append("nemotron")
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(targets)) as ex:
        futs = {ex.submit(ask, prompt, m, system, timeout): m for m in targets}
        for f in concurrent.futures.as_completed(futs):
            m = futs[f]
            try:
                results[m] = f.result()
            except Exception as e:
                results[m] = f"[ERROR: {e}]"
    return results

def status():
    zai_key = _get_zai_key()
    or_key = _get_openrouter_key()
    lines = ["Think Tank status:"]
    lines.append(f"  zai: {MODELS['zai']['desc']} — "
                 + ("READY" if zai_key else "NEEDS KEY (free signup at https://z.ai)"))
    lines.append(f"  nemotron: {MODELS['nemotron']['desc']} — "
                 + ("READY" if or_key else "NEEDS KEY (free at https://openrouter.ai/keys)"))
    lines.append(f"  pollinations: {MODELS['pollinations']['desc']} — READY (keyless)")
    return "\n".join(lines)

def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("--help", "-h"):
        print(__doc__)
        print()
        print(status())
        sys.exit(0)
    if sys.argv[1] == "--status":
        print(status())
        sys.exit(0)
    panel = "--panel" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--panel"]
    question = " ".join(args)
    if panel:
        print("Consulting think tank...\n", flush=True)
        for model, answer in ask_panel(question).items():
            print(f"=== {model.upper()} ===")
            print(answer)
            print()
    else:
        print(ask(question), flush=True)

if __name__ == "__main__":
    main()
