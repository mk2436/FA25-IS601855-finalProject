## FastAPI Calculator – Final Project

A production-ready, containerized FastAPI service that exposes a secure calculator API with persisted calculation history, advanced operations, and full end-to-end test coverage. The project demonstrates modern Python backend engineering practices, including REST API design, SQL database integration, automated testing, Dockerization, and CI/CD with GitHub Actions.

---

## Overview

This application provides a web-based calculator backed by a FastAPI REST API and a relational database managed via SQLAlchemy. Users can perform basic and advanced operations, inspect their calculation history, and interact with the API via an SPA-style front-end and auto-generated OpenAPI docs. The codebase is structured to emphasize testability, observability, and security best practices.

---

## Key Features

- **FastAPI REST API**
  - High-performance HTTP API for performing calculations.
  - Auto-generated interactive API docs via Swagger UI and ReDoc.
- **Pydantic-based validation**
  - Strongly-typed request and response models using Pydantic schemas.
  - Centralized validation, parsing, and serialization for all API payloads.
- **SQL-backed persistence**
  - SQLAlchemy ORM models for storing users and calculation records.
  - Clear separation between API layer, schemas, and persistence layer.
- **Advanced calculation support**
  - Core arithmetic operations (addition, subtraction, multiplication, division).
  - Extended operators (e.g., exponentiation, modulus, and other advanced functions as implemented).
  - Input validation and robust error handling for malformed or invalid requests.
- **History & reporting**
  - Endpoints to query prior calculations and summary metrics (e.g., counts, aggregates).
  - Useful for analytics, audits, and user-facing history views.
- **Authentication & security**
  - Credential-based login with hashed passwords.
  - Token-based authentication for protected operations (e.g., viewing personal history).
  - Secure password handling using industry-standard hashing algorithms.
- **Modern front-end integration**
  - UI screens/forms to submit calculations, visualize results, and inspect prior history.
  - Client-side validation for common input issues.
- **Production-friendly packaging**
  - Containerized via Docker.
  - CI pipeline that runs tests, builds the image, and pushes to Docker Hub on success.

---

## Tech Stack

- **Language**: Python 3.x  
- **Web Framework**: FastAPI  
- **ORM / DB Layer**: SQLAlchemy (+ Alembic for migrations, if configured)  
- **Database**: SQLite / PostgreSQL (depending on environment configuration)  
- **Validation / Serialization**: Pydantic models and schemas  
- **Testing**: `pytest`, HTTPX/TestClient for integration tests, Playwright for E2E tests  
- **Containerization**: Docker  
- **CI/CD**: GitHub Actions

---

## Project Structure (conceptual)

Your exact layout may vary slightly; this is the conceptual structure:

- **`app/`**
  - `main.py` – FastAPI application entry point, route wiring, middleware.
  - `schemas/` – Pydantic models for requests/responses (e.g., calculation, history, auth).
  - `models/` – SQLAlchemy models representing database tables.
  - `api/` – Route definitions (calculator endpoints, history endpoints, auth, etc.).
  - `core/` – Configuration, settings, security utilities, and shared dependencies.
  - `services/` or `crud/` – Business logic and database access layer.
- **`tests/`**
  - `unit/` – Pure logic tests (operations, utilities, services).
  - `integration/` – API + database integration tests.
  - `e2e/` – Playwright tests covering full browser flows.
- **`Dockerfile`** – Image definition for building and running the service.
- **`.github/workflows/`** – GitHub Actions CI configuration.
- **`alembic/` (optional)** – Migration environment & versions.
- **`requirements.txt` / `pyproject.toml`** – Python dependencies and tooling.

---

## API Documentation (Summary)

This section gives a high-level overview of the main REST API endpoints exposed by the application. For full interactive documentation, use the built-in Swagger UI at `/docs` or ReDoc at `/redoc` when the app is running.

- **Health**
  - **`GET /health`**  
    - **Description**: Simple health check to verify the API is up.  
    - **Auth**: Not required.  
    - **Response**: `{"status": "ok"}`.

