"""Zero Dollar Dev, video 1: a Telegram research agent for $0.

Message the bot a question. It searches the web, reads the top pages, and
answers with sources. No framework: the agent loop is the `run_agent` function.

Free tiers used: Telegram Bot API, Groq (Llama), DuckDuckGo search.
"""
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import httpx
import trafilatura
from ddgs import DDGS

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
GROQ_API_KEY = os.environ["GROQ_API_KEY"]
MODEL = os.environ.get("MODEL", "openai/gpt-oss-120b")  # what broke #2: llama-3.3-70b was retired. Check /v1/models.
FALLBACK_MODEL = os.environ.get("FALLBACK_MODEL", "openai/gpt-oss-20b")  # separate rate-limit bucket on the free tier

TG = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
GROQ = "https://api.groq.com/openai/v1/chat/completions"
MAX_TOOL_CALLS = 4          # what broke #1: free tier rate limit when the loop ran wild
MAX_PAGE_CHARS = 3000       # keep tokens low, keep it free

SYSTEM = """You are a research assistant. Use the tools to find current, factual answers.
Rules: search first, read 1 to 3 pages, then answer. Keep the answer under 120 words.
End with a line 'Sources:' followed by the URLs you actually read. Never invent URLs."""

TOOLS = [
    {"type": "function", "function": {
        "name": "search",
        "description": "Search the web. Returns titles, URLs and snippets.",
        "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {
        "name": "read_page",
        "description": "Fetch a URL and return its main text.",
        "parameters": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}}},
]


# ---------- tools ----------
def search(query: str) -> str:
    # what broke #3: DuckDuckGo reset the connection on my network. Try several engines.
    for backend in ("bing", "yahoo", "duckduckgo", "brave"):
        try:
            results = DDGS(timeout=15).text(query, max_results=5, backend=backend)
            if results:
                return "\n".join(f"- {r['title']}\n  {r['href']}\n  {r['body']}" for r in results)
        except Exception as e:
            print(f"  search via {backend} failed: {type(e).__name__}")
    return "no results from any search engine"


_page_cache: dict[str, str] = {}


def read_page(url: str) -> str:
    if url in _page_cache:  # the model asked for the same page 3 times in a row; serve it once
        return _page_cache[url]
    html = trafilatura.fetch_url(url)
    text = trafilatura.extract(html) if html else None
    _page_cache[url] = (text or "could not read page")[:MAX_PAGE_CHARS]
    return _page_cache[url]


TOOL_FUNCS = {"search": search, "read_page": read_page}


# ---------- the agent loop ----------
def llm(messages):
    # what broke #4: free tier returned 429 Too Many Requests mid-conversation.
    # Fix: wait and retry, then fall back to the smaller model, which has its own limit.
    for attempt, model in enumerate((MODEL, MODEL, FALLBACK_MODEL)):
        r = httpx.post(GROQ, timeout=60,
                       headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                       json={"model": model, "messages": messages, "tools": TOOLS, "tool_choice": "auto"})
        if r.status_code == 429:
            wait = float(r.headers.get("retry-after", 2 + 2 * attempt))
            print(f"  rate limited on {model}, waiting {wait:.0f}s")
            time.sleep(min(wait, 20))
            continue
        r.raise_for_status()
        return r.json()["choices"][0]["message"]
    raise RuntimeError("rate limited on every model, try again in a minute")


def run_agent(question: str) -> str:
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": question}]
    for _ in range(MAX_TOOL_CALLS):
        msg = llm(messages)
        messages.append(msg)
        if not msg.get("tool_calls"):
            return msg["content"]
        for call in msg["tool_calls"]:
            name = call["function"]["name"]
            args = json.loads(call["function"]["arguments"])
            print(f"  tool: {name}({args})")
            try:
                result = TOOL_FUNCS[name](**args)
            except Exception as e:  # what broke #3: the model invented an argument and crashed the loop
                result = f"tool error: {type(e).__name__}: {e}. Call the tool again with only the documented arguments."
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": result})
    # out of tool calls: force a final answer
    messages.append({"role": "user", "content": "Answer now with what you have."})
    return llm(messages)["content"]


# ---------- telegram (long polling, works locally with no public URL) ----------
def send(chat_id, text):
    text = text.replace("**", "").replace("__", "")  # the model writes markdown, Telegram showed the raw asterisks
    httpx.post(f"{TG}/sendMessage", json={"chat_id": chat_id, "text": text[:4000]}, timeout=30)


class Health(BaseHTTPRequestHandler):
    """Hugging Face Spaces expects something to answer on port 7860. This also gives the keep-awake ping a target."""
    def do_GET(self):
        self.send_response(200); self.end_headers(); self.wfile.write(b"zero dollar agent: running")
    def log_message(self, *_):
        pass


def main():
    threading.Thread(target=HTTPServer(("0.0.0.0", int(os.environ.get("PORT", 7860))), Health).serve_forever, daemon=True).start()
    print("agent running, cost so far: $0")
    offset = None
    while True:
        try:
            r = httpx.get(f"{TG}/getUpdates", params={"timeout": 30, "offset": offset}, timeout=40).json()
            for upd in r.get("result", []):
                offset = upd["update_id"] + 1
                msg = upd.get("message") or {}
                text, chat_id = msg.get("text"), msg.get("chat", {}).get("id")
                if not text or not chat_id:
                    continue
                print(f"question: {text}")
                send(chat_id, "Searching...")
                try:
                    send(chat_id, run_agent(text))
                except Exception as e:  # what broke #2: show the error instead of silence
                    send(chat_id, f"Something broke: {type(e).__name__}: {e}")
        except Exception as e:
            print("poll error", e)
            time.sleep(3)


if __name__ == "__main__":
    main()
