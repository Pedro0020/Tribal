"""Idempotencia de `commit_feature`: un fallo de commit no deja bump ni CHANGELOG a medias."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

from agents.agents.documentation_agent import DocumentationAgent
from agents.agents.git_agent import GitAgent
from agents.tools.git_tool import GitTool
from agents.tools.process_tool import ProcessResult

_VERSIONED_FILES = ("pyproject.toml", "README.md", "CHANGELOG.md", "uv.lock")


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, encoding="utf-8", check=True
    ).stdout


def _setup_project(root: Path) -> None:
    (root / "pyproject.toml").write_text(
        '[project]\nname = "x"\nversion = "0.1.0"\n', encoding="utf-8"
    )
    (root / "README.md").write_text(
        "![Version](https://img.shields.io/badge/Version-0.1.0-green)\n\n**Versión:** 0.1.0\n",
        encoding="utf-8",
    )
    subprocess.run(
        ["uv", "lock"], cwd=root, check=True, capture_output=True, text=True, encoding="utf-8"
    )
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "chore: setup")
    (root / "mi_paquete" / "modulo.py").write_text("print('feature')\n", encoding="utf-8")


def _md5(path: Path) -> str | None:
    return hashlib.md5(path.read_bytes()).hexdigest() if path.exists() else None


def test_commit_feature_no_duplica_tras_dos_fallos_y_cierra_al_tercero(context, monkeypatch):
    _setup_project(context.root)
    agent = GitAgent(context=context)
    original_commit = GitTool.commit

    def failing_commit(self, message: str) -> ProcessResult:
        return ProcessResult(
            command=["git", "commit", "-m", message],
            returncode=1,
            stdout="",
            stderr="hook pre-commit falló",
        )

    monkeypatch.setattr(GitTool, "commit", failing_commit)
    for _ in range(2):
        result = agent.commit_feature(id="FIX-005", title="Commit idempotente")

        assert not result.success
        assert result.needs, "un cierre fallido debe pedir acción, no sólo avisar"
        assert 'version = "0.1.0"' in (context.root / "pyproject.toml").read_text(encoding="utf-8")
        assert not (context.root / "CHANGELOG.md").exists(), "no debe quedar una sección a medias"
        status = _git(context.root, "status", "--porcelain")
        assert not any(name in status for name in _VERSIONED_FILES), status

    monkeypatch.setattr(GitTool, "commit", original_commit)
    result = agent.commit_feature(id="FIX-005", title="Commit idempotente")

    assert result.success
    assert result.data["next_version"] == "0.1.1"
    assert 'version = "0.1.1"' in (context.root / "pyproject.toml").read_text(encoding="utf-8")
    changelog = (context.root / "CHANGELOG.md").read_text(encoding="utf-8")
    assert changelog.count("(FIX-005)") == 1
    assert changelog.count("## [Unreleased]") == 1
    lock = subprocess.run(
        ["uv", "lock", "--check"],
        cwd=context.root,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert lock.returncode == 0, lock.stderr
    assert "feat(FIX-005)" in _git(context.root, "log", "--oneline")


def test_commit_feature_dry_run_no_escribe_nada(context):
    _setup_project(context.root)
    before = {name: _md5(context.root / name) for name in _VERSIONED_FILES}

    result = GitAgent(context=context).commit_feature(
        id="FIX-005", title="Commit idempotente", dry_run=True
    )

    assert result.success
    assert {name: _md5(context.root / name) for name in _VERSIONED_FILES} == before


def test_commit_feature_devuelve_needs_si_el_lock_no_cuadra(context):
    _setup_project(context.root)
    broken = '[project\nversion = "0.1.0"\n'
    (context.root / "pyproject.toml").write_text(broken, encoding="utf-8")

    result = GitAgent(context=context).commit_feature(id="FIX-005", title="Commit idempotente")

    assert not result.success
    assert any("lock" in need.lower() for need in result.needs), result.needs
    assert (context.root / "pyproject.toml").read_text(encoding="utf-8") == broken
    assert not (context.root / "CHANGELOG.md").exists()


def test_update_changelog_es_idempotente_por_feature(context):
    agent = DocumentationAgent(context=context)

    for _ in range(2):
        result = agent.run(
            "update_changelog",
            feature_id="FIX-005",
            feature_title="Commit idempotente",
            dry_run=False,
        )
        assert result.success
    third = agent.run(
        "update_changelog", feature_id="FIX-006", feature_title="Otra pieza", dry_run=False
    )
    assert third.success

    changelog = (context.root / "CHANGELOG.md").read_text(encoding="utf-8")
    assert changelog.count("(FIX-005)") == 1
    assert changelog.count("## [Unreleased]") == 1, "la sección de hoy se reutiliza, no se duplica"
    assert "(FIX-006)" in changelog