- **Authentication**
  - **`POST /auth/register`**  
    - **Description**: Register a new user account.  
    - **Body**: `UserCreate` (includes username, email, password, confirm_password, and optional profile fields).  
    - **Response**: `UserResponse`.  
    - **Auth**: Not required.
  - **`POST /auth/login`**  
    - **Description**: JSON-based login endpoint. Returns access token, refresh token, and user profile data.  
    - **Body**: `UserLogin` (username and password).  
    - **Response**: `TokenResponse`.  
    - **Auth**: Not required.
  - **`POST /auth/token`**  
    - **Description**: OAuth2-style form login (used by Swagger UI).  
    - **Body**: `application/x-www-form-urlencoded` (username, password).  
    - **Response**: Basic bearer token payload with `access_token` and `token_type`.  
    - **Auth**: Not required.

- **Calculation Management (BREAD)**
  - **`POST /calculations`**  
    - **Description**: Create a new calculation for the authenticated user; result is computed server-side.  
    - **Body**: `CalculationBase` (type of operation and inputs).  
    - **Response**: `CalculationResponse`.  
    - **Auth**: Required (bearer token).
  - **`GET /calculations`**  
    - **Description**: List all calculations belonging to the current user.  
    - **Response**: `List[CalculationResponse]`.  
    - **Auth**: Required.
  - **`GET /calculations/stats`**  
    - **Description**: Returns aggregated statistics for the current user’s calculations (total count, average operands, most used operation, average result, date range, etc.).  
    - **Response**: `CalculationStats`.  
    - **Auth**: Required.
  - **`GET /calculations/{calc_id}`**  
    - **Description**: Retrieve a single calculation by its UUID if it belongs to the current user.  
    - **Path params**: `calc_id` (UUID as string).  
    - **Response**: `CalculationResponse`.  
    - **Auth**: Required.
  - **`PUT /calculations/{calc_id}`**  
    - **Description**: Update the inputs (and recompute the result) for a specific calculation.  
    - **Body**: `CalculationUpdate` (e.g., new inputs).  
    - **Response**: `CalculationResponse`.  
    - **Auth**: Required.
  - **`DELETE /calculations/{calc_id}`**  
    - **Description**: Delete a calculation by its UUID if owned by the current user.  
    - **Response**: No content (`204`).  
    - **Auth**: Required.

- **User Profile & Account**
  - **`GET /users/me`**  
    - **Description**: Fetch the current authenticated user’s profile information from the database.  
    - **Response**: `UserResponse`.  
    - **Auth**: Required.
  - **`PUT /users/me`**  
    - **Description**: Update profile fields (e.g., username, email, names) for the current user, with uniqueness validation.  
    - **Body**: `UserUpdate`.  
    - **Response**: `UserResponse`.  
    - **Auth**: Required.
  - **`POST /users/profile-picture`**  
    - **Description**: Upload or replace the user’s profile picture (JPEG, PNG, GIF, WebP up to 5MB). Old picture is removed on update.  
    - **Body**: Multipart/form-data with `file: UploadFile`.  
    - **Response**: `UserResponse` including `profile_picture` path.  
    - **Auth**: Required.
  - **`DELETE /users/profile-picture`**  
    - **Description**: Delete the current user’s profile picture file and clear the profile field.  
    - **Response**: `UserResponse`.  
    - **Auth**: Required.
  - **`PUT /users/password`**  
    - **Description**: Change the authenticated user’s password, verifying the current password first.  
    - **Body**: `PasswordUpdate` (current_password, new_password, confirm_new_password as defined).  
    - **Response**: JSON message indicating success and that re-login is required.  
    - **Auth**: Required.

