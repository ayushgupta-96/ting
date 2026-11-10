# Toing Telegram Bot & Mini-App Platform (1k–5k Concurrent Users)

A high-performance Telegram Bot and Telegram Mini-App platform integrating with the Toing e-commerce infrastructure, engineered from HAR reference network traces.

---

## Architecture Overview

```
                        ┌──────────────────────────────────────────────┐
                        │              Telegram Client                 │
                        │   (Bot Commands / Mini-App WebApp View)      │
                        └──────────────────────┬───────────────────────┘
                                               │
                           Telegram InitData / REST API
                                               │
                                               ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                FastAPI Gateway (:8000)                                 │
│  ├── /api/v1/auth       (WebApp Validation, Session Token Rotation, Address Book)       │
│  ├── /api/v1/catalog    (Restaurant Discovery, Menu Search, Outlets)                   │
│  ├── /api/v1/cart       (Cart Calculation, Tax & Fee Breakdown, Cart ID Sync)          │
│  └── /api/v1/orders     (Direct Checkout Placement, Coupon Optimization, UPI/COD)      │
└──────────────┬───────────────────────────────┬───────────────────────────────┬─────────┘
               │                               │                               │
               ▼                               ▼                               ▼
    ┌────────────────────┐          ┌────────────────────┐          ┌────────────────────┐
    │   PostgreSQL 15    │          │     Redis 7.0      │          │    Toing Client    │
    │  (Users, Orders,   │          │  (Active Sessions, │          │   (HTTP/2 Async,   │
    │   Session State)   │          │    Cart Cache)     │          │  x-user-key Pool)  │
    └────────────────────┘          └────────────────────┘          └─────────┬──────────┘
                                                                              │
                                                                              ▼
                                                                 https://storelex.store/toing_web
```

---

## 1. Network Extraction Summary (from `storelex.store.har`)

- **Total Entries in HAR**: 155 requests
- **Unique API Endpoints**: 20 endpoints
- **Key Authentication Protocol**:
  - `POST /toing_web/api/auth/validate_webapp` with `{ "init_data": "<telegram_init_data>" }`
  - Returns: `{ "valid": True, "user_id": ..., "access_key": "TNG-...", "accounts_count": ... }`
  - All subsequent calls inject header: `x-user-key: <access_key>`
- **Direct Checkout Mechanism**:
  - In the reference web UI, `/toing_web/api/me` is checked for account wallet balance (`fee > 0 && balance < fee`), presenting a deposit barrier.
  - In this backend implementation, requests proceed directly to `POST /toing_web/api/checkout/place` with `{ mobile, cart_id, address_id, lat, lng, amount, method, snap }`, enabling smooth checkout without frontend fee interruptions.

---

## 2. Directory Structure

```text
toing_platform/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI lifespan & app setup
│   │   ├── core/
│   │   │   ├── config.py            # Pydantic Settings
│   │   │   ├── database.py          # SQLAlchemy Async Engine & connection pool
│   │   │   ├── redis.py             # Redis session manager
│   │   │   └── security.py          # Telegram initData HMAC verification
│   │   ├── models/
│   │   │   └── user.py              # User & OrderRecord models
│   │   ├── schemas/
│   │   │   ├── auth.py              # DTOs for Auth
│   │   │   ├── catalog.py           # DTOs for Restaurants & Menu
│   │   │   ├── cart.py              # DTOs for Cart
│   │   │   └── order.py             # DTOs for Checkout & Payment
│   │   ├── services/
│   │   │   ├── toing_client.py      # HTTP/2 Async external API client
│   │   │   └── session_manager.py   # Token caching & mobile switcher
│   │   ├── api/
│   │   │   ├── deps.py              # Auth dependencies
│   │   │   └── v1/
│   │   │       ├── api.py           # V1 Router aggregator
│   │   │       └── endpoints/
│   │   │           ├── auth.py
│   │   │           ├── catalog.py
│   │   │           ├── cart.py
│   │   │           └── orders.py
│   │   └── bot/
│   │       ├── loader.py            # aiogram 3.x bot initialization
│   │       └── handlers/
│   │           ├── start.py         # /start with Mini-App WebApp button
│   │           └── auth.py          # /status and /orders
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Header.jsx           # Store header & mobile session switcher
│   │   │   ├── RestaurantList.jsx   # Restaurant discovery cards
│   │   │   ├── MenuList.jsx         # Category & Item selection
│   │   │   ├── CartDrawer.jsx       # Cart view & delivery address selection
│   │   │   └── CheckoutModal.jsx    # Cash on delivery / UPI payment modal
│   │   ├── services/
│   │   │   └── api.js               # Axios client with @twa-dev/sdk integration
│   │   ├── App.jsx                  # Main TanStack Query UI state orchestrator
│   │   ├── main.jsx
│   │   └── index.css
│   ├── index.html
│   ├── package.json
│   ├── tailwind.config.js
│   └── vite.config.js
├── docker-compose.yml
├── parse_har.py                     # HAR parsing utility
└── endpoints_summary.json           # Extracted endpoint dictionary
```

---

## 3. Quickstart & Deployment

### Step A: Configure Environment Variables

Edit `backend/.env`:
```env
PORT=8001
HOST="0.0.0.0"
BOT_TOKEN="your_telegram_bot_token"
MINI_APP_URL="https://your-mini-app-domain.com"
TOING_BASE_URL="https://storelex.store/toing_web"
DATABASE_URL="postgresql+asyncpg://postgres:postgrespassword@postgres:5432/toing_db"
REDIS_URL="redis://redis:6379/0"
```

### Step B: Launch the Backend

#### Option 1: Direct Python Runner (With Auto-Port Detection)
```bash
cd backend
python run.py
```
> If port 8000 (or the configured port) is occupied, `run.py` automatically detects it and binds to the next free port (`8001`, `8002`, etc.).

#### Option 2: Docker Compose (Recommended for 1k–5k Users)
```bash
docker-compose up --build -d
```
This deploys:
- PostgreSQL with persistent storage.
- Redis caching pool.
- FastAPI multi-worker backend serving on `http://localhost:8001`.

### Step C: Run Frontend Mini-App

```bash
cd frontend
npm install
npm run dev
```

For production build:
```bash
npm run build
```
Host the `dist/` directory on any HTTPS provider (Vercel, Netlify, Cloudflare Pages, or Nginx) and configure your Telegram Bot's WebApp URL in BotFather to point to it.
