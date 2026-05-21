# WhatsApp Onboarding — Deployment Guide

Follow these steps in order. Total time: ~20 minutes.

---

## Step 1 — Set up Supabase

1. Go to https://supabase.com and sign up / log in
2. Click **New Project** → give it a name (e.g. `wa-onboarding`) → set a strong password → pick the closest region → Create
3. Wait ~2 minutes for the project to boot
4. In the sidebar go to **SQL Editor** → **New Query**
5. Paste the entire contents of `supabase_setup.sql` into the editor
6. Click **Run** — you should see "Success" and the `whatsapp_accounts` table will appear under Table Editor
7. Go to **Settings → API**:
   - Copy **Project URL** → this is your `SUPABASE_URL`
   - Copy **service_role** secret key → this is your `SUPABASE_SERVICE_KEY`
   - (Do NOT use the `anon` key for the backend — use `service_role`)

---

## Step 2 — Prepare the backend files

Make sure you have these files in one folder:

```
whatsapp_backend.py
requirements.txt
.env             ← create this yourself (copy .env.example and fill in values)
```

Create your `.env` file:

```
SUPABASE_URL=https://xxxxxxxxxxxx.supabase.co
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
META_GRAPH_VERSION=v25.0
```

**Never commit `.env` to GitHub.** Add it to `.gitignore`.

---

## Step 3 — Test locally (optional but recommended)

Make sure Python 3.10+ is installed, then run:

```bash
pip install -r requirements.txt
uvicorn whatsapp_backend:app --reload --port 8000
```

Open http://localhost:8000 in your browser. You should see:
```json
{"status": "ok", "service": "WhatsApp Onboarding API", "version": "1.0.0"}
```

Open http://localhost:8000/docs to see the interactive API docs (Swagger UI).

---

## Step 4 — Deploy to Railway (recommended — free to start)

Railway gives you a public HTTPS URL in about 2 minutes.

### 4a — Push code to GitHub

1. Create a new **private** GitHub repo (e.g. `wa-onboarding-backend`)
2. Add a `.gitignore` file with at least:
   ```
   .env
   __pycache__/
   *.pyc
   ```
3. Push `whatsapp_backend.py` and `requirements.txt` to the repo
   (Do NOT push `.env`)

### 4b — Deploy on Railway

1. Go to https://railway.app and sign up with GitHub
2. Click **New Project** → **Deploy from GitHub repo**
3. Select your `wa-onboarding-backend` repo
4. Railway will auto-detect Python and set the build command to `pip install -r requirements.txt`
5. Set the **Start command**:
   ```
   uvicorn whatsapp_backend:app --host 0.0.0.0 --port $PORT
   ```
6. Go to **Variables** tab and add:
   ```
   SUPABASE_URL        = https://xxxxxxxxxxxx.supabase.co
   SUPABASE_SERVICE_KEY = eyJ...
   META_GRAPH_VERSION  = v25.0
   ```
7. Click **Deploy** — Railway will build and start your server
8. Once deployed, click **Settings → Networking → Generate Domain**
   You'll get a URL like: `https://wa-onboarding-backend-production.up.railway.app`

Test it: open that URL in your browser — you should see the `{"status": "ok"}` response.

---

## Step 5 — Update the frontend

Open `whatsapp-onboarding.html` and find this line near the top of the `<script>` block:

```js
const HARDCODED_BACKEND_URL = '';
```

You can either:
- Leave it blank and type the Railway URL into the **Backend URL** field in the UI each time, OR
- Set it directly in the file:
  ```js
  const HARDCODED_BACKEND_URL = 'https://wa-onboarding-backend-production.up.railway.app';
  ```

Open `whatsapp-onboarding.html` in any browser (double-click it or serve it locally).

---

## Step 6 — Run a real test

1. Fill in your Meta **App ID**, **App Secret**, and **Configuration ID** in the form
2. Enter your Railway backend URL
3. Click **Connect WhatsApp Business**
4. Complete the Embedded Signup flow (use your own Facebook/Meta account for testing)
5. When done, check:
   - The UI should show "Onboarding Complete — Saved to Supabase ✓"
   - In Supabase → Table Editor → `whatsapp_accounts` → a new row should appear

---

## Step 7 — Using the saved data with webhooks / Cloud API

Each row in `whatsapp_accounts` contains everything another system needs:

| Field            | Used for                                        |
|------------------|-------------------------------------------------|
| `phone_number_id`| Sending messages via Cloud API                  |
| `waba_id`        | Managing the WhatsApp Business Account          |
| `access_token`   | Authorization header for all Graph API calls    |
| `app_id`         | Identifying which Meta app the account is under |

Example API call to send a message (using saved values):

```
POST https://graph.facebook.com/v25.0/{phone_number_id}/messages
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "messaging_product": "whatsapp",
  "to": "1234567890",
  "type": "text",
  "text": { "body": "Hello!" }
}
```

To expose account data to your webhook software, you can use the read-only endpoint:
```
GET https://your-railway-url.up.railway.app/api/accounts
```
This returns all accounts without exposing secrets.

---

## Alternative: Deploy to Render (free tier)

1. Push code to GitHub (same as Step 4a)
2. Go to https://render.com → New → Web Service → connect your repo
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn whatsapp_backend:app --host 0.0.0.0 --port $PORT`
5. Add environment variables in the Render dashboard
6. Click Deploy — you'll get an HTTPS URL after ~3 minutes

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `SUPABASE_URL` not set error | Make sure `.env` file exists and is in the same folder as `whatsapp_backend.py` |
| Token exchange returns 400 | Check that your App Secret is correct and the code hasn't expired (30s limit) |
| CORS error in browser | Your frontend domain is blocked — set `allow_origins` in `whatsapp_backend.py` to your domain |
| Row not appearing in Supabase | Check Railway logs for errors — likely a missing env var or Supabase key issue |
| `FB is not defined` in browser | The Facebook SDK hasn't loaded yet — ensure you have internet access and the `<script>` tag at the top of the HTML is present |
