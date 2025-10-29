#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import csv
import fnmatch
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    try:
        import toml as tomllib  # type: ignore
    except ModuleNotFoundError:  # pragma: no cover
        tomllib = None  # type: ignore

try:
    from pathspec import PathSpec
except ImportError:  # pragma: no cover
    PathSpec = None  # type: ignore

IGNORE_DIRS = {".git", "analysis", "build", "coverage", "dist", "node_modules", "out", "target", "vendor", "__pycache__", ".cache", ".tox", ".venv", "*.egg-info"}
LANGUAGE_EXT = {".py": "Python", ".pyi": "Python", ".js": "JavaScript", ".jsx": "JavaScript", ".ts": "TypeScript", ".tsx": "TypeScript", ".go": "Go", ".rs": "Rust", ".java": "Java", ".kt": "Kotlin", ".cs": ".NET", ".c": "C", ".cpp": "C++", ".h": "C", ".hpp": "C++", ".md": "Markdown", ".yml": "YAML", ".yaml": "YAML", ".json": "JSON", ".toml": "TOML", ".sql": "SQL", ".env": "Config", ".sh": "Shell", ".ps1": "Powershell"}
TEST_MARKERS = ("tests", "__tests__", "test_", "_test", "Test")
ENTRY_HINTS = {"main.py", "__main__.py", "cli.py", "manage.py", "index.js", "main.ts"}
ENV_PATTERN = re.compile(r"\.env(\..+)?$")
IMPORT_JS = re.compile(r"(?:import\s+(?:[^;]+?)\s+from\s+|import\s+|require\()(['\"])([^'\"]+)\1", re.MULTILINE)
EXPORT_JS = re.compile(r"export\s+(?:const|function|class)\s+([A-Za-z0-9_]+)")


def load_toml(path: Path) -> Dict[str, object]:
    if tomllib is None:
        return {}
    with path.open("rb") as fh:
        return tomllib.load(fh)


class IgnoreMatcher:
    def __init__(self, patterns: Iterable[str]):
        self.patterns = list(patterns)
        self._spec = PathSpec.from_lines("gitwildmatch", self.patterns) if PathSpec else None

    def match(self, rel_path: str) -> bool:
        if self._spec:
            return self._spec.match_file(rel_path)
        rel = rel_path.rstrip("/")
        for pattern in self.patterns:
            p = pattern.rstrip()
            if not p:
                continue
            stem = p.rstrip("/")
            if fnmatch.fnmatch(rel, stem) or rel.startswith(stem + "/"):
                return True
        return False


def load_matcher(root: Path) -> IgnoreMatcher:
    patterns: List[str] = []
    gitignore = root / ".gitignore"
    if gitignore.exists():
        for line in gitignore.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                patterns.append(line)
    patterns.extend(sorted(IGNORE_DIRS))
    return IgnoreMatcher(patterns)


def detect_module(dir_path: Path, files: Set[str]) -> Optional[Dict[str, object]]:
    if "pyproject.toml" in files:
        manifest = dir_path / "pyproject.toml"
        data = load_toml(manifest) if manifest.exists() else {}
        project = data.get("project", {}) if isinstance(data, dict) else {}
        tool = data.get("tool", {}) if isinstance(data, dict) else {}
        poetry = tool.get("poetry", {}) if isinstance(tool, dict) else {}
        name = project.get("name") or poetry.get("name") or dir_path.name
        description = project.get("description") or poetry.get("description")
        return _module_dict(name, dir_path, "Python", "python-package", manifest, description)
    if "package.json" in files:
        manifest = dir_path / "package.json"
        try:
            data = json.loads(manifest.read_text())
        except Exception:
            data = {}
        name = data.get("name") or dir_path.name
        return _module_dict(name, dir_path, "JavaScript", "node-package", manifest, data.get("description"))
    if "go.mod" in files:
        manifest = dir_path / "go.mod"
        name = dir_path.name
        for line in manifest.read_text().splitlines():
            if line.startswith("module "):
                name = line.split(maxsplit=1)[1].strip()
                break
        return _module_dict(name, dir_path, "Go", "go-module", manifest, None)
    if "Cargo.toml" in files:
        manifest = dir_path / "Cargo.toml"
        data = load_toml(manifest) if manifest.exists() else {}
        package = data.get("package", {}) if isinstance(data, dict) else {}
        name = package.get("name", dir_path.name)
        return _module_dict(name, dir_path, "Rust", "rust-crate", manifest, package.get("description"))
    for fname in files:
        if fname.endswith(".csproj"):
            manifest = dir_path / fname
            return _module_dict(manifest.stem, dir_path, ".NET", "dotnet-project", manifest, None)
    if "CMakeLists.txt" in files:
        manifest = dir_path / "CMakeLists.txt"
        return _module_dict(dir_path.name, dir_path, "C/C++", "cmake-project", manifest, None)
    return None


