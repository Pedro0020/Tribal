"""
Tests de la tabla de fuentes del RAG (`RagTool.FUENTES` / `RagTool.fuentes`).

El fallo que cierran: la fila del paquete del producto estaba escrita a mano
como `("app", ...)`. Tras renombrar el paquete a `tribal/`, ese directorio no
existe y el índice lo saltaba en silencio — el código del producto dejaba de
ser buscable sin un solo error.
"""

from __future__ import annotations

from pathlib import Path

from agents.tools.rag_tool import RagTool


def test_fuentes_incluye_el_paquete_del_proyecto():
    subs = [fila[0] for fila in RagTool.FUENTES]

    assert "tribal" in subs
    assert "app" not in subs


def test_fuentes_sale_de_project_slug(tmp_path: Path):
    (tmp_path / "project.yml").write_text("project_slug: otro_paquete\n", encoding="utf-8")

    subs = [fila[0] for fila in RagTool.fuentes(tmp_path)]

    assert subs[0] == "otro_paquete"
    assert "tribal" not in subs


def test_fuentes_sin_project_slug_no_inventa_paquete(tmp_path: Path):
    """Sin `project.yml` no hay fila de paquete: ni `app` ni una vacía."""
    subs = [fila[0] for fila in RagTool.fuentes(tmp_path)]

    assert "app" not in subs
    assert "" not in subs
    assert subs[0] == "api"  # el resto de la tabla sigue intacta


def test_fuentes_no_duplica_el_slug(tmp_path: Path):
    (tmp_path / "project.yml").write_text("project_slug: agents\n", encoding="utf-8")

    subs = [fila[0] for fila in RagTool.fuentes(tmp_path)]

    assert subs.count("agents") == 1
