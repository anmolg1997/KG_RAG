# Makefile Command Reference

This guide explains all available `make` commands for the KG-RAG project.

---

## Quick Reference

| Command | Description |
|---------|-------------|
| `make help` | Show all available commands |
| `make setup` | Complete project setup |
| `make dev` | Start all development servers |
| `make health` | Check all service health |
| `make strategy` | Show current strategy config |
| `make strategy-load PRESET=X` | Load a preset (balanced, strict, etc.) |
| `make db-stats` | Show database statistics |
| `make db-clear` | Clear all data (with confirmation) |
| `make stop-servers` | Stop backend and frontend |

---

## Setup Commands

### `make setup`
Complete one-time project setup:
1. Starts Neo4j (Docker)
2. Creates Python virtual environment with uv
3. Installs Python dependencies
4. Installs Node.js dependencies

```bash
make setup
```

### `make backend-setup`
Setup only the backend:
```bash
make backend-setup
# Creates .venv/ and installs Python packages
```

### `make frontend-setup`
Setup only the frontend:
```bash
make frontend-setup
# Runs npm install
```

---

## Development Commands

### `make dev`
Start all development servers (backend + frontend):
```bash
make dev
# Backend:  http://localhost:8000
# Frontend: http://localhost:5173
```

### `make backend`
Start only the backend server:
```bash
make backend
# Runs: uvicorn app.main:app --reload
```

### `make frontend`
Start only the frontend dev server:
```bash
make frontend
# Runs: npm run dev
```

---

## Neo4j Commands

### Neo4j Ports

| Port | Protocol | Purpose |
|------|----------|---------|
| **7474** | HTTP | Web Browser UI for visual exploration |
| **7687** | Bolt | Application connection protocol |

**Access your database:**
- Local Browser: http://localhost:7474
- Hosted Browser: https://browser.neo4j.io/ (connect to `bolt://localhost:7687`)

### `make neo4j`
Start Neo4j database:
```bash
make neo4j
# Starts or creates Neo4j container
# Browser UI: http://localhost:7474
# Bolt connection: bolt://localhost:7687
```

### `make neo4j-stop`
Stop Neo4j:
```bash
make neo4j-stop
```

### `make neo4j-logs`
View Neo4j logs:
```bash
make neo4j-logs
```

### `make neo4j-shell`
Open Cypher shell:
```bash
make neo4j-shell
# Interactive Neo4j command line
```

---

## Docker Commands

### `make docker-up`
Start all services with Docker Compose:
```bash
make docker-up
```

### `make docker-down`
Stop all services:
```bash
make docker-down
```

### `make docker-logs`
View all service logs:
```bash
make docker-logs
```

### `make docker-build`
Rebuild Docker images:
```bash
make docker-build
```

---

## Health & Monitoring

### `make health`
Quick health check of all services:
```bash
make health
# Shows status of: Neo4j, Backend, Frontend
```

### `make health-detail`
Detailed health information:
```bash
make health-detail
# Shows full JSON health response
```

---

## Testing & Quality

### `make test`
Run backend tests:
```bash
make test
```

### `make test-cov`
Run tests with coverage report:
```bash
make test-cov
# Generates HTML coverage report
```

### `make lint`
Run linters on all code:
```bash
make lint
# Runs ruff (Python) and eslint (JavaScript)
```

### `make format`
Auto-format code:
```bash
make format
```

---

## Schema Commands

### `make list-schemas`
List available schemas:
```bash
make list-schemas
# Output: contract, research_paper, etc.
```

### `make validate-schema`
Validate schema files:
```bash
make validate-schema
# Checks all YAML schemas for errors
```

---

## Strategy Commands

### `make strategy`
Show current extraction & retrieval strategies:
```bash
make strategy
# Displays current strategy configuration
```

### `make strategy-presets`
List available strategy presets:
```bash
make strategy-presets
# Shows: minimal, balanced, comprehensive, speed, research, strict
```

### `make strategy-load`
Load a specific strategy preset:
```bash
make strategy-load PRESET=comprehensive
# Available: minimal, balanced, comprehensive, speed, research, strict
```

### `make strategy-reset`
Reset strategies to defaults (balanced):
```bash
make strategy-reset
```

**Preset Summary:**
| Preset | Validation Mode | Best For |
|--------|-----------------|----------|
| minimal | ignore | Quick testing |
| balanced | warn | General use (default) |
| comprehensive | store_valid | Deep analysis |
| speed | ignore | High-volume |
| research | warn | Academic papers |
| strict | strict | Compliance |

---

## Database Commands

### `make db-stats`
Show database statistics:
```bash
make db-stats
# Shows node counts, relationship counts
# Distinguishes between empty database and connection errors
```

### `make db-clear`
Clear all data (with confirmation):
```bash
make db-clear
# First shows current stats, then prompts for confirmation
# Skips prompt if database is already empty
```

---

## Utility Commands

### `make clean`
Remove all build artifacts:
```bash
make clean
# Removes: .venv, node_modules, dist, __pycache__
```

### `make shell`
Open Python shell with app context:
```bash
make shell
# Useful for debugging
```

---

## Aliases

| Alias | Same as |
|-------|---------|
| `make install` | `make setup` |
| `make start` | `make dev` |
| `make stop` | `make neo4j-stop docker-down` |
| `make restart` | `make stop dev` |

---

## Examples

### First-time Setup
```bash
# Clone and setup
git clone <repo>
cd KG_RAG
make setup

# Configure
cp env.example backend/.env
# Edit backend/.env with your API keys

# Start
make dev
```

### Daily Development
```bash
# Start everything
make dev

# In another terminal, check health
make health

# Run tests before committing
make test
make lint
```

### Troubleshooting
```bash
# Check what's running
make health

# View logs
make neo4j-logs
make docker-logs

# Reset everything
make clean
make setup
```
