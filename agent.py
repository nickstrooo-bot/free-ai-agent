#!/usr/bin/env python3
"""
free-agent — give free AI models hands. Turns $0 models into working agents.

Each agent gets tools: read/write files, run commands, fetch web pages.
The agent loop: task -> model thinks -> calls tool -> gets result -> repeats -> done.

Usage:
    from agent import run_agent

    result = run_agent(
        task="Research the top 5 open-source chat bots and save a summary to findings.md",
        max_steps=15,
    )
    print(result)

Setup (one free API key):
    1. Sign up free at https://z.ai (no card) and create an API key
    2. mkdir -p ~/.config/free-agent && echo "YOUR_KEY" > ~/.config/free-agent/zai_key
    3. python3 agent.py "your task here"

Safety:
    - File ops sandboxed to ~/.free-agent-sandbox/
    - Commands run with 30s timeout, no sudo, destructive patterns blocked
    - Each agent task burns ~5-15 API requests (z.ai free tier: ~1,000/day)
"""
import json
import os
import re
import subprocess
import urllib.request

SANDBOX = os.path.expanduser("~/.free-agent-sandbox")
os.makedirs(SANDBOX, exist_ok=True)

PROVIDERS = [
    {
        "name": "zai",
        "url": "https://api.z.ai/api/paas/v4/chat/completions",
        "model": "glm-4.7-flash",
        "key_file": "~/.config/free-agent/zai_key",
        "key_env": "ZAI_API_KEY",
        "daily_budget": 1000,
        "role": "primary — perpetual free tier",
        "signup": "https://z.ai (free, no card)",
    },
    {
        "name": "gemini",
        "url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "model": "gemini-2.5-flash",
        "key_file": "~/.config/free-agent/gemini_key",
        "key_env": "GEMINI_API_KEY",
        "daily_budget": 1500,
        "role": "strong all-rounder",
        "signup": "https://aistudio.google.com (free, no card)",
    },
    {
        "name": "openrouter",
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "model": "nvidia/nemotron-3-ultra-550b-a55b:free",
        "key_file": "~/.config/free-agent/openrouter_key",
        "key_env": "OPENROUTER_API_KEY",
        "daily_budget": 50,
        "role": "reasoning fallback",
        "signup": "https://openrouter.ai/keys (free, no card)",
        "extra_headers": {
            "HTTP-Referer": "https://github.com",
            "X-Title": "free-agent",
        },
    },
]

def _safe_path(path):
    full = os.path.normpath(os.path.join(SANDBOX, path.lstrip("/")))
    if not full.startswith(SANDBOX):
        raise ValueError("Path escapes sandbox")
    return full

def tool_read_file(path):
    try:
        with open(_safe_path(path)) as f:
            content = f.read()
        return content[:10000]
    except Exception as e:
        return f"ERROR: {e}"

