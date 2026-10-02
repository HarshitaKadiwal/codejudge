# CodeJudge

CodeJudge is a small Flask/MySQL online judge and DevOps demonstration. Users can register, log in, browse problems, submit Python solutions, see verdicts, and review their submission history.

## Features

- bcrypt password hashing and session-based login
- Protected problem, submission, and history pages
- Parameterized MySQL queries
- Python submission evaluation with per-test input, captured output, and a five-second process timeout
- Per-user submission history
- Database-aware `/health` endpoint
- Docker, Docker Compose, Jenkins, and pytest configuration

## Architecture

```text
Browser -> Flask/Jinja application -> MySQL
						 |
						 +-> Python subprocess judge
```

The judge currently runs inside the Flask container. It is a teaching implementation, not a secure production sandbox; see [Known Limitations](#known-limitations).

Technology stack: Python, Flask, MySQL, mysql-connector-python, bcrypt, HTML/CSS/Jinja, Docker, Docker Compose, Jenkins, and pytest.

## Database Design

At startup, the application verifies that the configured database exists and creates missing tables with `CREATE TABLE IF NOT EXISTS`. It does not create the database itself, alter existing tables, seed sample problems, or delete data. The columns below describe the schema expected by the current routes and the initializer; no prior schema file was present in this repository.

| Table | Main columns | Purpose |
| --- | --- | --- |
| `users` | `id`, unique `username`, bcrypt `password` | Accounts |
| `problems` | `id`, `title`, `description`, `sample_input`, `sample_output` | Problem statements |
| `test_cases` | `id`, `problem_id`, `input_data`, `expected_output` | Evaluation cases |
| `submissions` | `id`, `username`, `problem_id`, `code`, `verdict`, `submitted_at` | Submitted source and result history |

`test_cases.problem_id` and `submissions.problem_id` reference `problems.id`. `submissions.username` references `users.username`. A problem can have many test cases and submissions; a user can have many submissions.

## How Submission Evaluation Works

1. The logged-in user posts source code to `/submit/<problem_id>`.
2. Flask loads the problem and its test cases from MySQL.
3. The judge writes the source to a temporary file and starts a fresh Python subprocess for each case.
4. Each case's `input_data` is sent to stdin; stdout is captured. A process taking more than five seconds receives `Time Limit Exceeded`.
5. Captured output and expected output are compared after trimming surrounding whitespace. Evaluation stops at the first failed case.
6. Flask stores the source and verdict in `submissions`, then renders the result.
7. The user can see past verdicts on the submission history page.

Verdicts include `Accepted`, `Wrong Answer`, `Runtime Error`, and `Time Limit Exceeded`. Runtime tracebacks are not returned to the browser.

## Environment Variables

Copy `.env.example` to `.env` and replace every `replace-with-...` value. `.env` is ignored by Git and is not copied into the Docker image.

| Variable | Required | Description |
| --- | --- | --- |
| `DB_HOST` | Yes | MySQL host; `mysql` in Compose, a reachable host for local/direct Docker runs |
| `DB_USER` | Yes | Application MySQL user |
| `DB_PASSWORD` | Yes | Application MySQL password |
| `DB_NAME` | Yes | Existing database name |
| `DB_PORT` | No | MySQL port; defaults to `3306` |
| `FLASK_SECRET_KEY` | Yes | Long, random Flask session-signing secret |
| `SESSION_COOKIE_SECURE` | No | Set to `true` when serving over HTTPS; defaults to `false` for local development |
| `MYSQL_ROOT_PASSWORD` | Compose | Root password used only to initialize the MySQL container |
| `APP_PORT` | Compose | Host port for Flask; defaults to `5000` |

Generate a Flask secret with `python -c "import secrets; print(secrets.token_hex(32))"`. Do not use the example placeholders as real credentials.

## Local Setup

Create and activate a virtual environment, install dependencies, and configure a reachable MySQL database:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env`; for a MySQL server running directly on the same machine, set `DB_HOST=127.0.0.1`. Ensure `DB_NAME` already exists and `DB_USER` can create and use tables within it. Start the app with:

```powershell
python app.py
```

Startup validates required settings, checks the database, and creates missing tables. If configuration or the database is unavailable, startup exits with a useful server-side message. The app does not automatically seed problems.

Open <http://localhost:5000>.

## Docker

Build the application image with `docker build -t codejudge-app:local .`. The image contains only runtime files and dependencies, runs as a non-root user, exposes port `5000`, and uses `/health` for its Docker health check. For a complete local application stack, use Compose below.

## Docker Compose

After configuring `.env`, start Flask and MySQL:

```powershell
docker compose up --build -d
docker compose ps
docker compose logs -f web
```

The Flask service connects to MySQL at `mysql:3306`; Compose waits for the MySQL health check before starting Flask. MySQL data persists in the `db_data` volume. `docker compose down` stops services but preserves the volume. `docker compose down -v` deletes the database volume and its data.

## Testing

Run the suite without a live MySQL service:

```powershell
python -m pytest
```

Route/database interactions are mocked where needed; judge tests execute short local subprocesses. A separate MySQL integration run is still useful when changing SQL or schema behavior.

## Jenkins CI/CD

The pipeline performs:

```text
Developer -> GitHub -> Jenkins checkout -> pytest -> Docker build/tag
		  -> deploy container -> /health verification -> running application
```

Stages are `Checkout`, `Install Dependencies`, `Run Tests`, `Build Docker Image`, `Deploy`, and `Health Check`. Images receive both a Jenkins build-number tag and `latest`. Tests failing stops the pipeline. The deploy stage replaces the named app container and exposes port `5001` by default.

The Jenkins agent needs Python 3, Docker CLI access to a running daemon, and environment/credential bindings for `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, and `FLASK_SECRET_KEY` (plus `DB_PORT` when not `3306`). `DB_HOST` must resolve from the deployed container; do not set it to the container's `localhost` unless MySQL is inside that same container. The pipeline deploys the app container, not a MySQL service.

## Security and Known Limitations

- Passwords are hashed with bcrypt; authentication queries use parameterized SQL.
- Flask sessions use HTTP-only, `SameSite=Lax` cookies. Enable `SESSION_COOKIE_SECURE` behind HTTPS.
- Database and Flask secrets are runtime configuration; do not commit `.env` or bake credentials into images.
- Submitted programs run as subprocesses in the same application container. The timeout and reduced child-process environment are useful safeguards, but submitted code is not isolated from the container filesystem, network, CPU, memory, or process resources. This Docker setup is not a production-grade sandbox.
- A production judge should execute code in short-lived isolated workers with network disabled, strict CPU/memory/process limits, minimal read-only filesystems, and a stronger boundary such as gVisor or Firecracker.
- Existing tables are never migrated. If an existing schema differs from the expected columns above, use a reviewed migration rather than assuming initialization will alter it.
- There is no problem seed script, rate limiting, CSRF protection, zero-downtime deployment, or production WSGI server configured. Jenkins deployment requires a reachable external MySQL database and briefly replaces the old app container.

## Future Improvements

Add explicit versioned SQL migrations and problem seeds, integration tests against disposable MySQL, CSRF protection and login rate limiting, and an isolated judge-worker service. A production deployment should also use a production WSGI server and an explicit rollback strategy.

See [docs/DEVOPS.md](docs/DEVOPS.md) for an interview-oriented explanation of the pipeline and deployment choices.
