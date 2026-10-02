# CodeJudge Project Report

CodeJudge is a Flask and MySQL coding platform with account registration, login, protected problem pages, Python submissions, verdicts, and submission history. Its delivery examples use Docker, Docker Compose, Jenkins, and pytest.

## Current Behavior

- Flask configuration and database credentials are read from environment variables; `.env` is ignored by Git and `.env.example` contains placeholders.
- Startup validates configuration, checks that the configured database exists, and creates missing tables with non-destructive `CREATE TABLE IF NOT EXISTS` statements.
- Passwords are stored as bcrypt hashes. Application SQL uses parameterized values.
- The judge evaluates each stored test case in a Python subprocess with a five-second timeout and records the verdict.
- `/health` checks Flask and MySQL availability.
- Docker uses a non-root user. Compose provides a persistent MySQL volume. Jenkins runs tests, builds/tags the image, deploys the app container, and waits for health.

## Database Caveat

There was no schema DDL or migration file in the repository before initialization was added. The initializer's expected schema is therefore based on the columns referenced by current routes. It does not create the database, seed problems, migrate existing tables, or delete data. See the schema and setup details in [README.md](README.md).

## Verification and Limitations

The pytest suite mocks database connections for route coverage and exercises the real local subprocess judge. Run it with `python -m pytest`. A live MySQL integration test and Docker deployment should also be run in an environment with MySQL and a Docker daemon.

Submitted Python still executes inside the Flask container. A timeout and reduced subprocess environment do not isolate filesystem, network, CPU, memory, or process access. This is not a production-grade sandbox. See [docs/DEVOPS.md](docs/DEVOPS.md) for the security boundary and production alternatives.

*** End Patch