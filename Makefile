.PHONY: install test lint api frontend train pipeline compose-up compose-down

install:
	python -m pip install -e '.[dev]'

api:
	uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest

lint:
	ruff check backend ml tests

train:
	python -m ml.training.train --input data/processed/training.csv --output backend/artifacts/price_model.joblib

pipeline:
	python -m ml.pipeline.flow

frontend:
	cd frontend && npm run dev

compose-up:
	docker compose up --build

compose-down:
	docker compose down -v
