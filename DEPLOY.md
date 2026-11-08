# Deploy for $0, runs 24/7

The agent uses long polling, so it needs no public URL. It also answers HTTP on `$PORT` (default 7860) so web hosts see it as healthy.

## What did not work (November 2026)

- **Hugging Face Spaces**: Docker Spaces now require a paid PRO plan. Only Static Spaces are free. Dead end for this project.

## Option A: Render free web service (recommended)

Free: 750 instance hours per month per workspace, enough for one service running all month. Limits: 512 MB RAM, spins down after 15 minutes without HTTP traffic. We keep it awake with a free ping.

1. Push this folder to GitHub (public repo).
2. render.com, sign up with GitHub. If Render asks for a credit card at any point, stop and use Option B instead.
3. New, **Web Service**, connect the repo.
4. Settings:
   - Language: **Docker** (Render reads the Dockerfile)
   - Instance type: **Free**
   - Environment variables: `TELEGRAM_TOKEN`, `GROQ_API_KEY`, `MODEL=openai/gpt-oss-120b`
5. Create Web Service. First build takes 2 to 4 minutes. Logs should show `agent running, cost so far: $0`.
6. Copy the service URL, like `https://telegram-research-agent.onrender.com`. Opening it shows `zero dollar agent: running`.

### Keep it awake, also free

cron-job.org (free, no card): create a job that GETs your Render URL every 10 minutes. Render then never spins the service down, and 750 hours covers the whole month.

Fair-use note: Render's free docs say not to use free services for production. A personal bot for a video is within reason. If they tighten the rule, move to Option B.

## Option B: Koyeb free instance

One free "nano" web service. Same Dockerfile, same environment variables. Check whether a card is required on the day you sign up.

## Option C: Your own machine

`docker run -d --restart unless-stopped --env-file .env -p 7860:7860 zerodollar-agent`. Truly $0 while the computer is on.

## Only one poller at a time

Telegram lets one process poll a bot token. Stop the local bot or container before the hosted one starts, or you get `409 Conflict` in the logs.
