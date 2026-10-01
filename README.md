# CodeJudge

CodeJudge is a simple Flask-based online coding platform intended as a beginner-friendly DevOps demonstration project. It demonstrates a complete CI/CD workflow using GitHub, Jenkins, Docker, and Docker Compose with automated testing via pytest.

## Summary
- Flask web app for submitting Python code to small problems
- MySQL for storing users, problems, test cases, and submissions
- Judge executes submitted Python code (see security notes)
- Dockerfile, docker-compose, and Jenkins pipeline included

## Project Structure

- `app.py` - Flask application and routes
- `database/db.py` - database connection (reads env vars)
- `judge/judge.py` - simple judge that runs Python code (UNTRUSTED)
- `templates/` - HTML templates
- `static/` - CSS and assets
- `tests/` - pytest tests
- `Dockerfile`, `docker-compose.yml`, `Jenkinsfile` - DevOps artifacts

## Quickstart - Local (without Docker)

1. Create and activate a virtualenv

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

2. Install dependencies

```bash
python -m pip install -r requirements.txt
```

3. Provide database environment variables (example in `.env.example`) and run the app

```bash
copy .env.example .env
# edit .env to set DB_PASSWORD and FLASK_SECRET_KEY
python app.py
```

4. Open http://localhost:5000

## Running with Docker

Build the image:

```bash
docker build -t codejudge-app:local .
```

Run the container:

```bash
docker run -e DB_HOST=host.docker.internal -e DB_USER=root -e DB_PASSWORD=example_password -p 5000:5000 codejudge-app:local
```

The container exposes a `/health` endpoint used for health checks.

## Running with Docker Compose

Start the app and MySQL together:

```bash
docker compose up -d
```

Stop and remove:

```bash
docker compose down
```

## Tests

Run pytest locally:

```bash
python -m pytest
```

Jenkins is configured to run tests as part of the pipeline and will fail the build if tests fail.

## Environment Variables
See `.env.example` for an example of required environment variables. Important vars:

- `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `DB_PORT`
- `FLASK_SECRET_KEY`

## Security Notes

- Passwords are hashed with `bcrypt` before storage.
- Database credentials and secrets must be provided via environment variables or a `.env` file (not committed).
- The judge executes untrusted code by running Python in a subprocess. This is NOT secure for production. See `docs/DEVOPS.md` for safer alternatives and recommendations.

## Jenkins

The included `Jenkinsfile` demonstrates stages: Checkout, Install Dependencies, Run Tests, Build Docker Image, Run Container & Health Check. The pipeline tags images with the Jenkins `${BUILD_NUMBER}`.

## Further Reading
See `docs/DEVOPS.md` for interview-ready explanations of CI/CD concepts used in this project.
