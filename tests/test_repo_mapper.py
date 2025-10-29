import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools import repo_mapper


def create_python_module(root: Path) -> Path:
    backend = root / "backend"
    backend.mkdir()
    (backend / "pyproject.toml").write_text(
        """
[project]
name = "demo-backend"
description = "Demo backend service"
""".strip()
    )
    (backend / "main.py").write_text(
        """
import frontend

class Service:
    pass

def run():
    return Service()
""".strip()
    )
    (backend / "tests").mkdir()
    (backend / "tests" / "test_main.py").write_text("from backend.main import run\n")
    return backend


def create_frontend_module(root: Path) -> Path:
    frontend = root / "frontend"
    frontend.mkdir()
    (frontend / "package.json").write_text(
        """
{"name": "demo-frontend", "description": "UI"}
"""
    )
    (frontend / "index.js").write_text(
        """
import axios from 'axios';
export function boot() {
  return axios.create();
}
"""
    )
    return frontend


def test_repo_mapper_generates_expected_artifacts(tmp_path: Path):
    create_python_module(tmp_path)
    create_frontend_module(tmp_path)

    output_dir = tmp_path / "analysis"
    repo_mapper.main([str(tmp_path), "--output", str(output_dir)])

    repo_map = output_dir / "REPO_MAP.md"
    modules_dir = output_dir / "MODULES"
    index_csv = output_dir / "INDEX.csv"
    heatmap = output_dir / "HEATMAP.json"

    assert repo_map.exists()
    assert modules_dir.is_dir()
    assert index_csv.exists()
    assert heatmap.exists()

    content = repo_map.read_text()
    assert "demo-backend" in content
    assert "demo-frontend" in content

    heatmap_data = json.loads(heatmap.read_text())
    assert "demo-backend" in heatmap_data
    assert heatmap_data["demo-backend"]["file_count"] >= 2
    assert heatmap_data["demo-backend"]["test_file_count"] == 1

    backend_module = modules_dir / "demo-backend.md"
    assert backend_module.exists()
    backend_summary = backend_module.read_text()
    assert "Entry points" in backend_summary
    assert "Internal deps" in backend_summary


@pytest.mark.parametrize(
    "relative_path",
    [
        "backend/tests/test_main.py",
        "frontend/index.js",
    ],
)
def test_index_csv_contains_expected_rows(tmp_path: Path, relative_path: str):
    create_python_module(tmp_path)
    create_frontend_module(tmp_path)
    output_dir = tmp_path / "analysis"
    repo_mapper.main([str(tmp_path), "--output", str(output_dir)])

    rows = (output_dir / "INDEX.csv").read_text().splitlines()
    assert any(relative_path in row for row in rows)
