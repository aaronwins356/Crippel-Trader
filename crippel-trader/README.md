# Crippel Trader

Crippel Trader shares documentation with the rest of the Croc-Bot mono-repository. Refer
to the [root README](../README.md#crippel-trader) for architecture diagrams, features, and
step-by-step backend/frontend setup instructions.

Quick start commands:

```bash
cd crippel-trader/backend
python -m venv .venv
source .venv/bin/activate
pip install -r ../requirements.txt
uvicorn main:app --reload
```

```bash
cd crippel-trader/frontend
npm install
npm run dev
```
