"""Architecture boundary guards (import-level)."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def _scan(folder: str) -> dict[Path, set[str]]:
    return {
        path: _imports(path)
        for path in (ROOT / folder).rglob("*.py")
    }


def test_domain_does_not_depend_on_frameworks_or_outer_layers() -> None:
    forbidden = (
        "fastapi",
        "sqlalchemy",
        "langgraph",
        "app.agent",
        "app.application",
        "app.infrastructure",
        "app.api",
        "app.user_models",
    )
    violations: list[str] = []
    for path, modules in _scan("app/domain").items():
        for module in modules:
            if module == forbidden or module.startswith(tuple(f + "." for f in forbidden)):
                violations.append(f"{path.relative_to(ROOT)} imports {module}")
    assert violations == []


def test_agent_never_imports_persistence_or_sqlalchemy() -> None:
    forbidden = ("sqlalchemy", "app.infrastructure.database")
    violations: list[str] = []
    for path, modules in _scan("app/agent").items():
        for module in modules:
            if module == forbidden or module.startswith(tuple(f + "." for f in forbidden)):
                violations.append(f"{path.relative_to(ROOT)} imports {module}")
    assert violations == []


def test_application_does_not_import_api_schemas() -> None:
    violations: list[str] = []
    for path, modules in _scan("app/application").items():
        for module in modules:
            if module == "app.schemas" or module.startswith("app.schemas."):
                violations.append(f"{path.relative_to(ROOT)} imports {module}")
    assert violations == []


def test_user_model_runtime_does_not_import_persistence_or_scheduling() -> None:
    forbidden = (
        "sqlalchemy",
        "fastapi",
        "app.infrastructure",
        "app.domain.rules",
        "app.domain.scheduling",
        "app.agent",
    )
    violations: list[str] = []
    for path, modules in _scan("app/user_models").items():
        for module in modules:
            if module == forbidden or module.startswith(tuple(f + "." for f in forbidden)):
                violations.append(f"{path.relative_to(ROOT)} imports {module}")
    assert violations == []