def tool_write_file(path, content):
    try:
        full = _safe_path(path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w") as f:
            f.write(content)
        return f"Wrote {len(content)} chars to {path}"
    except Exception as e:
        return f"ERROR: {e}"

def tool_run_command(command):
    if re.search(r'\bsudo\b|\brm -rf\s+[/~]', command):
        return "ERROR: blocked command"
    try:
        r = subprocess.run(
            command, shell=True, capture_output=True, text=True,
            timeout=30, cwd=SANDBOX,
        )
        out = (r.stdout + r.stderr)[:5000]
        return f"exit={r.returncode}\n{out}"
    except subprocess.TimeoutExpired:
        return "ERROR: command timed out (30s)"
    except Exception as e:
        return f"ERROR: {e}"

def tool_list_files(path="."):
    try:
        full = _safe_path(path)
        items = sorted(os.listdir(full))
        return "\n".join(items) if items else "(empty)"
    except Exception as e:
        return f"ERROR: {e}"

def tool_fetch_url(url):
    if not url.startswith(("http://", "https://")):
        return "ERROR: URL must start with http:// or https://"
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (compatible; free-agent/1.0)"})
        with urllib.request.urlopen(req, timeout=15) as r:
            ctype = r.headers.get("Content-Type", "")
            raw = r.read(50000)
            text = raw.decode("utf-8", errors="ignore")
            if "html" in ctype:
                text = re.sub(r'<script.*?</script>', ' ', text,
                              flags=re.DOTALL | re.IGNORECASE)
                text = re.sub(r'<style.*?</style>', ' ', text,
                              flags=re.DOTALL | re.IGNORECASE)
                text = re.sub(r'<[^>]+>', ' ', text)
                text = re.sub(r'\s+', ' ', text)
            return text[:20000]
    except Exception as e:
        return f"ERROR: {e}"

TOOLS = {
    "read_file": tool_read_file,
    "write_file": tool_write_file,
    "run_command": tool_run_command,
    "list_files": tool_list_files,
    "fetch_url": tool_fetch_url,
}

TOOL_SCHEMAS = [
    {"type": "function", "function": {
        "name": "read_file",
        "description": "Read a file from the sandbox workspace",
        "parameters": {"type": "object",
                       "properties": {"path": {"type": "string"}},
                       "required": ["path"]}}},
    {"type": "function", "function": {
        "name": "write_file",
        "description": "Write content to a file in the sandbox workspace",
        "parameters": {"type": "object",
                       "properties": {"path": {"type": "string"},
                                      "content": {"type": "string"}},
                       "required": ["path", "content"]}}},
    {"type": "function", "function": {
        "name": "run_command",
        "description": "Run a shell command (30s timeout, no sudo)",
        "parameters": {"type": "object",
                       "properties": {"command": {"type": "string"}},
                       "required": ["command"]}}},
    {"type": "function", "function": {
        "name": "list_files",
        "description": "List files in a sandbox directory",
        "parameters": {"type": "object",
                       "properties": {"path": {"type": "string"}},
                       "required": []}}},
    {"type": "function", "function": {
        "name": "fetch_url",
        "description": "Fetch a URL and return its text content (for research, API docs, web pages)",
        "parameters": {"type": "object",
                       "properties": {"url": {"type": "string"}},
                       "required": ["url"]}}},
]

def _get_key(provider):
    key = os.environ.get(provider["key_env"], "").strip()
    if key:
        return key
    kf = os.path.expanduser(provider["key_file"])
    if os.path.exists(kf):
        with open(kf) as f:
            return f.read().strip()
    return None

def _call_provider(messages, provider, key, timeout=90):
    payload = {"model": provider["model"], "messages": messages,
               "tools": TOOL_SCHEMAS, "tool_choice": "auto"}
    data = json.dumps(payload).encode()
    headers = {"Content-Type": "application/json",
               "Authorization": f"Bearer {key}"}
    headers.update(provider.get("extra_headers", {}))
    req = urllib.request.Request(provider["url"], data=data, headers=headers)
    last_err = None
    for _ in range(2):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode()), provider["name"]
        except Exception as e:
            last_err = e
    raise RuntimeError(f"{provider['name']}: {last_err}")

def _call_model(messages, timeout=90):
    errors = []
    for provider in PROVIDERS:
        pkey = _get_key(provider)
        if not pkey:
            continue
        try:
            return _call_provider(messages, provider, pkey, timeout)
        except Exception as e:
            errors.append(str(e)[:100])
            continue
    raise RuntimeError("All providers failed: " + "; ".join(errors))

def provider_status():
    lines = ["Agent provider stack:"]
    total = 0
    for p in PROVIDERS:
        ready = bool(_get_key(p))
        state = "READY" if ready else f"NEEDS KEY ({p['signup']})"
        lines.append(f"  {p['name']}: {p['model']} ({p['daily_budget']}/day) — {p['role']} — {state}")
        if ready:
            total += p["daily_budget"]
    lines.append(f"  Combined daily budget: ~{total} requests")
    return "\n".join(lines)

def run_agent(task, max_steps=15, verbose=False):
    if not any(_get_key(p) for p in PROVIDERS):
        return ("[ERROR: no provider API keys configured. "
                "Get a free key at https://z.ai and save it to "
                "~/.config/free-agent/zai_key, or run: python3 agent.py --status]")

    system = (
        "You are a coding agent working in a sandboxed workspace. "
        "You have tools: read_file, write_file, run_command, list_files, fetch_url. "
        "fetch_url fetches any web page or API docs and returns text — use it for research. "
        "Break the task into steps, use tools to do the work, verify your results. "
        "When done, reply with a summary of what you accomplished. "
        "Be efficient — you have limited steps."
    )
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": task},
    ]

    for step in range(max_steps):
        if verbose:
            print(f"  [step {step+1}/{max_steps}] thinking...", flush=True)
        resp, provider_name = _call_model(messages)
        if verbose and step == 0:
            print(f"  [via {provider_name}]", flush=True)
        msg = resp["choices"][0]["message"]
        messages.append(msg)

        tool_calls = msg.get("tool_calls") or []
        if not tool_calls:
            return msg.get("content", "(no output)")

        for tc in tool_calls:
            fname = tc["function"]["name"]
            try:
                args = json.loads(tc["function"]["arguments"])
            except Exception:
                args = {}
            if verbose:
                print(f"  [tool] {fname}({str(args)[:80]})", flush=True)
            fn = TOOLS.get(fname)
            result = fn(**args) if fn else f"ERROR: unknown tool {fname}"
            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": str(result),
            })

    return "[Agent hit max steps without finishing]"


if __name__ == "__main__":
    import sys
    if "--status" in sys.argv:
        print(provider_status())
        sys.exit(0)
    task = " ".join(a for a in sys.argv[1:] if a != "--status") \
        or "List the files in the sandbox and write a hello.txt with a greeting"
    print(run_agent(task, verbose=True))
