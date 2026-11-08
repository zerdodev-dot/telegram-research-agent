# Deploy for $0, runs 24/7

The agent uses long polling, so it needs no public URL. Any free host that runs a Python process works.

## Option A: Hugging Face Space (recommended, no card, does not sleep while active)

1. huggingface.co, New Space, SDK: Docker, hardware: CPU basic (free).
2. Push this folder with the `Dockerfile` below.
3. Space settings, Variables and secrets: add `TELEGRAM_TOKEN` and `GROQ_API_KEY` as secrets.

```Dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY agent.py .
CMD ["python", "agent.py"]
```

Free Spaces pause after 48 h without visits. Fix: a free cron ping (cron-job.org) to the Space URL every 12 h, or accept the pause for a demo.

## Option B: Render free Background Worker

Render's free tier covers web services that sleep. A polling bot needs a worker, which is paid. Skip unless you switch to webhooks.

## Option C: Your own machine

`python agent.py` in a tmux session. Literally $0, as long as the laptop is on. Good enough for the video demo.
