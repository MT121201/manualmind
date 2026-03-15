.PHONY: up down build logs-api logs-worker restart

# Boot the whole system in the background
up:
	docker compose up -d

# Stop and remove all containers
down:
	docker compose down

# Rebuild the images and boot (use this when you install new pip packages)
build:
	docker compose up -d --build

# Watch the FastAPI logs
logs-api:
	docker compose logs -f api

# Watch the Celery Worker logs
logs-worker:
	docker compose logs -f worker

# Quick restart for all services
restart:
	docker compose restart