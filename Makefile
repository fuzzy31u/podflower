# PodFlower Makefile

.PHONY: help install format lint test bench run clean

# Default target
help:
	@echo "PodFlower Development Commands"
	@echo "==============================="
	@echo ""
	@echo "Setup:"
	@echo "  install     Install dependencies and setup environment"
	@echo "  setup-dev   Setup development environment"
	@echo ""
	@echo "Code Quality:"
	@echo "  format      Format code with black and ruff"
	@echo "  lint        Run linting checks"
	@echo "  type-check  Run mypy type checking"
	@echo ""
	@echo "Testing:"
	@echo "  test        Run unit and integration tests"
	@echo "  test-unit   Run unit tests only"
	@echo "  test-e2e    Run end-to-end tests"
	@echo "  bench       Run benchmarks and quality metrics"
	@echo ""
	@echo "Execution:"
	@echo "  run         Run the full pipeline with sample data"
	@echo "  demo        Run demo with verbose output"
	@echo ""
	@echo "Maintenance:"
	@echo "  clean       Clean temporary files and cache"
	@echo "  deps-update Update dependencies"

# =============================================================================
# Setup
# =============================================================================

install:
	@echo "Installing PodFlower dependencies..."
	pip install -r requirements.txt
	@echo "✅ Dependencies installed"

setup-dev: install
	@echo "Setting up development environment..."
	pip install pytest pytest-asyncio pytest-mock coverage mypy black ruff
	@echo "✅ Development environment ready"

# =============================================================================
# Code Quality
# =============================================================================

format:
	@echo "Formatting code with black and ruff..."
	black --line-length 88 --target-version py311 agents/ pipelines/ tests/
	ruff --fix agents/ pipelines/ tests/
	@echo "✅ Code formatted"

lint:
	@echo "Running linting checks..."
	ruff check agents/ pipelines/ tests/
	@echo "✅ Linting passed"

type-check:
	@echo "Running mypy type checking..."
	mypy --strict agents/ pipelines/
	@echo "✅ Type checking passed"

# =============================================================================
# Testing
# =============================================================================

test: test-unit test-e2e
	@echo "✅ All tests passed"

test-unit:
	@echo "Running unit tests..."
	pytest tests/ -v --tb=short -x
	@echo "✅ Unit tests passed"

test-e2e:
	@echo "Running end-to-end tests..."
	pytest tests/test_pipeline.py -v --tb=short
	@echo "✅ End-to-end tests passed"

bench:
	@echo "Running benchmarks and quality metrics..."
	@echo "=== Coverage Report ==="
	coverage run -m pytest tests/
	coverage report --show-missing
	@echo ""
	@echo "=== Performance Metrics ==="
	python -m pytest tests/test_pipeline.py --benchmark-only --benchmark-sort=mean
	@echo "✅ Benchmarks completed"

# =============================================================================
# Execution
# =============================================================================

run:
	@echo "Running PodFlower pipeline..."
	python pipelines/full_workflow.py sample_episode/

demo:
	@echo "Running PodFlower demo with verbose output..."
	LOG_LEVEL=DEBUG python pipelines/full_workflow.py sample_episode/

# =============================================================================
# Maintenance
# =============================================================================

clean:
	@echo "Cleaning temporary files..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type f -name ".coverage" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	rm -rf build/
	rm -rf dist/
	@echo "✅ Cleanup completed"

deps-update:
	@echo "Updating dependencies..."
	pip list --outdated --format=freeze | grep -v '^\-e' | cut -d = -f 1 | xargs -n1 pip install -U
	pip freeze > requirements.txt
	@echo "✅ Dependencies updated"

# =============================================================================
# Docker Support
# =============================================================================

docker-build:
	@echo "Building Docker image..."
	docker build -t podflower:latest .
	@echo "✅ Docker image built"

docker-run:
	@echo "Running PodFlower in Docker..."
	docker run --rm -v $(PWD)/sample_episode:/app/sample_episode -v $(PWD)/assets:/app/assets --env-file .env podflower:latest
	@echo "✅ Docker execution completed"

# =============================================================================
# Documentation
# =============================================================================

docs:
	@echo "Generating documentation..."
	@echo "📚 See SPEC.md for complete documentation"
	@echo "📚 See README.md for setup instructions"
	@echo "📚 API documentation available in agents/ directory" 