def _module_dict(name: str, path: Path, language: str, module_type: str, manifest: Optional[Path], description: Optional[str]) -> Dict[str, object]:
    return {
        "name": name,
        "path": path,
        "language": language,
        "module_type": module_type,
        "manifest": manifest,
        "description": description,
        "files": [],
        "entrypoints": set(),
        "configs": set(),
        "dependencies": set(),
        "external": set(),
        "has_tests": False,
    }


def classify_kinds(path: Path) -> Set[str]:
    parts = set(path.parts)
    kinds = set()
    if any(marker in path.name for marker in TEST_MARKERS) or parts & set(TEST_MARKERS):
        kinds.add("test")
    if path.name in ENTRY_HINTS:
        kinds.add("entrypoint")
    if path.suffix in {".sh", ".ps1"}:
        kinds.add("script")
    if path.suffix in {".md", ".rst"}:
        kinds.add("docs")
    return kinds


def detect_language(path: Path) -> str:
    return LANGUAGE_EXT.get(path.suffix.lower(), "Other")


def count_loc(path: Path) -> int:
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as fh:
            return sum(1 for _ in fh)
    except OSError:
        return 0


def extract_python(path: Path) -> Tuple[List[str], List[str], Set[str]]:
    try:
        module = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
    except SyntaxError:
        return [], [], set()
    classes = [n.name for n in module.body if isinstance(n, ast.ClassDef)]
    funcs = [n.name for n in module.body if isinstance(n, ast.FunctionDef)]
    imports: Set[str] = set()
    for node in module.body:
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            imports.add(node.module.split(".")[0])
    return classes, funcs, imports


def extract_js(text: str) -> Tuple[List[str], Set[str]]:
    exports = EXPORT_JS.findall(text)
    imports: Set[str] = set()
    for match in IMPORT_JS.finditer(text):
        target = match.group(2)
        if target.startswith("."):
            continue
        imports.add(target.split("/")[0])
    return exports, imports


def resolve_module_for_path(path: Path, modules: Dict[Path, Dict[str, object]]) -> Optional[Dict[str, object]]:
    for module_path in sorted(modules.keys(), key=lambda p: len(p.parts), reverse=True):
        if path == module_path or path.is_relative_to(module_path):
            return modules[module_path]
    return None


def ensure_module(path: Path, modules: Dict[Path, Dict[str, object]], root: Path) -> Dict[str, object]:
    for parent in path.parents:
        if parent in modules:
            return modules[parent]
        if parent == root:
            break
    if root not in modules:
        modules[root] = _module_dict(root.name, root, "Mixed", "root", None, f"Synthetic root module for {root.name}")
    return modules[root]


def scan_repository(root: Path) -> Tuple[Dict[Path, Dict[str, object]], List[Dict[str, object]]]:
    matcher = load_matcher(root)
    modules: Dict[Path, Dict[str, object]] = {}
    files: List[Dict[str, object]] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dir_path = Path(dirpath)
        if dir_path != root and matcher.match(dir_path.relative_to(root).as_posix()):
            dirnames[:] = []
            continue
        dirnames[:] = [d for d in dirnames if not matcher.match((dir_path / d).relative_to(root).as_posix())]
        module = modules.get(dir_path)
        file_set = set(filenames)
        if module is None:
            mod = detect_module(dir_path, file_set)
            if mod:
                modules[dir_path] = mod
        for name in filenames:
            file_path = dir_path / name
            if matcher.match(file_path.relative_to(root).as_posix()):
                continue
            language = detect_language(file_path)
            kinds = classify_kinds(file_path)
            assigned = resolve_module_for_path(file_path, modules) or ensure_module(file_path, modules, root)
            loc = count_loc(file_path)
            symbols = defaultdict(list)
            imports: Set[str] = set()
            if language == "Python":
                classes, funcs, py_imports = extract_python(file_path)
                symbols["class"] = classes
                symbols["function"] = funcs
                imports |= py_imports
            elif language in {"JavaScript", "TypeScript"}:
                try:
                    exports, js_imports = extract_js(file_path.read_text(encoding="utf-8", errors="ignore"))
                    symbols["export"] = exports
                    imports |= js_imports
                except OSError:
                    pass
            record = {
                "path": file_path,
                "module": assigned,
                "language": language,
                "loc": loc,
                "kinds": kinds,
                "has_tests": "test" in kinds,
                "symbols": symbols,
                "imports": imports,
            }
            assigned["files"].append(record)
            if "entrypoint" in kinds:
                assigned["entrypoints"].add(file_path)
            if record["has_tests"]:
                assigned["has_tests"] = True
            if language.lower() in {"yaml", "toml", "json"} or ENV_PATTERN.search(name):
                assigned["configs"].add(file_path)
            files.append(record)
    name_counts = Counter(mod["name"] for mod in modules.values())
    for module in modules.values():
        if name_counts[module["name"]] > 1:
            rel = module["path"].relative_to(root).as_posix()
            module["name"] = f"{module['name']} ({rel})"
    return modules, files


