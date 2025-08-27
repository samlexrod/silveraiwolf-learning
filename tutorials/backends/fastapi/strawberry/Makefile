.PHONY: help install dev test test-pytest init-db start-postgres stop-postgres logs clean add-dep add-dev-dep

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install Python dependencies
	uv sync

install-dev: ## Install development dependencies
	uv sync --extra dev

dev: ## Start the development server
	uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test: ## Run the test suite
	uv run python tests/test_app.py

test-pytest: ## Run tests with pytest
	uv run pytest tests/ -v

init-db: ## Initialize the database
	uv run python init_db.py

start-postgres: ## Start PostgreSQL with Docker
	docker compose up -d postgres

stop-postgres: ## Stop PostgreSQL
	docker compose down

logs: ## Show PostgreSQL logs
	docker compose logs -f postgres

clean: ## Clean up containers and cache files
	docker compose down -v
	rm -rf __pycache__ .pytest_cache .coverage

setup: ## Complete project setup (install, start postgres, init db)
	$(MAKE) install
	$(MAKE) start-postgres
	sleep 3
	$(MAKE) init-db

setup-dev: ## Complete development setup with dev dependencies
	$(MAKE) install-dev
	$(MAKE) start-postgres
	sleep 3
	$(MAKE) init-db

full-test: ## Run complete test suite with database
	$(MAKE) start-postgres
	sleep 3
	$(MAKE) test

add-dep: ## Add a new dependency (usage: make add-dep PKG=package-name)
	uv add $(PKG)

add-dev-dep: ## Add a new development dependency (usage: make add-dev-dep PKG=package-name)
	uv add --dev $(PKG)

# Docker commands
docker-build: ## Build the Docker image
	docker build -t strawberry-graphql-api .

docker-run: ## Run the application in Docker (requires postgres)
	docker run -p 8000:8000 --env-file .env strawberry-graphql-api

docker-compose-dev: ## Start development environment with Docker Compose
	docker compose -f docker-compose.dev.yml up -d

docker-compose-dev-down: ## Stop development environment
	docker compose -f docker-compose.dev.yml down

docker-compose-dev-logs: ## View development logs
	docker compose -f docker-compose.dev.yml logs -f

docker-compose-dev-clean: ## Clean up development environment and volumes
	docker compose -f docker-compose.dev.yml down -v

docker-test: ## Test the Docker container
	docker run --rm -p 8000:8000 strawberry-graphql-api &
	sleep 10
	curl -f http://localhost:8000/ || exit 1
	docker stop $$(docker ps -q --filter ancestor=strawberry-graphql-api)
