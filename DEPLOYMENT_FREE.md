# Free Public Deployment Guide — Toing G Telegram Mini App

This guide walks you through deploying the complete **Toing G** full-stack platform (Telegram Mini App Frontend + FastAPI Backend + PostgreSQL Database + Telegram Bot) **100% FREE** with zero upfront or recurring costs.

---

## Architecture Overview

| Component | Recommended Free Host | Free Tier Limits | SSL / Domain |
| :--- | :--- | :--- | :--- |
| **Frontend (React Mini App)** | **Vercel** / **Cloudflare Pages** | Unlimited builds, 100 GB/mo bandwidth | Free HTTPS (`*.vercel.app`) |
| **Backend (FastAPI + Bot)** | **Render.com** or **Koyeb** or **Oracle Cloud** | 750 free hrs/mo (Render), 550 hrs/mo (Koyeb), Always Free (Oracle) | Free HTTPS (`*.onrender.com`) |
| **Database (PostgreSQL)** | **Neon.tech** or **Supabase** | 0.5 GB Serverless Postgres (Neon), 500 MB (Supabase) | SSL connection string |
| **Telegram Bot & Mini App** | **Telegram BotFather** | 100% Free forever | In-app native WebApp |

---

## Step 1: Deploy Free PostgreSQL Database (Neon.tech)

1. Go to [https://neon.tech](https://neon.tech) and sign up with GitHub or Google (free, no credit card required).
2. Click **Create Project** -> Name it `toing-db`.
3. Neon provides a connection string formatted as:
   ```text
   postgresql://username:password@ep-xyz.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```
4. For FastAPI SQLAlchemy with `asyncpg`, prefix the protocol with `postgresql+asyncpg://`:
   ```text
   postgresql+asyncpg://username:password@ep-xyz.us-east-2.aws.neon.tech/neondb?ssl=require
   ```
   *(Save this as your `DATABASE_URL`)*.

---

## Step 2: Deploy Backend to Render.com (100% Free)

1. Push your repository to GitHub (`toing_platform`).
2. Go to [https://render.com](https://render.com) and log in with GitHub.
3. Click **New +** -> **Web Service**.
4. Select your `toing_platform` repository.
5. Set the service settings:
   - **Root Directory**: `backend`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
6. Add **Environment Variables** in Render Dashboard:
   - `DATABASE_URL`: Your Neon PostgreSQL async connection string from Step 1.
   - `BOT_TOKEN`: Your Telegram Bot token from `@BotFather`.
   - `X_USER_KEY`: `TNG-EMJ9-SATT-NVHL` (or your Toing API access key).
   - `MINI_APP_URL`: Your public frontend URL (will configure in Step 3).
   - `PORT`: `10000`
7. Click **Create Web Service**.
8. Render will build and deploy your API with free HTTPS:
   `https://toing-backend.onrender.com`

> **Note on Render Free Tier Sleep**: Render spins down free web services after 15 minutes of inactivity. To keep your live order tracker and bot alive 24/7 for free, add a free monitor on [https://cron-job.org](https://cron-job.org) or [https://uptimerobot.com](https://uptimerobot.com) to ping `https://toing-backend.onrender.com/api/v1/health` every 10 minutes.

---

## Step 3: Deploy Frontend to Vercel (100% Free)

1. Go to [https://vercel.com](https://vercel.com) and sign in with GitHub.
2. Click **Add New...** -> **Project**.
3. Import your GitHub repository.
4. Set the project configuration:
   - **Framework Preset**: `Vite`
   - **Root Directory**: `frontend`
5. In **Environment Variables**, add:
   - `VITE_API_BASE`: `https://toing-backend.onrender.com/api/v1`
6. Click **Deploy**.
7. In ~30 seconds, Vercel gives you a live HTTPS URL:
   `https://toing-g.vercel.app`

---

## Step 4: Configure Telegram Mini App in @BotFather

1. Open Telegram and search for `@BotFather`.
2. Send `/mybots` -> Select your bot (or `/newbot` to create one).
3. **Set Up the Mini App**:
   - Send `/newapp` -> Select your bot.
   - Enter App Title: `toing G`
   - Enter App Short Description: `Fast 10-Minute Food Delivery & Discount Bot`
   - Upload App Icon (640x360 px image).
   - When asked for the Web App URL, enter your Vercel URL:
     `https://toing-g.vercel.app`
   - Choose a short name (e.g. `order` -> URL becomes `t.me/your_bot/order`).
4. **Set Bottom Menu Button**:
   - Send `/setmenubutton` -> Select your bot.
   - Enter Button Text: `🛒 Order Food`
   - Enter WebApp URL: `https://toing-g.vercel.app`

---

## Step 5: Test & Verify

1. Open your Telegram bot in the Telegram mobile or desktop app.
2. Click the bottom-left `🛒 Order Food` button.
3. The Mini App opens in native full-screen with real user isolation (`telegram_id`).
4. Users can paste their session JSON, search restaurants, apply coupons, auto-build ₹1 carts, and track orders with live status updates!