def build_dependencies(modules: Dict[Path, Dict[str, object]]):
    name_map = {mod["name"]: mod for mod in modules.values()}
    path_map = {mod["path"].name: mod for mod in modules.values()}
    for module in modules.values():
        local: Set[str] = set()
        external: Set[str] = set()
        for file in module["files"]:
            for target in file["imports"]:
                resolved = name_map.get(target) or path_map.get(target)
                if resolved and resolved["name"] != module["name"]:
                    local.add(resolved["name"])
                else:
                    external.add(target)
        module["dependencies"].update(local)
        module["external"].update(external)


def repo_map(modules: Dict[Path, Dict[str, object]], files: List[Dict[str, object]], output: Path, root: Path) -> None:
    langs = sorted({f["language"] for f in files if f["language"] not in {"Other", ""}})
    build_tools = []
    if any(m["module_type"] == "python-package" for m in modules.values()):
        build_tools.append("Python (pyproject.toml)")
    if any(m["module_type"] == "node-package" for m in modules.values()):
        build_tools.append("Node.js (package.json)")
    ci = "GitHub Actions workflows detected" if (root / ".github" / "workflows").exists() else "No GitHub Actions workflows detected"
    structure = []
    for module in sorted(modules.values(), key=lambda m: m["path"].as_posix()):
        rel = module["path"].relative_to(root)
        indent = "  " * max(len(rel.parts) - 1, 0)
        structure.append(f"{indent}- **{module['name']}** ({module['module_type']}, {module['language']})")
    content = ["# Repository Map", "", "## Structure", *structure, "", "## Tech Stacks", f"- {', '.join(langs) if langs else 'Unknown'}", "", "## Build & Test Tooling"]
    content.extend(f"- {tool}" for tool in build_tools) if build_tools else content.append("- No build tooling detected")
    content.extend(["", "## Continuous Integration", f"- {ci}"])
    (output / "REPO_MAP.md").write_text("\n".join(content) + "\n", encoding="utf-8")


def module_summaries(modules: Dict[Path, Dict[str, object]], output: Path, root: Path) -> None:
    out_dir = output / "MODULES"
    out_dir.mkdir(parents=True, exist_ok=True)
    for module in modules.values():
        bullets = build_module_summary(module, root)
        text = [f"## {module['name']}", "", *[f"- {b}" for b in bullets]]
        (out_dir / f"{sanitize(module['name'])}.md").write_text("\n".join(text) + "\n", encoding="utf-8")


