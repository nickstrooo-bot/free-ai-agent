# free-agent 🤖

**Free AI that does work for you. $0. No subscriptions.**

Give free AI models *hands* — let them read files, write code, run commands, and research the web. They do the task, you get the result. No $20/month. No API bills.

```bash
python3 agent.py "Research the top 5 open-source chat bots and save a summary to findings.md"
```

That's it. The agent thinks, uses tools, and delivers.

---

## What is this?

Two scripts, zero dependencies, three free AI models:

| Script | What it does |
|---|---|
| `agent.py` | Gives a free AI model **hands**: read/write files, run shell commands, fetch web pages. It breaks your task into steps and does the work. |
| `thinktank.py` | Asks free AI models anything — one model, or all of them in parallel for a "think tank" second opinion. |

Both run on **100% free model tiers**. No credit card. No trial that expires.

## The free models

| Model | Cost | Limit | Get a key |
|---|---|---|---|
| **z.ai GLM-4.7** (primary) | Free forever | ~1,000 req/day | [z.ai](https://z.ai) — free signup, no card |
| **Gemini 2.5 Flash** (optional) | Free | ~1,500 req/day | [Google AI Studio](https://aistudio.google.com) — free, no card |
| **Nemotron 3 Ultra** (fallback) | Free | 50 req/day | [OpenRouter](https://openrouter.ai/keys) — free, no card |
| **Pollinations** (keyless) | Free | Shared pool | None needed — works out of the box |

The agent tries each provider in order and fails over automatically. One key is enough to start.

## Quick start

```bash
# 1. Get a free key (pick one — z.ai is the easiest)
#    Sign up at https://z.ai (no card), create an API key

# 2. Save it
mkdir -p ~/.config/free-agent
echo "YOUR_KEY_HERE" > ~/.config/free-agent/zai_key
chmod 600 ~/.config/free-agent/zai_key

# 3. Check what's live
python3 agent.py --status

# 4. Give it a job
python3 agent.py "Write a Python script that renames all .txt files in the sandbox to .md and list what changed"
```

No `pip install`. No virtualenv. Python 3.8+ stdlib only.

## Example

```
$ python3 agent.py "Fetch the Python homepage and tell me the latest release version"

  [step 1/15] thinking...
  [via zai]
  [tool] fetch_url({'url': 'https://www.python.org/'})
  [step 2/15] thinking...

Python 3.14.0 is the latest stable release (October 2025)...
```

The agent fetched the page, parsed it, and answered. Cost: $0.00.

## thinktank.py — free AI answers

```bash
# Ask the smartest available model
python3 thinktank.py "Explain recursion like I'm five"

# Ask all models at once, compare answers
python3 thinktank.py --panel "Should I learn Rust or Go in 2026?"

# Check which models are ready
python3 thinktank.py --status
```

```python
from thinktank import ask, ask_panel

ask("Summarize this in one sentence: ...")
ask("Debug this for me", model="nemotron")   # pick a specific model
ask_panel("Best budget laptop?")             # all models, compare
```

## How the agent works

```
task → model thinks → calls tool → gets result → repeats → done
```

Tools the agent gets (all sandboxed):
- `read_file` / `write_file` — file ops locked to `~/.free-agent-sandbox/`
- `run_command` — shell with 30s timeout; `sudo` and destructive patterns blocked
- `list_files` — browse the sandbox
- `fetch_url` — fetch any web page or API docs as text

```python
from agent import run_agent, provider_status

print(provider_status())          # see which providers are live

result = run_agent(
    task="Your task here",
    max_steps=15,                 # cap the loop
    verbose=True,                 # watch it think
)
```

## Safety

- **Sandboxed files**: the agent can only touch `~/.free-agent-sandbox/`
- **Sandboxed shell**: 30-second timeout, no `sudo`, `rm -rf /` style patterns blocked
- **Your keys stay yours**: keys live in `~/.config/free-agent/` (600 perms) or env vars — never in the code
- **Failover, not lock-in**: if one provider 404s or rate-limits, the next one picks up

## Why free?

AI companies give away generous free tiers to win developers. This project just... uses them. Hard. The z.ai free tier alone handles ~1,000 requests a day — that's 60–200 agent tasks daily at zero cost.

Stop paying $20/month for a chatbot. Put the models to work.

## Who made this

Built by [Atlas](https://www.youtube.com/@Nickstrovipai) — I run a YouTube channel and got tired of paying for AI. So I built the free version. Star the repo if it saves you money. 🤖

## License

MIT — do whatever you want with it.
