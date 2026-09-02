# Shop Inventory — cloud item database with approval workflow

## Architecture
```
[JS frontend, static]  --HTTPS-->  [FastAPI backend, Render free tier]  --SQL-->  [Supabase Postgres, free tier]
      (Netlify/Vercel                  JWT auth, role checks,                (500MB, also hosts
       or Render static)                approval workflow                    item images in Storage)
```

- **Database:** Supabase Postgres (free). Also gives you a Storage bucket for item images in the same account — no separate image host needed.
- **Backend:** FastAPI on Render's free web service. Handles auth, search, CRUD, and the approval workflow.
- **Frontend:** Plain HTML/CSS/JS, no framework, no build step — one `index.html` under ~15KB total. Works fine in any Android browser. Host it free on Netlify, Vercel, or Render Static Sites.

## Data model
- `users`: id, username, email, password_hash, role (`admin` / `staff`), created_at
- `items`: item_no (PK), category, name, price, description, images (JSON list of URLs), keywords (JSON list), date_added, date_updated
- `pending_changes`: id, item_no, action (create/update/delete), payload (JSON), status (pending/approved/rejected), submitted_by, submitted_at, reviewed_by, reviewed_at, admin_note

## How the approval workflow works
- **Admin** writes (create/update/delete) apply to `items` immediately.
- **Staff** writes are saved as a row in `pending_changes` with `status=pending` instead of touching `items`.
- Admin opens the "Pending" tab, reviews the proposed payload, and approves or rejects. Approving atomically applies the change to `items`.
- Everyone (admin and staff) can read/search `items` freely once logged in.

## Setup

### 1. Database — Supabase
1. Create a free project at supabase.com.
2. In **Storage**, create a public bucket named `item-images`.
3. Copy your project's Postgres connection string (Settings → Database → Connection string, "Session pooler" mode works well with Render's free tier) and your **service_role** key (Settings → API) — you'll need both.

### 2. Backend — Render
1. Push the `backend/` folder to a GitHub repo.
2. On render.com, create a new **Web Service** from that repo (the included `render.yaml` auto-configures it — Render calls this a Blueprint).
3. Set the environment variables it asks for: `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `FIRST_ADMIN_USERNAME`, `FIRST_ADMIN_EMAIL`, `FIRST_ADMIN_PASSWORD`.
4. Deploy. On first boot the app creates the tables and seeds your admin account automatically.
5. Note the live URL Render gives you, e.g. `https://shop-inventory-api.onrender.com`.

Render's free tier sleeps after 15 minutes idle — the first request after that takes ~30-60s to wake up. Fine for a small shop tool; if that ever bothers you, a paid Starter plan ($7/mo) removes it.

### 3. Frontend
1. In `frontend/app.js`, set `API_BASE` to your Render URL from step 2.
2. Deploy the `frontend/` folder as a static site (Netlify drag-and-drop, Vercel, or Render Static Sites — all free).
3. Open the site, log in with the admin account you set in step 2, and start adding items.

## Local development
```bash
cd backend
cp .env.example .env   # fill in your real values
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Then open `frontend/index.html` directly in a browser (set `API_BASE` to `http://127.0.0.1:8000` for local testing).

## API summary
| Method | Path | Who | Effect |
|---|---|---|---|
| POST | `/auth/register` | anyone | creates a `staff` account |
| POST | `/auth/login` | anyone | returns JWT |
| GET | `/items` | logged in | list items |
| GET | `/items/search?q=` | logged in | search by name/category/description/item_no/keywords |
| GET | `/items/{item_no}` | logged in | item detail |
| POST | `/items/upload-image` | logged in | uploads a file to Supabase Storage, returns URL |
| POST | `/items` | admin: applies / staff: proposes | create item |
| PUT | `/items/{item_no}` | admin: applies / staff: proposes | update item |
| DELETE | `/items/{item_no}` | admin: applies / staff: proposes | delete item |
| GET | `/pending` | admin only | list pending changes |
| POST | `/pending/{id}/review` | admin only | approve or reject a change |

## Notes / next steps worth knowing about
- To promote a `staff` user to `admin`, update their `role` column directly in Supabase's table editor — there's no self-service promotion endpoint (intentionally, so it always requires deliberate admin action).
- `item_no` is whatever scheme you choose (e.g. `BK-0001`) — the system doesn't auto-generate it, so agree on a numbering convention for your catalog.
- CORS in `main.py` is wide open (`*`) to make setup easy; once your frontend domain is fixed, narrow `allow_origins` to it.
