.PHONY: gate test lint typecheck

# The gate: must pass before any commit is considered done
gate: test lint typecheck

test:
	uv run pytest tests/ -v --tb=short

test-cov:
	uv run pytest tests/ -v --tb=short --cov=halos --cov-report=term-missing

lint:
	@echo "lint: no linter configured for halos (Python). Placeholder."

typecheck:
	@echo "typecheck: no type checker configured for halos (Python). Placeholder."
	@# Node.js side:
	@npm run build 2>&1 | tail -1

# Run just one module's tests
test-memctl:
	uv run pytest tests/memctl/ -v

test-nightctl:
	uv run pytest tests/nightctl/ -v

test-cronctl:
	uv run pytest tests/cronctl/ -v

test-todoctl:
	uv run pytest tests/todoctl/ -v
