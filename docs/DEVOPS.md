# DevOps Guide for CodeJudge
This document explains the core DevOps concepts showcased by CodeJudge. It is written to be interview-friendly and practical. Each section explains what the concept is, why this project uses it, and where it appears.

## CI vs CD

- What: Continuous Integration (CI) runs automated builds and tests on changes. Continuous Delivery/Deployment (CD) automates packaging and deployment to environments.
- Why: Ensures regressions are caught early and deployment is repeatable.
- Where: `Jenkinsfile` defines a CI pipeline that runs tests and builds Docker images.

## Jenkins Pipeline

- What: A scriptable pipeline describing stages run on Jenkins agents.
- Why: Provides reproducible, auditable build steps and integrates with SCM.
- Where: `Jenkinsfile` contains stages: Checkout, Install Dependencies, Run Tests, Build Docker Image, Run Container & Health Check.

## Docker & Dockerfile

- What: Docker packages the application and its runtime into an image.
- Why: Portable artifact for consistent deployments across environments.
- Where: `Dockerfile` builds a Python-slim image, installs dependencies, creates a non-root user, and sets a healthcheck.

## Docker Compose

- What: A YAML format to define multi-container applications.
- Why: Local multi-container orchestration for app + database with a single command.
- Where: `docker-compose.yml` defines `web` and `mysql` services and persistent volume for MySQL.

## Image Tagging

- What: Assign unique tags to images (e.g., build numbers).
- Why: Artifacts are traceable to a build.
- Where: `Jenkinsfile` builds `codejudge-app:${BUILD_NUMBER}` and tags `latest`.

## Health Checks

- What: Small endpoints or checks that prove the app is responding.
- Why: Detect runtime failures; used by containers and CI to validate deployment.
- Where: `/health` endpoint and Docker HEALTHCHECK in `Dockerfile`.

## Secrets & Environment Variables

- What: Sensitive configuration should be injected at runtime, not committed.
- Why: Prevents secret leakage and allows different values per environment.
- Where: `database/db.py` reads DB config from env vars; `.env.example` shows required variables.

## Testing & pytest

- What: Unit tests validate behavior automatically.
- Why: Prevent regressions and allow safe refactoring.
- Where: `tests/` contains tests for health, auth, and judge logic; Jenkins runs `pytest`.

## Running Untrusted Code (Security)

- What: Executing user-submitted code carries risk.
- Why: Submitted code can access host resources, spawn processes, or exhaust CPU/memory.
- Project choice: The judge currently runs code in a subprocess. This is simple for teaching but insecure.
- Safer options: Run submissions inside short-lived, resource-limited Docker containers with no network access and restricted filesystem. Consider using gVisor, Firecracker, or dedicated sandbox services in production.

## Logs

- What: Structured logs help diagnose issues.
- Why: Essential for debugging and auditing.
- Where: `app.py` uses Python `logging` for key events.

## Future Improvements

- Use a proper task queue for judging (e.g., Celery) and isolate execution in containers.
- Add dependency vulnerability scanning (e.g., `safety`, `bandit`, or GitHub Dependabot).
- Add backup and migration scripts for database.

## Where to look in the repo

- Application: `app.py`
- DB: `database/db.py`
- Judge: `judge/judge.py`
- Docker: `Dockerfile`, `docker-compose.yml`
- CI: `Jenkinsfile`
- Tests: `tests/`

