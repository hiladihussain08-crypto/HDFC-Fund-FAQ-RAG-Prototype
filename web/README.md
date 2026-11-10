# Fund FAQ assistant (Next.js frontend)

Chat UI for the HDFC Mutual Fund FAQ assistant. Talks to the FastAPI backend
in `../api/main.py`.

## Run locally

1. Start the backend (from the repo root):
   ```
   uvicorn api.main:app --host 0.0.0.0 --port 8000
   ```
   with `API_KEY` set in your environment.

2. In this folder:
   ```
   npm install
   npm run dev
   ```
   Open http://localhost:3000.

## Environment variables

Copy `.env.example` to `.env.local` and fill in:

- `BACKEND_URL` — backend base URL (default `http://localhost:8000`)
- `API_KEY` — must match the backend's `API_KEY`

`.env.local` is gitignored; never commit secrets.

## Vercel

Set the project's root directory to `web`. Add `BACKEND_URL` and `API_KEY`
as environment variables in the Vercel dashboard. The backend itself is
hosted on Hugging Face Spaces (Docker, port 7860).