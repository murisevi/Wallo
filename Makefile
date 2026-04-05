.PHONY: up down logs backend-shell db-shell migrate test-backend test-frontend lint

up:
	docker compose up -d

down:
	docker compose down -v

logs:
	docker compose logs -f backend

backend-shell:
	docker compose exec backend bash

db-shell:
	docker compose exec db psql -U wallo -d wallo

migrate:
	docker compose exec backend alembic upgrade head

test-backend:
	docker compose exec backend pytest tests/ -v --cov=app

test-frontend:
	docker compose exec frontend npm run test

lint:
	docker compose exec backend ruff check app/ --fix && ruff format app/
	docker compose exec frontend npm run lint
