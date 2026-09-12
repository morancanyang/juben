.PHONY: install migrate api web dev test build check

install:
	python -m venv .venv
	.venv/Scripts/pip install -r api/requirements.txt
	cd web && npm install

migrate:
	set PYTHONPATH=.&& .venv/Scripts/python -m api.migrate

api:
	set PYTHONPATH=.&& .venv/Scripts/python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload

web:
	cd web && npm run dev

dev:
	start "casebook-api" cmd /c "set PYTHONPATH=.&& .venv/Scripts/python -m uvicorn api.main:app --host 127.0.0.1 --port 8000"
	cd web && npm run dev

test:
	set PYTHONPATH=.&& .venv/Scripts/python -m pytest -q

build:
	cd web && npm run build

check:
	set PYTHONPATH=.&& .venv/Scripts/python -m pytest -q
	cd web && npm run build
