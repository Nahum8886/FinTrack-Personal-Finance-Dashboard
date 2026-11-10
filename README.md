# FinTrack — Personal Finance Dashboard

Full-stack personal finance dashboard built with Flask, SQLite, JavaScript and Chart.js.

## Features
- Registration/login with Werkzeug password hashing, signed sessions, CSRF tokens and per-user records
- Add/delete dated transactions, category charts, search and type filtering
- Monthly budgets, savings goals and Python-generated financial insights
- CSV export with spreadsheet-formula injection protection
- Responsive dark fintech interface and automated tests

## Run locally (Windows PowerShell)

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:SECRET_KEY = (py -c "import secrets; print(secrets.token_hex(32))")
.\.venv\Scripts\python.exe app.py
```

Open http://127.0.0.1:5000 and create an account.

### Keep your old data
**Back up the entire old project, especially `finance.db`, before starting.** Put a *copy* of the old `finance.db` in this new project's root. Start the application, register your account, stop the server, then run:

```powershell
$env:FLASK_APP = 'app'
.\.venv\Scripts\python.exe -m flask claim-legacy
```

Enter your new account email and type `CLAIM` when prompted. This explicitly assigns previously unowned transactions, budgets and savings goals to your account. Old transactions without dates are assigned the migration date; review them before trusting monthly comparisons. Legacy databases may have different column names or constraints: keep your backup and check the database migration before importing production data.

## Run tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## GitHub

1. Create a **private** GitHub repository first.
2. In the project folder run:

```powershell
git init
git add .
git commit -m "Build FinTrack full-stack finance dashboard"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/fintrack.git
git push -u origin main
```

Do not commit `finance.db`, `.env`, passwords or other personal financial data. `.gitignore` excludes these by default. Make the repository public only after reviewing its history for secrets and data.

## Live deployment

`render.yaml` is an **example** configuration for Render with a persistent disk (usually a paid service). Import your GitHub repo as a Blueprint, verify the plan and billing before deploying, and keep the generated `SECRET_KEY` private. The server runs using Gunicorn; SQLite lives at `/var/data/finance.db` on the persistent disk. Do not deploy with Flask debug mode enabled. For multi-instance or larger production use, migrate to PostgreSQL. A free ephemeral filesystem is **not safe** for persistent financial records.

This is a portfolio learning project, not a banking application. It lacks production-grade rate limiting, email verification, password reset, MFA, monitoring, backup automation, and formal security review. Do not store bank credentials or sensitive real-world financial information in a public demo. Use sample data.

## Security notes

The CSRF token is returned after login and stored in the page session. Flask's signed cookie requires a stable secret in production. HTTPS-only cookies require `COOKIE_SECURE=1`. The app uses SQLite parameterised queries and user-scoped data access. For a public deployment, add account lockout/rate limiting, backup/restore processes, and stricter operational controls before treating it as production-ready.
