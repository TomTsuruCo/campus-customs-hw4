# HW4 — Campus Customs

A React + Vite + TypeScript storefront with a FastAPI backend and a Pydantic AI shopping assistant. The catalogue database, original product photos, and generated white-background photos are intentionally local-only and are not included in this public source folder.

## Add the local catalogue data

Place the course-provided data pack so the project has these paths:

```text
hw4/data/campus_customs.db
hw4/data/products/*.jpg
```

From PowerShell, run the included image-preparation script once after adding the data pack. It creates the white-background product images used by the storefront:

```powershell
.\scripts\make_white_product_images.ps1
```

The database and all files under `data/` are excluded by `.gitignore`; do not add them to GitHub.

## Configure the agent

Copy `.env.example` to `.env` in this `hw4` folder and replace the placeholder with your own Portkey API key. Keep `.env` local; never put a real key in the frontend or commit it.

```powershell
Copy-Item .env.example .env
```

## Run the backend

From this `hw4` folder:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Set-Location backend
uvicorn main:app --reload --port 8000
```

Run the frontend in a second terminal:

```powershell
Set-Location frontend
npm install
npm run dev
```

Open <http://localhost:5173>. The frontend uses the local API at `http://localhost:8000` by default. For the seeded demo account, use `test@campuscustoms.yale.edu` / `password` after installing the supplied local database.

## Project notes

- `backend/main.py` is the FastAPI entry point; run it from the `backend/` folder with Uvicorn.
- `backend/agent.py`, `backend/tools.py`, `backend/models.py`, and `backend/prompts/prompt.md` define the Pydantic AI assistant, its tools and structured types, and its system prompt. `backend/audit.py` writes the append-only tool activity log to `output/audit_trail.json`.
- `output/app_check.html` is a standalone browser-check report; its screenshots are stored in `output/app_check_images/` and linked with relative paths.
- `AI_prompts.md` records the assignment prompts; `output/harness.md` describes the system, data models, safety rules, and run steps.

The password-reset flow is development-only until an email provider is configured. Do not deploy this class project with real customer data or credentials.
