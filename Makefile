.PHONY: install test lint format mypy clean run

install:
	./scripts/install.sh

test:
	python3 -m pytest tests/

lint:
	ruff check src/ tests/

format:
	ruff format src/ tests/

mypy:
	mypy src/

clean:
	rm -rf .venv dist build *.egg-info __pycache__ src/playyt/__pycache__

run:
	python3 -m playyt