def build_module_summary(module: Dict[str, object], root: Path) -> List[str]:
    rel = module["path"].relative_to(root)
    description = module.get("description") or f"Located at `{rel}` with {len(module['files'])} files."
    bullets: List[str] = [description]
    if module["entrypoints"]:
        entries = ", ".join(sorted(str(p.relative_to(root)) for p in module["entrypoints"]))
        bullets.append(f"Entry points: {entries}.")
    else:
        bullets.append("No explicit entry points detected; library-oriented module.")
    class_names = Counter()
    func_names = Counter()
    export_names = Counter()
    for file in module["files"]:
        class_names.update(file["symbols"].get("class", []))
        func_names.update(file["symbols"].get("function", []))
        export_names.update(file["symbols"].get("export", []))
    parts = []
    if class_names:
        parts.append("classes " + ", ".join(name for name, _ in class_names.most_common(3)))
    if func_names:
        parts.append("functions " + ", ".join(name for name, _ in func_names.most_common(3)))
    if export_names:
        parts.append("exports " + ", ".join(name for name, _ in export_names.most_common(3)))
    bullets.append("Key symbols: " + "; ".join(parts) + "." if parts else "Key symbols could not be determined from source headers.")
    if module["dependencies"]:
        deps = sorted(module["dependencies"])
        bullets.append("Internal deps: " + ", ".join(deps[:10]) + (f" (+{len(deps)-10} more)." if len(deps) > 10 else "."))
    else:
        bullets.append("Internal deps: none detected.")
    if module["external"]:
        externals = sorted(module["external"])
        bullets.append("External deps: " + ", ".join(externals[:10]) + (f" (+{len(externals)-10} more)." if len(externals) > 10 else "."))
    else:
        bullets.append("External deps: none detected or manifest-only.")
    if module["configs"]:
        configs = ", ".join(sorted(str(p.relative_to(root)) for p in module["configs"]))
        bullets.append(f"Configuration files: {configs}.")
    bullets.append("Tests detected within module." if module["has_tests"] else "Tests missing or not detected.")
    return bullets[:7]


def sanitize(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", name)


def dependency_graph(modules: Dict[Path, Dict[str, object]], output: Path) -> None:
    clusters: Dict[str, List[str]] = defaultdict(list)
    for module in modules.values():
        clusters[module["language"]].append(module["name"])
    lines = ["digraph G {", "  rankdir=LR;"]
    for language, names in clusters.items():
        cluster = sanitize(language or "Unknown")
        lines.append(f"  subgraph cluster_{cluster} {{")
        lines.append(f"    label=\"{language or 'Unknown'}\";")
        for name in names:
            lines.append(f"    \"{name}\";")
        lines.append("  }")
    for module in modules.values():
        for dep in sorted(module["dependencies"]):
            lines.append(f"  \"{module['name']}\" -> \"{dep}\";")
    lines.append("}")
    (output / "DEPENDENCY_GRAPH.dot").write_text("\n".join(lines) + "\n", encoding="utf-8")


def index_csv(files: List[Dict[str, object]], output: Path, root: Path) -> None:
    with (output / "INDEX.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["module", "path", "language", "loc", "has_tests", "primary_kinds"])
        for record in files:
            rel = record["path"].relative_to(root)
            writer.writerow([
                record["module"]["name"],
                rel.as_posix(),
                record["language"],
                record["loc"],
                "yes" if record["has_tests"] else "no",
                ";".join(sorted(record["kinds"])) or "code",
            ])


def heatmap(modules: Dict[Path, Dict[str, object]], output: Path) -> None:
    data = {}
    for module in modules.values():
        files = module["files"]
        loc = sum(f["loc"] for f in files)
        test_files = sum(1 for f in files if f["has_tests"])
        languages = sorted({f["language"] for f in files if f["language"]})
        last_modified = 0.0
        for file in files:
            try:
                last_modified = max(last_modified, file["path"].stat().st_mtime)
            except OSError:
                continue
        data[module["name"]] = {
            "loc": loc,
            "file_count": len(files),
            "test_file_count": test_files,
            "languages": languages,
            "estimated_complexity": estimate_complexity(files),
            "last_modified": datetime.fromtimestamp(last_modified).isoformat() if last_modified else None,
        }
    (output / "HEATMAP.json").write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def estimate_complexity(files: Sequence[Dict[str, object]]) -> int:
    score = 0
    for file in files:
        language = file["language"]
        symbols = file["symbols"]
        if language == "Python":
            score += len(symbols.get("class", [])) * 2 + len(symbols.get("function", []))
        elif language in {"JavaScript", "TypeScript"}:
            score += len(symbols.get("export", []))
        else:
            score += 1
    return score


def ensure_outputs(path: Path) -> None:
    (path / "MODULES").mkdir(parents=True, exist_ok=True)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Generate repository mapping artefacts")
    parser.add_argument("root", nargs="?", default=".", help="Repository root directory")
    parser.add_argument("--output", default="analysis", help="Output directory for artefacts")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    output = Path(args.output).resolve()
    ensure_outputs(output)
    modules, files = scan_repository(root)
    build_dependencies(modules)
    repo_map(modules, files, output, root)
    module_summaries(modules, output, root)
    dependency_graph(modules, output)
    index_csv(files, output, root)
    heatmap(modules, output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
