# backend/app/api

REST API layer — routers, controllers, and middleware for the FastAPI application.

## Structure

- `routers/` — Route definitions grouped by domain (profiles, jobs, resumes, applications)
- `dependencies.py` — Shared dependency injection (auth, database sessions)
- `middleware.py` — Custom middleware (CORS, request logging, error handling)
