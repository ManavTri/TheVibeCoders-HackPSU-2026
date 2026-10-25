# Deployment: Supabase + Render + Vercel

Deployment files are checked in (`render.yaml` and `frontend/vercel.json`), but provider-side projects, credentials, and live URLs must be supplied by a project owner. This workspace does not contain deployment credentials and cannot publish the services directly.

## 1. Create and configure Supabase

1. Create a Supabase project and enable email/password sign-in under **Authentication → Providers**.
2. Open **SQL Editor**, paste and run the contents of each migration under `backend/supabase/migrations/` in timestamp order. This includes the document-type constraint migration; do not skip migrations.
3. In **Authentication → URL Configuration**, set the Site URL to the Vercel URL once known. Add local `http://localhost:5173` and the production Vercel URL to Redirect URLs.
4. In **Project Settings → API**, record the project URL, public anon/publishable key, backend service-role/service key, and the HS256 JWT secret. Confirm that the project issues HS256 tokens accepted by `SUPABASE_JWT_SECRET`; newer asymmetric signing keys require a matching verifier implementation and must not be silently treated as HS256.
5. Keep the `student-documents` bucket private. The SQL migration creates it with a 10 MB PDF limit and adds user-path policies.

## 2. Deploy the API to Render

1. Connect this GitHub repository to Render and create a Blueprint from the repository root; Render discovers `render.yaml`.
2. Set the secret values when Render prompts, or add them under the service's **Environment** page:

   | Variable | Value |
   |---|---|
   | `APP_ENV` | `production` (set by the blueprint) |
   | `REQUIRE_AUTH` | `true` (set by the blueprint) |
   | `SUPABASE_URL` | Supabase project URL |
   | `SUPABASE_SERVICE_KEY` | Supabase service-role/service key; backend only |
   | `SUPABASE_JWT_SECRET` | Supabase HS256 JWT secret; backend only |
   | `CORS_ORIGINS` | Exact Vercel origin, e.g. `https://clearledger-example.vercel.app` |
   | `SUPABASE_STORAGE_BUCKET` | `student-documents` (set by the blueprint) |
   | `MAX_UPLOAD_MB` | `10` (set by the blueprint) |
   | `LLM_API_KEY` | Optional Gemini API key; keep backend-only |
   | `LLM_MODEL` | Optional model name supported by the configured Gemini API key; there is no built-in default |
   | `LLM_TIMEOUT_SECONDS` | Optional request timeout in seconds; defaults to `45` |

3. Wait for the Render service to become healthy. Check `https://<render-service>.onrender.com/health`.
4. Copy the API origin (without `/api`) for Vercel's `VITE_API_URL`.

If the Vercel URL is not known yet, deploy Render initially with a temporary known Vercel origin, then update `CORS_ORIGINS` to the exact final origin and redeploy the backend. Never use `*` with credentials.

## 3. Deploy the web app to Vercel

1. Import the same GitHub repository into Vercel.
2. Set **Root Directory** to `frontend`; framework preset **Vite**; install command `npm ci`; build command `npm run build`; output directory `dist`.
3. Add these variables for Production (and Preview if preview deployments should access the API):

   | Variable | Value |
   |---|---|
   | `VITE_API_URL` | Render API origin, e.g. `https://clearledger-api.onrender.com` (no trailing slash and no `/api`) |
   | `VITE_SUPABASE_URL` | Supabase project URL |
   | `VITE_SUPABASE_ANON_KEY` | Supabase public anon/publishable key |

4. Deploy. Add the final Vercel origin to Supabase Auth redirect URLs and Render's `CORS_ORIGINS`, then redeploy the API if CORS changed.
5. Open the Vercel domain, create a test account, upload only synthetic PDFs, correct one extracted field, and verify the new validation report. Check the API health endpoint and Render logs if requests fail.

Only Supabase's public anon/publishable key belongs in Vercel variables. Do **not** add `SUPABASE_SERVICE_KEY`, `SUPABASE_JWT_SECRET`, or `LLM_API_KEY` to any `VITE_*` variable or Vercel client-side build setting.

## 4. Local and release checks

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
