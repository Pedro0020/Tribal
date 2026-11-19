"""Export del grafo a Markdown para Obsidian (stack §6).

El criterio es de fidelidad y de bytes: un `.md` por nodo con su frontmatter,
un `[[wikilink]]` por cada arista en cada extremo, y dos exports seguidos que
dejan exactamente el mismo árbol. El slug sale del id —no del título— y una
colisión de saneado se resuelve con sufijo.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from pathlib import Path

import pytest

from tribal.cli import main
from tribal.culture.arbol import Nodo
from tribal.culture.grafo import Grafo
from tribal.sim import run
from tribal.store import Repositorio
from tribal.store.export import exportar_obsidian

_WIKILINK = re.compile(r"\[\[([^\]]+)\]\]")


def _exportar(ruta: Path, salida: Path) -> None:
    repositorio = Repositorio(ruta, crear=False)
    try:
        exportar_obsidian(repositorio, salida)
    finally:
        repositorio.cerrar()


def _frontmatter(texto: str) -> dict[str, str]:
    """Frontmatter como claves → valores sin comillas (los escalares son texto)."""
    cabecera = texto.split("---", 2)[1]
    campos: dict[str, str] = {}
    for linea in cabecera.strip().splitlines():
        clave, _, valor = linea.partition(": ")
        campos[clave] = json.loads(valor) if valor.startswith('"') else valor
    return campos


def _hash_arbol(carpeta: Path) -> str:
    """Hash de nombres + bytes de los `.md`, en orden, para comparar exports."""
    resumen = hashlib.sha256()
    for nota in sorted(carpeta.glob("*.md")):
        resumen.update(nota.name.encode("utf-8"))
        resumen.update(b"\0")
        resumen.update(nota.read_bytes())
        resumen.update(b"\0")
    return resumen.hexdigest()


@pytest.fixture()
def partida(tmp_path: Path) -> tuple[Path, Grafo]:
    """Partida con títulos repetidos, colisión de slug y un nodo apagado."""
    ruta = tmp_path / "tribu.db"
    simulacion = run(600, 42, headless=True)
    simulacion.grafo.agregar(Nodo("eco uno", "simbolico", 9, "Mismo", "Uno."))
    simulacion.grafo.agregar(Nodo("eco-uno", "simbolico", 9, "Mismo", "Dos."))
    simulacion.grafo.agregar(Nodo("eco-apagado", "simbolico", 9, "Perdido", "Ya no se usa."))
    simulacion.grafo.apagar("eco-apagado", tick=650, motivo="sin portadores")
    repositorio = Repositorio(ruta)
    try:
        repositorio.guardar(
            simulacion.mundo,
            simulacion.grafo,
            simulacion.diario,
            [],
            config=simulacion.config,
        )
    finally:
        repositorio.cerrar()
    return ruta, simulacion.grafo


def test_un_md_por_nodo_y_dos_wikilinks_por_arista(
    partida: tuple[Path, Grafo], tmp_path: Path
) -> None:
    ruta, grafo = partida
    salida = tmp_path / "vault"

    repositorio = Repositorio(ruta, crear=False)
    try:
        resumen = exportar_obsidian(repositorio, salida)
    finally:
        repositorio.cerrar()

    nodos = sorted(grafo.nodos)
    assert resumen.nodos == len(nodos)
    assert resumen.aristas == len(grafo.aristas)
    assert resumen.ficheros == len(nodos) + 1
    assert len(list(salida.glob("*.md"))) == len(nodos) + 1
    assert (salida / "index.md").exists()
    # El slug sale del id, no del título: dos títulos iguales no chocan.
    assert (salida / "eco-uno.md").exists()
    assert (salida / "eco-uno-2.md").exists()

    notas = [nota for nota in sorted(salida.glob("*.md")) if nota.name != "index.md"]
    assert len(notas) == len(nodos)

    for nota in notas:
        datos = nota.read_bytes()
        assert not datos.startswith(b"\xef\xbb\xbf")
        assert b"\r\n" not in datos
        texto = datos.decode("utf-8")
        assert texto.startswith("---\n")

    por_id: dict[str, Path] = {}
    for nota in notas:
        campos = _frontmatter(nota.read_text(encoding="utf-8"))
        assert set(campos) == {
            "id",
            "rama",
            "nivel",
            "origen",
            "estado",
            "autor",
            "tick",
            "tick_apagado",
            "motivo_apagado",
        }, nota.name
        nodo = grafo.nodos[campos["id"]]
        assert campos["rama"] == nodo.rama, nota.name
        assert campos["nivel"] == str(nodo.nivel), nota.name
        assert campos["origen"] == nodo.origen, nota.name
        assert campos["estado"] == nodo.estado, nota.name
        assert campos["autor"] == str(nodo.autor), nota.name
        assert campos["tick"] == str(nodo.tick), nota.name
        assert campos["tick_apagado"] == str(nodo.tick_apagado), nota.name
        assert campos["motivo_apagado"] == nodo.motivo_apagado, nota.name
        por_id[campos["id"]] = nota

    apagado = _frontmatter((salida / "eco-apagado.md").read_text(encoding="utf-8"))
    assert apagado["estado"] == "apagado"
    assert apagado["tick_apagado"] == "650"
    assert apagado["motivo_apagado"] == "sin portadores"

    id_a_slug = {identificador: nota.stem for identificador, nota in por_id.items()}
    for arista in grafo.aristas:
        origen = por_id[arista.origen].read_text(encoding="utf-8")
        destino = por_id[arista.destino].read_text(encoding="utf-8")
        assert f"[[{id_a_slug[arista.destino]}]] — lo desbloquea" in origen
        assert f"[[{id_a_slug[arista.origen]}]] — requiere" in destino

    # Cada arista deja un wikilink en cada extremo; el índice enlaza a cada nodo.
    enlaces = sum(len(_WIKILINK.findall(nota.read_text(encoding="utf-8"))) for nota in notas)
    assert enlaces == 2 * len(grafo.aristas)
    indice = (salida / "index.md").read_text(encoding="utf-8")
    assert len(_WIKILINK.findall(indice)) == len(nodos)


def test_dos_exports_seguidos_son_byte_a_byte_iguales(
    partida: tuple[Path, Grafo], tmp_path: Path
) -> None:
    ruta, _ = partida

    primera = tmp_path / "vault"
    _exportar(ruta, primera)
    hash_primero = _hash_arbol(primera)

    _exportar(ruta, primera)
    assert _hash_arbol(primera) == hash_primero

    otra = tmp_path / "otra"
    _exportar(ruta, otra)
    assert _hash_arbol(otra) == hash_primero


def test_arista_colgante_sale_con_2_y_sin_traza(
    partida: tuple[Path, Grafo], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Una base tocada a mano no revienta con KeyError: error legible y exit 2."""
    ruta, _ = partida
    conexion = sqlite3.connect(ruta)
    try:
        conexion.execute(
            "INSERT INTO aristas (id_origen, id_destino, tipo_relacion, peso) VALUES (?, ?, ?, ?)",
            ("guijarro", "fantasma", "prerrequisito", 1.0),
        )
        conexion.commit()
    finally:
        conexion.close()

    assert main(["export", "obsidian", "--db", str(ruta), "--out", str(tmp_path / "vault")]) == 2
    error = capsys.readouterr().err
    assert "guijarro -> fantasma" in error
    assert "inexistente" in error
    assert "Traceback" not in error


def test_cli_export_obsidian_escribe_el_vault(
    partida: tuple[Path, Grafo], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    ruta, grafo = partida
    salida = tmp_path / "cli"

    assert main(["export", "obsidian", "--db", str(ruta), "--out", str(salida)]) == 0
    assert (salida / "index.md").exists()
    assert len(list(salida.glob("*.md"))) == len(grafo.nodos) + 1
    assert "export obsidian:" in capsys.readouterr().out


def test_export_sale_con_2_si_la_base_no_sirve(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["export", "obsidian", "--db", str(tmp_path / "no-existe.db")]) == 2
    assert "no existe" in capsys.readouterr().err

    basura = tmp_path / "basura.db"
    basura.write_text("esto no es sqlite", encoding="utf-8")
    assert main(["export", "obsidian", "--db", str(basura), "--out", str(tmp_path / "v")]) == 2
    assert "error" in capsys.readouterr().err