- **Web (HTML) Views**
  - **`GET /`**  
    - **Description**: Landing page with welcome content and links to register/login.  
    - **Response**: HTML (`index.html`).  
    - **Auth**: Not required.
  - **`GET /login`**  
    - **Description**: Login page with a form for username/password that posts to the auth endpoints.  
    - **Response**: HTML (`login.html`).  
    - **Auth**: Not required.
  - **`GET /register`**  
    - **Description**: Registration page with a form to create a new user account.  
    - **Response**: HTML (`register.html`).  
    - **Auth**: Not required.
  - **`GET /dashboard`**  
    - **Description**: Authenticated dashboard showing the user’s calculations and a form to create new ones; frontend JS calls the `/calculations` APIs.  
    - **Response**: HTML (`dashboard.html`).  
    - **Auth**: Typically requires a valid session/token (handled client-side).
  - **`GET /dashboard/view/{calc_id}`**  
    - **Description**: Page to view details of a single calculation; uses the `calc_id` to call the `/calculations/{calc_id}` API from the browser.  
    - **Path params**: `calc_id` (UUID as string).  
    - **Response**: HTML (`view_calculation.html`).  
    - **Auth**: Typically requires a valid session/token.
  - **`GET /dashboard/edit/{calc_id}`**  
    - **Description**: Page to edit an existing calculation; uses the `calc_id` to call the calculations APIs for load/update.  
    - **Path params**: `calc_id` (UUID as string).  
    - **Response**: HTML (`edit_calculation.html`).  
    - **Auth**: Typically requires a valid session/token.
  - **`GET /profile`**  
    - **Description**: Profile settings page where the user can manage profile information and profile picture, backed by the `/users/*` APIs.  
    - **Response**: HTML (`profile.html`).  
    - **Auth**: Typically requires a valid session/token.

---

## Getting Started

### Prerequisites

- Python 3.10+  
- `pip` or a Python dependency manager (`pipenv`, `poetry`, etc.)  
- Docker (for containerized runs)  
- Node.js (optional, for Playwright CLI and any front-end tooling)

### 1. Clone the Repository

```bash
git clone https://github.com/mk2436/FA25-IS601855-finalProject.git
cd FA25-IS601855-finalProject
```

### 2. Create and Activate a Virtual Environment

```bash
python -m venv .venv

# Windows PowerShell
. .venv\Scripts\Activate.ps1

# Windows cmd
.venv\Scripts\activate.bat
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

If you use `poetry` or a different tool, follow that workflow instead.

### 4. Configure Environment

Create a `.env` file or export environment variables. Typical configuration values include:

- **`DATABASE_URL`** – Connection string for the application database.  
- **`SECRET_KEY`** – Secret used for signing tokens.  
- **`ACCESS_TOKEN_EXPIRE_MINUTES`** – Access token lifetime.  
- **`APP_ENV`** – Environment flag such as `local`, `dev`, or `prod`.

On PowerShell, for example:

```powershell
$env:DATABASE_URL = "sqlite:///./app.db"
$env:SECRET_KEY = "change-me"
$env:ACCESS_TOKEN_EXPIRE_MINUTES = "30"
```

---

## Running the Application Locally

With dependencies installed and the environment configured:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- **Base URL**: `http://localhost:8000`  
- **Swagger UI**: `http://localhost:8000/docs`  
- **ReDoc**: `http://localhost:8000/redoc`

---

## Database & Migrations

If Alembic is set up for schema migrations, typical commands are:

```bash
# Generate a new migration after model changes
alembic revision --autogenerate -m "describe change"

# Apply all migrations
alembic upgrade head

# Roll back one migration
alembic downgrade -1
```

Ensure `alembic.ini` and `env.py` are wired to your `DATABASE_URL` and SQLAlchemy models.

---

## Testing

The codebase is built with comprehensive automated testing:

- **Unit tests** – Validate core computation logic and utility functions.  
- **Integration tests** – Exercise FastAPI routes together with the database.  
- **End-to-end (E2E) tests** – Use Playwright to validate user flows in the browser.

For any tests that hit the database (integration and E2E), ensure the database service is up first. The recommended workflow is:

```bash
# Start the database and any dependent services
docker compose up -d
```

Once the containers are healthy, run the tests from the project root:

```bash
# Run the full Python test suite
pytest

# Run unit tests only
pytest tests/unit

# Run integration tests only
pytest tests/integration
```

For Playwright-based E2E tests (ensure the app is running first):

```bash
playwright install  # first time only
pytest tests/e2e
```

## Feature Test Coverage

The User Profile & Password Change feature is comprehensively tested across all layers:

- **Unit Tests** (`tests/unit/test_calculator.py`)
  - Core calculator operations (addition, subtraction, multiplication, division)
  - Input validation and error handling for mathematical operations

