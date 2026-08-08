# Tech stack

- Python >=3.12, setuptools, src package layout (`src/autoforge`).
- Runtime: Typer/Rich CLI, Pydantic, PyYAML, Jinja2, GitPython, Watchdog, FastAPI, HTTPX, Uvicorn.
- Optional server persistence: SQLAlchemy 2.x and asyncpg. PostgreSQL is the current default database contract; MySQL is future provider-plugin scope.
- Tests: pytest with `src` on pythonpath; `integration` marker requires external services.
- Quality: Ruff targets Python 3.12.