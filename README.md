# ACEest Fitness & Gym — Flask CI/CD Project

A Flask web application for fitness-club management (members, training
programs, calorie/BMI calculation, weekly adherence tracking), delivered
through an automated DevOps pipeline: **Git/GitHub → Pytest → Docker →
GitHub Actions + Jenkins**.

The application logic is modularized from the original ACEest Tkinter
desktop prototypes (v1.0 → v3.2.4) into a Flask REST API with a small web UI.

## Project Structure

```
.
├── app.py                    # Flask application
├── requirements.txt          # Runtime dependencies
├── requirements-dev.txt      # Test + lint dependencies (pytest, flake8)
├── test_app.py               # Pytest suite (27 tests)
├── Dockerfile                # Multi-stage: runtime / test targets
├── Jenkinsfile               # Jenkins BUILD pipeline
├── .github/workflows/main.yml# GitHub Actions pipeline
├── .flake8  .dockerignore  .gitignore
├── templates/index.html      # Web dashboard
└── static/style.css
```

## API Endpoints

| Method | Endpoint                       | Description                                   |
|--------|--------------------------------|-----------------------------------------------|
| GET    | `/`                            | Web dashboard                                 |
| GET    | `/health`                      | Health check                                  |
| GET    | `/api/programs`                | List training programs                        |
| GET    | `/api/members`                 | List members                                  |
| POST   | `/api/members`                 | Register member (`name`, `age`, `weight`, `program`, optional `height` cm) |
| GET    | `/api/members/<name>`          | Get a member                                  |
| DELETE | `/api/members/<name>`          | Delete a member                               |
| POST   | `/api/members/<name>/progress` | Log weekly adherence (`adherence` 0–100)      |
| POST   | `/api/bmi`                     | BMI calculator (`weight` kg, `height` cm)     |

Calories = weight (kg) × program factor (Fat Loss 22, Muscle Gain 35, Beginner 26).

## Local Setup & Execution

Requires Python 3.11+.

```bash
git clone https://github.com/krittb/aceest-fitness-flask.git
cd aceest-fitness-flask

python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

python app.py                        # http://localhost:5000
```

### Run with Docker

```bash
docker build -t aceest-fitness .             # builds the lean runtime image
docker run -p 5000:5000 aceest-fitness
curl http://localhost:5000/health
```

## Running Tests Manually

**Locally**

```bash
pip install -r requirements-dev.txt
pytest -v                                    # run suite
pytest -v --cov=app --cov-report=term-missing   # with coverage
flake8 .                                     # lint
```

**Inside Docker (same as CI)**

```bash
docker build --target test -t aceest-fitness:test .
docker run --rm aceest-fitness:test
```

Expected: 27 passed, ~92% coverage. The suite covers health/UI, program
listing, member create/read/delete, input validation (parametrized),
adherence logging, and the BMI calculator.

## Docker Design

- **Multi-stage build**: `builder` installs runtime deps; `test` adds
  pytest/flake8 and the tests; `runtime` (default) contains only the app and
  runtime deps, so test tooling never ships in production.
- `python:3.12-slim` base, `--no-cache-dir`, `.dockerignore` for a small context.
- Runs as a **non-root user** (`appuser`, no login shell), served by **gunicorn**.
- Built-in `HEALTHCHECK` on `/health`.

## CI/CD Overview

### GitHub Actions — `.github/workflows/main.yml`
Triggers on **every push and pull request**. Three dependent jobs:

1. **Build & Lint** — installs deps, compile-checks sources
   (`compileall`), runs `flake8`.
2. **Docker Image Assembly** — builds the `runtime` image with layer
   caching and smoke-tests it (`/health`).
3. **Automated Testing** — builds the `test` target and runs Pytest
   **inside the container**.

A failure in any job stops the pipeline (`needs:` chain).

### Jenkins — `Jenkinsfile`
A Pipeline job ("Pipeline script from SCM") pointing at this GitHub repo,
triggered by a GitHub webhook (`/github-webhook/`) with SCM polling as fallback.

1. **Clean Workspace & Checkout** — `deleteDir()` then `checkout scm`
   for a clean build of the latest code.
2. **Build & Lint** — fresh virtualenv, install deps, compile check, flake8.
3. **Docker Image Assembly** — builds runtime and test images.
4. **Automated Testing (in Docker)** — runs Pytest in the container and
   publishes JUnit results.
5. **Smoke Test** — starts the image and curls `/health`.

Jenkins agent requirements: Git, Python 3 + `venv`, Docker (Jenkins user in
the `docker` group), `curl`; plugins: Pipeline, Git, JUnit.

### How they fit together
Both pipelines enforce the same gate (build/lint → image → containerized
tests) from the same `Dockerfile` and requirements files. GitHub Actions is
the fast per-push/PR check; Jenkins is the secondary validation in a
controlled, clean build environment.

## Git Workflow

- `main` is always releasable; work happens on short-lived branches and
  merges via Pull Request (which triggers the Actions pipeline):
  - `feature/<name>` — new functionality
  - `bugfix/<name>` — fixes
  - `infra/<name>` — Docker / CI / Jenkins changes
- Commit messages are imperative and descriptive, e.g.
  `Add BMI endpoint with input validation`, `Fix flake8 E127 in add_member`.

## Running Jenkins (Docker)

Jenkins runs in a container with Python, Git and the Docker CLI, sharing the
host Docker daemon (`jenkins/Dockerfile`, `jenkins/docker-compose.yml`).

```bash
docker compose -f jenkins/docker-compose.yml up -d --build
# open http://localhost:8080  (setup wizard disabled for this demo setup)
```

Create a **Pipeline** job -> *Pipeline script from SCM* -> Git ->
`https://github.com/krittb/aceest-fitness-flask.git`, branch `*/main`,
Script Path `Jenkinsfile`, then **Build Now**. The pipeline wipes the
workspace, pulls the latest code, lints, builds the Docker images, runs Pytest
inside the container and smoke-tests the runtime image.