- **Integration Tests** (`tests/integration/test_user_auth.py`, `tests/integration/test_user.py`)
  - **Password Management:**
    - Password hashing and verification at model level (`User.hash_password`, `User.verify_password`)
    - Password update logic with hash verification
    - PasswordUpdate schema validation (Pydantic):
      - Password mismatch detection
      - Minimum length enforcement (8 characters)
      - Complexity requirements (uppercase, lowercase, digit, special character)
      - Prevention of reusing current password
    - Password update preserves other user fields
    - Updated timestamp tracking on password changes
  - **Profile Management:**
    - Profile picture field operations (assignment, clearing, replacement)
    - Profile picture update preserves other user fields
    - Updated timestamp tracking on profile changes
  - **User Model Operations:**
    - User registration with password validation
    - User authentication and token generation
    - Uniqueness constraints (email, username)
    - Database transaction handling and rollbacks

- **E2E Tests** (`tests/e2e/test_fastapi_calculator.py`)
  - **Password Update API (`PUT /users/password`):**
    - Successful password update with verification
    - Re-login with new password after update
    - Rejection of incorrect current password
    - Validation errors (password mismatch, weak passwords, same as current)
    - Unauthorized access handling (missing/invalid tokens)
  - **Profile Picture API:**
    - `POST /users/profile-picture` – Successful upload with supported formats (JPEG, PNG, GIF, WebP)
    - `POST /users/profile-picture` – File validation (type, size limits, filename requirements)
    - `POST /users/profile-picture` – Replacing existing profile picture
    - `DELETE /users/profile-picture` – Successful deletion
    - `DELETE /users/profile-picture` – Handling deletion when no picture exists
    - `GET /users/me` – Verifying profile picture updates in user profile
    - Unauthorized access handling for upload/delete operations
  - **Complete User Flow:**
    - User registration → login → profile update → password change → re-login with new password


Typical flows covered in E2E tests include:

- **Authentication** – Logging in with valid/invalid credentials.  
- **Calculations** – Triggering operations through the UI and verifying the results.  
- **History & reporting** – Viewing previous calculations and any summary/metric views.  
- **Negative paths** – Submitting invalid operands or accessing protected pages without authorization.

---

## Docker

### Build the Image

From the project root (where the `Dockerfile` resides):

```bash
docker build -t <your-dockerhub-username>/fastapi-calculator:latest .
```

### Docker Compose

The repository includes a `docker-compose.yml` that orchestrates the full environment (API + database) with sensible defaults. Typical usage:

```bash
# Start services in the background
docker compose up -d

# View logs (optional)
docker compose logs -f

# Tear everything down when finished
docker compose down
```

This is the same composition used by the test and development workflows to ensure a consistent, reproducible environment.

### Run the Container

```bash
docker run --rm -p 8000:8000 ^
  -e DATABASE_URL=sqlite:///./app.db ^
  -e SECRET_KEY=change-me ^
  -e ACCESS_TOKEN_EXPIRE_MINUTES=30 ^
  <your-dockerhub-username>/fastapi-calculator:latest
```

The API will be available at `http://localhost:8000`.

### Push to Docker Hub

```bash
docker login
docker push <your-dockerhub-username>/fastapi-calculator:latest
```

This image tag can then be consumed by any container orchestration platform or deployment target.

---

## Continuous Integration (GitHub Actions)

GitHub Actions is configured via `.github/workflows/DockerBuildandPush.yml` to provide a full CI/CD pipeline for this project.

- **Triggers**
  - Workflow name: **`Docker CI/CD`**.
  - Runs automatically on:
    - `push` events to the `main` branch.
    - `pull_request` events targeting `main`.
  - Can also be run manually using the `workflow_dispatch` event.

- **`test` job**
  - **Runner & database service**
    - Executes on `ubuntu-latest`.
    - Starts a `postgres:latest` service container with:
      - `POSTGRES_USER=user`
      - `POSTGRES_PASSWORD=password`
      - `POSTGRES_DB=mytestdb`
    - Exposes port `5432` and configures a health check using `pg_isready` with interval, timeout, and retry settings.
  - **Environment setup**
    - Checks out the code with `actions/checkout@v3`.
    - Sets up Python 3.10 using `actions/setup-python@v4`.
    - Caches `pip` dependencies via `actions/cache@v3`, keyed on `requirements.txt`.
  - **Dependency installation**
    - Creates a virtual environment (`python -m venv venv`) and activates it (`source venv/bin/activate`).
    - Upgrades `pip` and installs dependencies from `requirements.txt`.
    - Installs Playwright browsers with `playwright install`.
    - Uses `DATABASE_URL=postgresql://user:password@localhost:5432/mytestdb` to point the app/tests at the Postgres service.
  - **Test execution**
    - Re-activates the virtual environment and runs:
      - Unit tests: `pytest tests/unit/ --cov=src --junitxml=test-results/junit.xml`
      - Integration tests: `pytest tests/integration/`
      - E2E tests: `pytest tests/e2e/`

