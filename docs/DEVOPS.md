# CodeJudge DevOps Guide

This guide describes the project's current, deliberately small CI/CD flow and the boundaries it does not provide.

## Architecture

```text
Browser -> Flask/Jinja app -> MySQL
										|
										+-> Python subprocess judge
```

Compose runs Flask and MySQL as separate services. The app uses `mysql` as its database hostname, and MySQL data is stored in the named `db_data` volume. The judge subprocess runs inside the Flask service container; it is not a separate worker or sandbox.

## Developer-to-Deployment Flow

```text
Developer
	-> GitHub
	-> Jenkins checkout
	-> install requirements
	-> pytest
	-> build and tag Docker image
	-> replace app container
	-> wait for /health
	-> report pipeline result
```

The declarative pipeline in `Jenkinsfile` has these stages:

1. `Checkout` retrieves the configured SCM revision.
2. `Install Dependencies` creates a virtual environment and installs `requirements.txt`.
3. `Run Tests` runs pytest; a failure stops subsequent stages.
4. `Build Docker Image` tags the image with the Jenkins build number and `latest`.
5. `Deploy` replaces the `codejudge-app` container and starts the newly tagged image.
6. `Health Check` waits for Docker's health status, which calls `/health` and verifies MySQL with `SELECT 1`.

The Jenkins agent needs Python 3, a Docker CLI and access to a running Docker daemon. Configure `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, and `FLASK_SECRET_KEY` as agent environment values or Jenkins credentials; configure `DB_PORT` if it is not `3306`. The database must already exist and be reachable from the new application container. The `DB_HOST` value cannot be `localhost` when MySQL is in another container. The deploy stage replaces the prior container, so it may cause brief downtime.

## Docker Image

`Dockerfile` uses Python 3.11 slim, installs pinned requirements before copying application runtime files, runs as a non-root user, and exposes port `5000`. The Docker health check uses Python's standard library, so it does not require `curl`. `.dockerignore` keeps tests, docs, local environments, and secrets out of the image build context.

The image starts `python app.py`. Startup validates required settings, checks the configured database, and creates absent tables. It does not create a missing database or modify existing tables.

## Docker Compose

Copy `.env.example` to `.env`, replace the placeholder values, then run `docker compose up --build -d`. Compose starts MySQL with a scoped application user and waits for its health check before starting Flask. The application connects to `mysql:3306`, not `localhost:3306`.

The `db_data` volume survives `docker compose down`. Removing the volume with `docker compose down -v` deletes the MySQL data. MySQL initialization variables apply when the volume is first created; changing those values later does not rewrite an existing database account.

## Configuration and Secrets

The app requires `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, and `FLASK_SECRET_KEY`. `DB_PORT` defaults to `3306`. Compose additionally requires `MYSQL_ROOT_PASSWORD`; that credential initializes the database service and is not used by Flask. `SESSION_COOKIE_SECURE` should be enabled when the application is served over HTTPS.

`.env` is excluded from Git and the Docker image. `.env.example` contains placeholders only. Jenkins must receive deployment credentials outside source control. Do not put real values in `Jenkinsfile`, Docker build arguments, or image layers.

## Database and Tests

`database/db.py` checks `INFORMATION_SCHEMA` for the configured database, retries selected transient connection errors up to three attempts, and runs only `CREATE TABLE IF NOT EXISTS`. The schema is inferred from the app's existing SQL because no earlier DDL or migration file was present. Existing tables are not altered; mismatches require an explicit reviewed migration.

The pytest suite covers auth, access control, problem listing, accepted/incorrect submissions, submission history, health behavior, DB initialization behavior, and judge results. Most database interactions are mocked, so tests do not need a live MySQL server. Validate SQL and migrations separately against MySQL before deploying schema changes.

## Health and Logs

`GET /health` returns success only when Flask can also execute `SELECT 1` against MySQL. Docker and Jenkins use this endpoint to verify readiness. User-facing error responses are generic; database failures, unexpected application errors, startup, and verdicts are logged server-side without returning internal tracebacks in the page.

## Code Execution Security

The judge starts Python subprocesses with a five-second timeout and a reduced environment that omits the app's database and Flask secrets. These measures are not a security boundary. Submitted code still runs under the app container's user and can access resources available to that container, including filesystem and network access; CPU, memory, process count, and descendant processes are not comprehensively constrained.

Do not describe this Docker setup as a production-grade sandbox. A stronger production design would use short-lived isolated workers, disable network access, enforce CPU/memory/process limits, mount a minimal read-only filesystem, and add a hardened boundary such as gVisor or Firecracker. That infrastructure is intentionally outside this student project.

## Further Work

Good next steps are versioned SQL migrations and seed data, a disposable-MySQL integration test job, CSRF protection and login rate limiting, a production WSGI server, and a dedicated isolated judge worker with an explicit deployment rollback strategy.

