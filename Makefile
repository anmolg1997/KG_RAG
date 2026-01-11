# =============================================================================
# KG-RAG Makefile
# =============================================================================
# Common commands for development and deployment
#
# Usage:
#   make help        - Show all available commands
#   make setup       - Initial project setup
#   make dev         - Start development servers
#   make test        - Run tests

.PHONY: help setup backend-setup frontend-setup dev backend frontend neo4j \
        docker-up docker-down clean test lint format health \
        strategy strategy-presets strategy-load strategy-reset

# Default target
.DEFAULT_GOAL := help

# Colors for terminal output
BLUE := \033[34m
GREEN := \033[32m
YELLOW := \033[33m
RED := \033[31m
NC := \033[0m  # No Color

# =============================================================================
# HELP
# =============================================================================

help: ## Show this help message
	@echo ""
	@echo "$(BLUE)╔═══════════════════════════════════════════════════════════════════╗$(NC)"
	@echo "$(BLUE)║               KG-RAG Development Commands                         ║$(NC)"
	@echo "$(BLUE)╚═══════════════════════════════════════════════════════════════════╝$(NC)"
	@echo ""
	@echo "$(YELLOW)🚀 QUICK START$(NC)"
	@echo "  $(GREEN)make setup$(NC)           Complete first-time project setup"
	@echo "  $(GREEN)make dev$(NC)             Start all development servers"
	@echo "  $(GREEN)make health$(NC)          Check if all services are running"
	@echo ""
	@echo "$(YELLOW)📦 SETUP$(NC)"
	@echo "  $(GREEN)make setup$(NC)           Full setup (Neo4j + backend + frontend)"
	@echo "  $(GREEN)make backend-setup$(NC)   Setup Python backend with uv"
	@echo "  $(GREEN)make frontend-setup$(NC)  Setup Node.js frontend with npm"
	@echo ""
	@echo "$(YELLOW)🔧 DEVELOPMENT$(NC)"
	@echo "  $(GREEN)make dev$(NC)             Start backend + frontend together"
	@echo "  $(GREEN)make backend$(NC)         Start only backend server (port 8000)"
	@echo "  $(GREEN)make frontend$(NC)        Start only frontend server (port 5173)"
	@echo ""
	@echo "$(YELLOW)🗄️  NEO4J DATABASE$(NC)"
	@echo "  $(GREEN)make neo4j$(NC)           Start Neo4j container"
	@echo "  $(GREEN)make neo4j-stop$(NC)      Stop Neo4j container"
	@echo "  $(GREEN)make neo4j-logs$(NC)      View Neo4j logs"
	@echo "  $(GREEN)make neo4j-shell$(NC)     Open Cypher shell"
	@echo ""
	@echo "$(YELLOW)🐳 DOCKER$(NC)"
	@echo "  $(GREEN)make docker-up$(NC)       Start all services via Docker Compose"
	@echo "  $(GREEN)make docker-down$(NC)     Stop all Docker services"
	@echo "  $(GREEN)make docker-logs$(NC)     View Docker Compose logs"
	@echo "  $(GREEN)make docker-build$(NC)    Rebuild Docker images"
	@echo ""
	@echo "$(YELLOW)💓 HEALTH & MONITORING$(NC)"
	@echo "  $(GREEN)make health$(NC)          Quick health check (all services)"
	@echo "  $(GREEN)make health-detail$(NC)   Detailed JSON health response"
	@echo "  $(GREEN)make db-stats$(NC)        Show database statistics"
	@echo ""
	@echo "$(YELLOW)🧪 TESTING & QUALITY$(NC)"
	@echo "  $(GREEN)make test$(NC)            Run backend tests"
	@echo "  $(GREEN)make test-cov$(NC)        Run tests with coverage report"
	@echo "  $(GREEN)make lint$(NC)            Run linters (ruff + eslint)"
	@echo "  $(GREEN)make format$(NC)          Auto-format code"
	@echo ""
	@echo "$(YELLOW)📋 SCHEMA MANAGEMENT$(NC)"
	@echo "  $(GREEN)make list-schemas$(NC)    List available schema files"
	@echo "  $(GREEN)make validate-schema$(NC) Validate all schema files"
	@echo ""
	@echo "$(YELLOW)⚙️  STRATEGY MANAGEMENT$(NC)"
	@echo "  $(GREEN)make strategy$(NC)        Show current extraction & retrieval strategies"
	@echo "  $(GREEN)make strategy-presets$(NC) List available strategy presets"
	@echo "  $(GREEN)make strategy-load$(NC)   Load preset (e.g., make strategy-load PRESET=comprehensive)"
	@echo "  $(GREEN)make strategy-reset$(NC)  Reset strategies to defaults"
	@echo ""
	@echo "$(YELLOW)🧹 UTILITIES$(NC)"
	@echo "  $(GREEN)make clean$(NC)           Remove build artifacts & caches"
	@echo "  $(GREEN)make shell$(NC)           Open Python shell with app context"
	@echo "  $(GREEN)make logs-backend$(NC)    Tail backend log files"
	@echo ""
	@echo "$(YELLOW)⚡ SHORTCUTS$(NC)"
	@echo "  $(GREEN)make install$(NC)         → make setup"
	@echo "  $(GREEN)make start$(NC)           → make dev"
	@echo "  $(GREEN)make stop$(NC)            → Stop all services"
	@echo "  $(GREEN)make restart$(NC)         → Stop then start"
	@echo ""
	@echo "$(BLUE)─────────────────────────────────────────────────────────────────────$(NC)"
	@echo "📖 For detailed docs: $(YELLOW)docs/MAKEFILE_GUIDE.md$(NC)"
	@echo ""

# =============================================================================
# SETUP
# =============================================================================

setup: neo4j backend-setup frontend-setup ## Complete project setup
	@echo "$(GREEN)✓ Setup complete!$(NC)"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Copy env.example to backend/.env and add your API keys"
	@echo "  2. Run 'make dev' to start development servers"

backend-setup: ## Setup backend with uv (Python 3.12)
	@echo "$(BLUE)Setting up backend with Python 3.12...$(NC)"
	cd backend && uv venv --python 3.12
	cd backend && uv pip install -r requirements.txt
	@echo "$(GREEN)✓ Backend setup complete$(NC)"

frontend-setup: ## Setup frontend with npm
	@echo "$(BLUE)Setting up frontend...$(NC)"
	cd frontend && npm install
	@echo "$(GREEN)✓ Frontend setup complete$(NC)"

# =============================================================================
# DEVELOPMENT
# =============================================================================

dev: ## Start all development servers (backend + frontend)
	@echo "$(BLUE)Starting development servers...$(NC)"
	@echo "Backend:  http://localhost:8000"
	@echo "Frontend: http://localhost:5173"
	@echo "Neo4j:    http://localhost:7474"
	@echo ""
	@make -j2 backend frontend

backend: ## Start backend server
	@echo "$(BLUE)Starting backend...$(NC)"
	cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend: ## Start frontend dev server
	@echo "$(BLUE)Starting frontend...$(NC)"
	cd frontend && npm run dev

# =============================================================================
# NEO4J
# =============================================================================

neo4j: ## Start Neo4j database (Docker)
	@echo "$(BLUE)Starting Neo4j...$(NC)"
	@if docker ps -a --format '{{.Names}}' | grep -q '^neo4j$$'; then \
		docker start neo4j; \
	else \
		docker run -d \
			--name neo4j \
			-p 7474:7474 -p 7687:7687 \
			-e NEO4J_AUTH=neo4j/password \
			neo4j:community; \
	fi
	@echo "$(GREEN)✓ Neo4j running at http://localhost:7474$(NC)"

neo4j-stop: ## Stop Neo4j database
	@echo "$(BLUE)Stopping Neo4j...$(NC)"
	docker stop neo4j || true
	@echo "$(GREEN)✓ Neo4j stopped$(NC)"

neo4j-logs: ## Show Neo4j logs
	docker logs -f neo4j

neo4j-shell: ## Open Neo4j Cypher shell
	docker exec -it neo4j cypher-shell -u neo4j -p password

# =============================================================================
# DOCKER COMPOSE
# =============================================================================

docker-up: ## Start all services with Docker Compose
	@echo "$(BLUE)Starting all services...$(NC)"
	docker-compose up -d
	@echo "$(GREEN)✓ All services running$(NC)"
	@echo "Frontend: http://localhost:5173"
	@echo "Backend:  http://localhost:8000"
	@echo "Neo4j:    http://localhost:7474"

docker-down: ## Stop all Docker Compose services
	@echo "$(BLUE)Stopping all services...$(NC)"
	docker-compose down
	@echo "$(GREEN)✓ All services stopped$(NC)"

docker-logs: ## Show Docker Compose logs
	docker-compose logs -f

docker-build: ## Rebuild Docker images
	docker-compose build --no-cache

# =============================================================================
# HEALTH CHECKS
# =============================================================================

health: ## Check health of all services
	@echo "$(BLUE)Checking service health...$(NC)"
	@echo ""
	@echo "Neo4j:"
	@curl -s http://localhost:7474 > /dev/null 2>&1 && \
		echo "  $(GREEN)✓ Running$(NC)" || echo "  $(RED)✗ Not running$(NC)"
	@echo ""
	@echo "Backend:"
	@curl -s http://localhost:8000/health > /dev/null 2>&1 && \
		echo "  $(GREEN)✓ Running$(NC)" || echo "  $(RED)✗ Not running$(NC)"
	@echo ""
	@echo "Frontend:"
	@curl -s http://localhost:5173 > /dev/null 2>&1 && \
		echo "  $(GREEN)✓ Running$(NC)" || echo "  $(RED)✗ Not running$(NC)"

health-detail: ## Show detailed health status
	@echo "$(BLUE)Detailed health check...$(NC)"
	@curl -s http://localhost:8000/health | python -m json.tool 2>/dev/null || \
		echo "$(RED)Backend not reachable$(NC)"

# =============================================================================
# TESTING & QUALITY
# =============================================================================

test: ## Run backend tests
	@echo "$(BLUE)Running tests...$(NC)"
	cd backend && source .venv/bin/activate && pytest -v

test-cov: ## Run tests with coverage
	cd backend && source .venv/bin/activate && pytest --cov=app --cov-report=html

lint: ## Run linters
	@echo "$(BLUE)Running linters...$(NC)"
	cd backend && source .venv/bin/activate && ruff check app/
	cd frontend && npm run lint

format: ## Format code
	@echo "$(BLUE)Formatting code...$(NC)"
	cd backend && source .venv/bin/activate && ruff format app/
	cd frontend && npm run format 2>/dev/null || true

# =============================================================================
# UTILITIES
# =============================================================================

clean: ## Clean build artifacts and caches
	@echo "$(BLUE)Cleaning...$(NC)"
	rm -rf backend/.venv
	rm -rf backend/__pycache__
	rm -rf backend/.pytest_cache
	rm -rf backend/.ruff_cache
	rm -rf frontend/node_modules
	rm -rf frontend/dist
	@echo "$(GREEN)✓ Cleaned$(NC)"

logs-backend: ## Show backend logs
	@tail -f backend/logs/*.log 2>/dev/null || echo "No log files found"

shell: ## Open Python shell with app context
	cd backend && source .venv/bin/activate && python -c "from app.config import settings; print('Settings loaded')" && python

# =============================================================================
# SCHEMA MANAGEMENT
# =============================================================================

list-schemas: ## List available schemas
	@echo "$(BLUE)Available schemas:$(NC)"
	@ls -1 schemas/*.yaml | xargs -n1 basename | sed 's/.yaml//'

validate-schema: ## Validate schema files
	@echo "$(BLUE)Validating schemas...$(NC)"
	cd backend && source .venv/bin/activate && python -c "\
from app.schema.loader import SchemaLoader; \
loader = SchemaLoader(); \
for s in ['contract', 'research_paper']: \
    try: \
        loader.load_schema(s); \
        print(f'✓ {s}.yaml is valid'); \
    except Exception as e: \
        print(f'✗ {s}.yaml: {e}')"

# =============================================================================
# STRATEGY MANAGEMENT
# =============================================================================

strategy: ## Show current extraction & retrieval strategies
	@echo "$(BLUE)Current Strategies:$(NC)"
	@echo ""
	@echo "$(YELLOW)Extraction Strategy:$(NC)"
	@curl -s http://localhost:8000/strategies/extraction | python -m json.tool 2>/dev/null || \
		echo "$(RED)Backend not reachable$(NC)"
	@echo ""
	@echo "$(YELLOW)Retrieval Strategy:$(NC)"
	@curl -s http://localhost:8000/strategies/retrieval | python -m json.tool 2>/dev/null || \
		echo "$(RED)Backend not reachable$(NC)"

strategy-presets: ## List available strategy presets
	@echo "$(BLUE)Available Strategy Presets:$(NC)"
	@curl -s http://localhost:8000/strategies/presets | python -m json.tool 2>/dev/null || \
		echo "$(RED)Backend not reachable$(NC)"

strategy-load: ## Load a strategy preset (usage: make strategy-load PRESET=comprehensive)
	@if [ -z "$(PRESET)" ]; then \
		echo "$(RED)Usage: make strategy-load PRESET=<name>$(NC)"; \
		echo "Available: minimal, balanced, comprehensive, speed, research"; \
	else \
		echo "$(BLUE)Loading preset: $(PRESET)$(NC)"; \
		curl -s -X POST http://localhost:8000/strategies/preset \
			-H "Content-Type: application/json" \
			-d '{"name": "$(PRESET)"}' | python -m json.tool; \
	fi

strategy-reset: ## Reset strategies to defaults
	@echo "$(BLUE)Resetting strategies to defaults...$(NC)"
	@curl -s -X POST http://localhost:8000/strategies/reset | python -m json.tool 2>/dev/null || \
		echo "$(RED)Backend not reachable$(NC)"

# =============================================================================
# DATABASE
# =============================================================================

db-clear: ## Clear all data from Neo4j (DANGEROUS!)
	@echo "$(YELLOW)WARNING: This will delete ALL data in Neo4j!$(NC)"
	@read -p "Are you sure? [y/N] " confirm && \
		[ "$$confirm" = "y" ] && \
		curl -X DELETE http://localhost:8000/graph/all || \
		echo "Cancelled"

db-stats: ## Show database statistics
	@curl -s http://localhost:8000/graph/stats | python -m json.tool 2>/dev/null || \
		echo "$(RED)Could not fetch stats$(NC)"

# =============================================================================
# QUICK COMMANDS
# =============================================================================

install: setup ## Alias for setup

start: dev ## Alias for dev

stop: neo4j-stop docker-down ## Stop all services

restart: stop dev ## Restart all services