- **`security` job**
  - Declared with `needs: test`, so it only runs if the `test` job succeeds.
  - Uses `ubuntu-latest` and checks out the repository with `actions/checkout@v4`.
  - Builds a Docker image tagged `app:test` from the current repository (`docker build -t app:test .`).
  - Scans that image with Trivy using `aquasecurity/trivy-action@master`, configured to:
    - Output results in table format.
    - Fail the job on `CRITICAL` or `HIGH` vulnerabilities (`exit-code: '1'`, `severity: 'CRITICAL,HIGH'`).
    - Ignore unfixed vulnerabilities (`ignore-unfixed: true`).

- **`deploy` job**
  - Declared with `needs: security` and guarded by:
    - `if: github.ref == 'refs/heads/main'` so it only runs on the `main` branch after passing tests and security scan.
  - Runs on `ubuntu-latest` and uses the `production` environment.
  - Steps:
    - Checks out code (`actions/checkout@v4`).
    - Sets up Docker Buildx with `docker/setup-buildx-action@v3`.
    - Logs in to Docker Hub using `docker/login-action@v3` and the repository secrets `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN`.
    - Builds and pushes a multi-architecture image with `docker/build-push-action@v5`, configured to:
      - `push: true`.
      - Tag images as:
        - `mihirkadam1912/is601-finalproject:latest`
        - `mihirkadam1912/is601-finalproject:${{ github.sha }}`
      - Target `linux/amd64` and `linux/arm64` platforms.
      - Use a registry-based cache (`cache-from` pointing to `mihirkadam1912/is601-finalproject:cache` and `cache-to` with inline, max mode).

Together, these jobs implement a complete CI/CD workflow: tests run against a real Postgres instance, the resulting container image is scanned for vulnerabilities, and on clean builds from the `main` branch, a versioned image is published to Docker Hub at `mihirkadam1912/is601-finalproject` ([repo link](https://hub.docker.com/r/mihirkadam1912/is601-finalproject)). 

---

## Security & Best Practices

The application is structured to follow secure development practices:

- **Password handling**
  - Passwords are never stored in plain text.
  - Hashing is implemented using reliable, battle-tested algorithms.
- **Authentication and authorization**
  - Protected routes rely on dependency-injected token validation.
  - Tokens are time-bound and signed using a server-side secret.
- **Input validation**
  - Pydantic schemas enforce strict validation rules for request payloads.
  - Clear error messages and appropriate HTTP status codes are returned for invalid inputs.
- **Configuration hygiene**
  - Sensitive values are read from environment variables or a secure configuration mechanism.
  - No secrets are hard-coded in the source code.
 - **CI-driven vulnerability assessment**
   - The GitHub Actions pipeline builds the Docker image and runs a Trivy container image scan as a dedicated `security` job.
   - Builds are blocked when critical or high-severity vulnerabilities are detected, ensuring only vetted images progress to deployment.

---

## Quick Reference

- **Start API locally**  
  `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`

- **Run full Python tests**  
  `pytest`

- **Run E2E tests (after starting the app)**  
  `playwright install` (first run) then `pytest tests/e2e`

- **Build Docker image**  
  `docker build -t <your-dockerhub-username>/fastapi-calculator:latest .`

- **Run Docker container**  
  `docker run --rm -p 8000:8000 <your-dockerhub-username>/fastapi-calculator:latest`

---

## Links

- **GitHub repository**: [`https://github.com/mk2436/FA25-IS601855-finalProject`](https://github.com/mk2436/FA25-IS601855-finalProject)  
- **Docker Hub image**: [`https://hub.docker.com/r/mihirkadam1912/is601-finalproject`](https://hub.docker.com/r/mihirkadam1912/is601-finalproject)  
