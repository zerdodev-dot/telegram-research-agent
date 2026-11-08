---
title: Zero Dollar Research Agent
emoji: 💸
colorFrom: green
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
license: mit
---

# Telegram Research Agent for $0

Message the bot a question. It searches the web, reads the top pages, and replies with a short answer and sources. Built in the Zero Dollar Dev video: [link after publish].

## Run it locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in the two keys
set -a; source .env; set +a
python agent.py
```

Then message your bot on Telegram.

## Free keys

- Telegram: message @BotFather, send `/newbot`, copy the token.
- Groq: console.groq.com, create an API key. Free tier, no card.

## Deploy for free (24/7)

See `DEPLOY.md`. Hugging Face Space or Render free tier, no card.

## What broke

See the video. Short version: cap tool calls (free tier rate limits), trim page text, and show errors to the user instead of failing silently.
