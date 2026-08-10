# Check

Run the same quality gates as CI (lint + tests).

## Steps

From the repository root:

```bash
uv sync --locked --group dev
uv run black --check src tests
uv run isort --check-only src tests
uv run pylint --rcfile=.pylintrc src/boundarykit tests
uv run python -m unittest discover -s tests -v
```

If any step fails, fix the reported issues and re-run until all steps pass.
Report which steps failed and what you changed.
