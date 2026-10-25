# Deployment: Auth0 + Supabase + Render + Vercel

Deployment files are checked in (`render.yaml` and `frontend/vercel.json`), but provider-side projects, credentials, and live URLs must be supplied by a project owner. This workspace does not contain deployment credentials and cannot publish the services directly.

## 1. Create and configure Auth0

1. Create an Auth0 SPA application and an API. Use the API identifier as the audience.
2. Add the Vercel origin to the Auth0 allowed callback, logout, and web origins lists.
3. Record the Auth0 domain, SPA client ID, and API audience. Auth0 client secrets belong only in Auth0 and must not be added to the frontend.

## 2. Create and configure Supabase

1. Create a Supabase project. Supabase Auth is the fallback if Auth0 is not configured.
2. Open **SQL Editor**, paste and run the contents of each migration under `backend/supabase/migrations/` in timestamp order. This includes the document-type constraint repair migration; do not skip migrations.
3. In **Project Settings → API**, record the project URL and backend service-role/service key. The public anon key is not needed by the Muni frontend.
4. Keep the `student-documents` bucket private. The SQL migration creates it with a 10 MB PDF limit and adds user-path policies.

## 3. Deploy the API to Render

1. Connect this GitHub repository to Render and create a Blueprint from the repository root; Render discovers `render.yaml`.
2. Set the secret values when Render prompts, or add them under the service's **Environment** page:

   | Variable | Value |
   |---|---|
   | `APP_ENV` | `production` (set by the blueprint) |
   | `REQUIRE_AUTH` | `true` (set by the blueprint) |
   | `SUPABASE_URL` | Supabase project URL |
   | `SUPABASE_SERVICE_KEY` | Supabase service-role/service key; backend only |
   | `AUTH0_DOMAIN` | Auth0 tenant domain; preferred authentication provider |
   | `AUTH0_AUDIENCE` | Auth0 API audience; preferred authentication provider |
   | `SUPABASE_JWT_SECRET` | Optional Supabase HS256 secret when using Supabase Auth fallback |
   | `CORS_ORIGINS` | Exact Vercel origin, e.g. `https://muni-example.vercel.app` |
   | `SUPABASE_STORAGE_BUCKET` | `student-documents` (set by the blueprint) |
   | `MAX_UPLOAD_MB` | `10` (set by the blueprint) |
   | `LLM_API_KEY` | Optional Gemini API key; keep backend-only |
   | `LLM_MODEL` | Optional model name supported by the configured Gemini API key; there is no built-in default |
   | `LLM_TIMEOUT_SECONDS` | Optional request timeout in seconds; defaults to `45` |

3. Wait for the Render service to become healthy. Check `https://<render-service>.onrender.com/health`.
4. Copy the API origin (without `/api`) for Vercel's `VITE_API_URL`.

If the Vercel URL is not known yet, deploy Render initially with a temporary known Vercel origin, then update `CORS_ORIGINS` to the exact final origin and redeploy the backend. Never use `*` with credentials.

## 4. Deploy the web app to Vercel

1. Import the same GitHub repository into Vercel.
2. Set **Root Directory** to `frontend`; framework preset **Vite**; install command `npm ci`; build command `npm run build`; output directory `dist`.
3. Add these variables for Production (and Preview if preview deployments should access the API):

   | Variable | Value |
   |---|---|
   | `VITE_API_URL` | Render API origin, e.g. `https://muni-api.onrender.com` (no trailing slash and no `/api`) |
   | `VITE_AUTH0_DOMAIN` | Auth0 tenant domain |
   | `VITE_AUTH0_CLIENT_ID` | Auth0 SPA client ID |
   | `VITE_AUTH0_AUDIENCE` | Auth0 API audience |

4. Deploy. Add the final Vercel origin to Auth0 allowed callback/logout/web origins when using Auth0, and add Supabase Auth redirect URLs when using the fallback. Update Render's `CORS_ORIGINS`, then redeploy the API if CORS changed.
5. Open the Vercel domain, create a test account, upload only synthetic PDFs, correct one extracted field, and verify the new validation report. Check the API health endpoint and Render logs if requests fail.

Only Auth0's public SPA client ID and the public API audience, or Supabase's public anon key when using fallback Auth, belong in Vercel variables. Do **not** add `SUPABASE_SERVICE_KEY`, Auth0 client secrets, or `LLM_API_KEY` to any `VITE_*` variable or Vercel client-side build setting.

## 5. Local and release checks

Run backend tests and lint from `backend/` (for example, in WSL/Linux):

```bash
python -m pip install -e ".[test]" ruff
python -m pytest
ruff check app tests
```

Run the frontend build from `frontend/`:

```bash
npm ci
npm run build
npm audit --audit-level=moderate
```

The GitHub Actions workflow runs backend tests/lint and the frontend production build on pushes and pull requests. Render auto-deploys from the configured branch according to the Blueprint; Vercel builds each configured Git branch/deployment.

## Deployment status

The repository is deployment-configured, not provider-deployed: no Supabase project reference, Render service, Vercel project, provider authorization, or live URL was provided. After the owner connects the repository and supplies the listed environment values, record the resulting API and web URLs in the README.
