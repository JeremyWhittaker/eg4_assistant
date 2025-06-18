# Solar Assistant Docker Makefile

.PHONY: help build up down restart logs shell backup restore clean

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

build: ## Build Docker images
	docker-compose build

up: ## Start all services
	docker-compose up -d
	@echo "Solar Assistant is running at http://localhost"

down: ## Stop all services
	docker-compose down

restart: ## Restart all services
	docker-compose restart

logs: ## View logs (use logs service=<name> for specific service)
	docker-compose logs -f $(service)

shell: ## Access main container shell
	docker exec -it solar-assistant /bin/bash

backup: ## Backup database
	@echo "Creating backup..."
	docker exec solar-assistant python -c "from data_collector import DataCollector; DataCollector().backup_database()"
	@echo "Backup completed"

restore: ## Restore database from backup (use restore file=<path>)
	@if [ -z "$(file)" ]; then echo "Usage: make restore file=<backup_file>"; exit 1; fi
	docker cp $(file) solar-assistant:/data/db/solar_assistant.db
	docker restart solar-assistant
	@echo "Database restored from $(file)"

clean: ## Remove all data and volumes (WARNING: This deletes all data!)
	@echo "WARNING: This will delete all data!"
	@read -p "Are you sure? [y/N] " confirm && [ "$$confirm" = "y" ] || exit 1
	docker-compose down -v
	rm -rf data/ mosquitto/ influxdb/ redis/
	@echo "All data removed"

status: ## Show service status
	docker-compose ps

export: ## Export data (use export format=<csv|json|excel>)
	@format=$${format:-csv}; \
	docker exec solar-assistant python -c "import requests; print(requests.get('http://localhost:5000/api/export/$$format').text)"

test: ## Run tests
	docker exec solar-assistant pytest tests/

update: ## Pull latest images and restart
	docker-compose pull
	docker-compose up -d

config: ## Edit configuration
	$${EDITOR:-nano} config/config.yaml

install: ## Initial setup
	@if [ ! -f .env ]; then cp .env.example .env && echo "Created .env file"; fi
	@if [ ! -f ../config/config.yaml ]; then mkdir -p ../config && cp config.yaml.default ../config/config.yaml && echo "Created default config"; fi
	@echo "Setup complete. Edit .env and config/config.yaml then run 'make up'"