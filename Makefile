.PHONY: help setup backend frontend lint format test dev clean install-pre-commit

help:
	@echo "AI Career Agent - Development Commands"
	@echo "======================================"
	@echo "make setup              - Full project setup (backend + frontend)"
	@echo "make backend            - Install backend dependencies"
	@echo "make frontend           - Install frontend dependencies"
	@echo "make dev                - Run both backend and frontend in development mode"
	@echo "make lint               - Run all linters (ruff, eslint)"
	@echo "make format             - Format all code (black, ruff, prettier)"
	@echo "make test               - Run all tests"
	@echo "make clean              - Remove temporary files and caches"
	@echo "make install-pre-commit - Install pre-commit hooks"

setup: backend frontend install-pre-commit

backend:
	python -m venv .venv
	.venv\Scripts\pip install -r backend\requirements.txt
	playwright install chromium

frontend:
	cd frontend && npm install

dev:
	@echo "Starting backend on http://localhost:8000 ..."
	@echo "Starting frontend on http://localhost:5173 ..."
	start cmd /c "cd backend && ..\.venv\Scripts\uvicorn main:app --reload"
	start cmd /c "cd frontend && npm run dev"

lint:
	.venv\Scripts\ruff check backend\
	cd frontend && npm run lint

format:
	.venv\Scripts\black backend\
	.venv\Scripts\ruff format backend\
	cd frontend && npm run format

test:
	.venv\Scripts\pytest backend\tests\
	@echo "Frontend tests: cd frontend && npm run test"

clean:
	rm -rf .venv
	rm -rf frontend/node_modules
	rm -rf **/__pycache__
	rm -rf .pytest_cache
	rm -rf frontend/dist

install-pre-commit:
	.venv\Scripts\pip install pre-commit
	.venv\Scripts\pre-commit install

install:
	python -m venv .venv
	.venv\Scripts\pip install -r backend\requirements.txt
	cd frontend && npm install
	.venv\Scripts\pre-commit install
