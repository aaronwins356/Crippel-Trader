PYTHON=python3
PIP=$(PYTHON) -m pip
POETRY?=
NPM?=npm
BACKEND_DIR=croc-bot/backend
DASHBOARD_DIR=croc-bot/dashboard

.PHONY: setup-backend setup-dashboard dev test train backtest lint fmt clean

setup-backend:
cd $(BACKEND_DIR) && $(PIP) install -U pip && $(PIP) install -e .[dev]

setup-dashboard:
cd $(DASHBOARD_DIR) && $(NPM) install

dev:
cd $(BACKEND_DIR) && $(PYTHON) -m croc.app

test:
cd $(BACKEND_DIR) && pytest

train:
cd $(BACKEND_DIR) && ./scripts/train_rl.sh

backtest:
cd $(BACKEND_DIR) && ./scripts/backtest.sh

lint:
cd $(BACKEND_DIR) && ruff check croc

fmt:
cd $(BACKEND_DIR) && ruff format croc

clean:
rm -rf $(BACKEND_DIR)/.pytest_cache $(BACKEND_DIR)/.mypy_cache $(BACKEND_DIR)/htmlcov
rm -rf $(DASHBOARD_DIR)/node_modules $(DASHBOARD_DIR)/dist
