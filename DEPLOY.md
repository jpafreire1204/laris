# Laris — Deployment Guide

## Architecture

- **Backend** (FastAPI + edge-tts) → Railway
- **Frontend** (React + Vite) → Vercel

---

## 1. Push to GitHub

```bash
# Create the repo at https://github.com/new (name: laris, public or private)
# Then:
git remote add origin https://github.com/YOUR_USERNAME/laris.git
git branch -M main
git push -u origin main
```

---

## 2. Deploy Backend on Railway

1. Go to [railway.app](https://railway.app) and sign in with GitHub.
2. Click **New Project → Deploy from GitHub repo** and select `laris`.
3. Railway will detect `railway.json` automatically.
4. Set environment variables in the Railway dashboard:
   - `CORS_ORIGINS` = `https://your-laris-frontend.vercel.app` (set after Vercel deploy)
5. Wait for the build to complete. Railway will assign a public URL like `https://laris-production-xxxx.up.railway.app`.
6. Verify: open `https://YOUR_RAILWAY_URL/health` — should return `{"status": "healthy"}`.

### Railway Notes
- Railway provides `$PORT` automatically — the start command uses it.
- `ffmpeg` is available by default on Nixpacks builds.
- The `outputs/` directory is ephemeral (resets on each deploy). For persistent storage, add a Railway volume mounted at `/app/outputs`.

---

## 3. Deploy Frontend on Vercel

1. Go to [vercel.com](https://vercel.com) and sign in with GitHub.
2. Click **Add New → Project** and import the `laris` repo.
3. Set the **Root Directory** to `frontend`.
4. Vercel will detect `vercel.json` and the Vite framework automatically.
5. Set environment variable:
   - `VITE_API_URL` = `https://YOUR_RAILWAY_URL` (the Railway URL from step 2, **no trailing slash**)
6. Click **Deploy**.

### After First Deploy
- Copy the Vercel URL (e.g., `https://laris.vercel.app`).
- Go back to Railway dashboard and set `CORS_ORIGINS` to include that Vercel URL.
- Redeploy Railway for the CORS change to take effect.

---

## 4. Custom Domain (optional)

### Vercel (frontend)
- Go to Project Settings → Domains → add `www.laris.com.br`.
- Point your DNS CNAME to `cname.vercel-dns.com`.

### Railway (backend)
- Go to Service Settings → Networking → Custom Domain → add `api.laris.com.br`.
- Point your DNS CNAME to the Railway-provided value.
- Update `VITE_API_URL` on Vercel to `https://api.laris.com.br`.
- Update `CORS_ORIGINS` on Railway to include `https://www.laris.com.br`.

---

## Environment Variables Summary

| Variable | Where | Value |
|---|---|---|
| `CORS_ORIGINS` | Railway (backend) | `https://your-frontend.vercel.app` |
| `VITE_API_URL` | Vercel (frontend) | `https://your-backend.up.railway.app` |

---

## Updating

Push to `main` and both Railway and Vercel will auto-deploy:

```bash
git add .
git commit -m "feat: your change"
git push
```
