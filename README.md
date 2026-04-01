# Seekle

[Seekle](https://seekle.io) is an Answer Engine Optimization (AEO) platform. Ask a question and Seekle routes it to the most suitable AI provider(s), selects the strongest response, and returns one clear answer with verifiable citations — so you're not limited to a single model's knowledge or browsing ability.

It's built for anyone who needs fast, sourced answers: founders doing research, marketers understanding AI-driven discovery, operators cutting down on tab-switching, and researchers following citations.

---

## Running locally

**Requirements:** Python 3.11+, Node.js 18+, a Postgres database.

### Backend

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in your API keys
uvicorn app.main:app --reload
```

### Frontend

```bash
cd seekle-frontend
npm install
npm run dev
```

---

## Environment variables

Create a `.env` file in the project root. All secrets are read from environment — nothing is hardcoded. See `app/config.py` for the full list with defaults.

---

## Deployment

Backend is configured for [Render](https://render.com) via `render.yaml`. Set environment variables in the Render dashboard.

The frontend deploys to Vercel or any Next.js-compatible host.
