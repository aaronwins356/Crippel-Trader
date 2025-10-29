---
name: dashboard
type: knowledge
version: 1.0.0
agent: CodeActAgent
triggers:
  - dashboard
  - frontend
  - next.js
  - ui

description: |
  Microagent to assist with dashboard tasks in crippel-trader/frontend.
  When asked to work on the dashboard:
    - Setup dev environment: cd crippel-trader/frontend && npm install && npm run dev
    - Use existing components under frontend/src/components/; keep layout responsive and clean.
    - Wire data to the FastAPI endpoints (no hardcoded trades for production code).
    - Add badges for "paper mode" and status indicators for latency/errors.
    - Suggest small UX improvements with minimal code changes first.

usage: |
  User: "Let's work on the dashboard."
  Assistant: "<triggered dashboard microagent instructions>"

limitations: |
  - Ensure the microagent triggers only on relevant terms.
  - Does not cover styling beyond basic responsiveness.

error_handling: |
  - If dependencies fail to install, check package.json and npm registry connectivity.
  - If FastAPI endpoints are unreachable, verify backend service is running.
