.PHONY: dev backend frontend lint test format typecheck

backend:
cd backend && uvicorn main:app --reload

frontend:
cd frontend && npm run dev

dev:
python -m asyncio run scripts.smoke

lint:
ruff check backend

format:
ruff format backend

test:
cd backend && pytest -q

typecheck:
cd backend && mypy crippel
