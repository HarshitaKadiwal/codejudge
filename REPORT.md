# CodeJudge Migration Report

## Files created
- `.gitignore`
- `.dockerignore`
- `.env.example`
- `docker-compose.yml`
- `docs/DEVOPS.md`
- `REPORT.md`
- `tests/test_auth.py`
- `tests/test_judge.py`

## Files modified
- `app.py` (load env, logging, bcrypt password hashing, dotenv)
- `database/db.py` (use env vars, parameterize connection)
- `judge/judge.py` (minor cleanup, safe writes)
- `Dockerfile` (non-root user, healthcheck, caching)
- `Jenkinsfile` (pipeline stages, tagging, health check)
- `requirements.txt` (added `python-dotenv`, `bcrypt`)
- `README.md` (expanded)
- `docs/DEVOPS.md` (expanded)
- `tests/test_app.py` (improved)

## Important changes
- Passwords are hashed with `bcrypt` on registration and verified on login.
- Database configuration moved to environment variables and `.env.example` provided.
- Dockerfile improved to use non-root user and include HEALTHCHECK.
- Docker Compose added to run `web` + `mysql` together with a persistent volume.
- Jenkinsfile updated for proper build/test/tag/deploy workflow and health verification.
- Tests expanded and now mock DB interactions for auth tests.

## How to run

Local (dev):

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
copy .env.example .env
# edit .env to set DB_PASSWORD and other values if needed
python app.py
```

Docker build:

```bash
docker build -t codejudge-app:local .
```

Docker run (with host DB):

```bash
docker run -e DB_HOST=host.docker.internal -e DB_USER=root -e DB_PASSWORD=example_password -p 5000:5000 codejudge-app:local
```

Docker Compose:

```bash
docker compose up -d
docker compose down
```

Run tests:

```bash
python -m pytest
```

## Jenkins pipeline stages
1. Checkout
2. Install Dependencies
3. Run Tests
4. Build Docker Image (tagged with build number)
5. Run Container & Health Check

## Environment variables
- `DB_HOST`
- `DB_USER`
- `DB_PASSWORD`
- `DB_NAME`
- `DB_PORT`
- `FLASK_SECRET_KEY`

See `.env.example` for an example.

## Security improvements
- Passwords hashed with bcrypt
- No credentials committed; `.env` ignored
- Database connection uses parameterized `mysql-connector` queries
- Docker runs app as non-root user
- Added notes and docs explaining that running untrusted code is insecure and providing safer recommendations

## Known limitations & manual steps
- The judge runs submitted code in the app container as a subprocess — insecure for production. Use containerized sandboxes in future.
- Jenkins/HOST-specific Docker and network settings must be configured on your Jenkins agents.
- MySQL user/password in `docker-compose.yml` is an example and should be changed.
- You must create the database schema and seed problems/test_cases manually or via migration scripts (not included).

*** End Patch