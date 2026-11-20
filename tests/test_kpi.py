"""
El criterio de hecho de `objetivo.md` §3, medido sobre una partida guardada.

La partida se produce de punta a punta con una semilla fija y el backend
guionizado de la puerta F2 (`tribal.gate_f2.backend_guionizado`): decisiones,
narración y propuestas de nodo deterministas, sin red. Sobre esa base:

- se comprueban los cuatro hitos de §3.1;
- se ejecuta **literalmente** el SQL de §3.2 (con `llm` en el numerador) y se
  compara con `kpi.evaluar`;
- se exige el umbral del 50 % con nodos reales: combinaciones y nodos `llm`
  (nivel 1) y un máximo de una tradición por rama, ninguna copiada de `llm`;
- se comprueba que excluir `llm` del numerador daría otro número;
- las tradiciones se apagan si dejan de imitarse (`test_tradiciones.py`).
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import replace
from pathlib import Path
from typing import cast

import pytest

from tribal.cli import main
from tribal.config import SimConfig
from tribal.culture.kpi import UMBRAL_PCT, evaluar
from tribal.gate_f2 import backend_guionizado
from tribal.llm.cliente import ClienteLLM
from tribal.llm.cola import ColaLLM
from tribal.sim import run

SEMILLA = 1
TICKS = 3000

SQL_OBJETIVO = """
SELECT ROUND(100.0 * SUM(CASE WHEN origen IN ('combinacion','interaccion','llm')
                         THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_fuera_arbol
FROM nodos
WHERE estado = 'activo';
"""


@pytest.fixture(scope="module")
def partida(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Una partida de punta a punta, guardada, con backend guionizado y semilla fija."""
    ruta = tmp_path_factory.mktemp("kpi") / "tribu.db"
    config = replace(SimConfig(seed=SEMILLA, individuos=12), crisis=True)
    cola = ColaLLM(ClienteLLM(transporte=backend_guionizado()), sincrona=True)
    run(TICKS, SEMILLA, headless=True, config=config, cola=cola, db=ruta)
    return ruta


def _consulta(ruta: Path, sql: str) -> sqlite3.Row:
    with sqlite3.connect(ruta) as conexion:
        conexion.row_factory = sqlite3.Row
        fila = conexion.execute(sql).fetchone()
    assert fila is not None
    return cast(sqlite3.Row, fila)


def test_el_e2e_llega_a_fuego_herramienta_lenguaje_y_mito(partida: Path) -> None:
    kpi = evaluar(partida)

    assert kpi.hitos.todos(), kpi.a_json()
    assert kpi.hitos.fuego is True
    assert kpi.hitos.herramienta_compuesta is True
    assert kpi.hitos.proto_lenguaje is True
    assert kpi.hitos.mito is True


def test_la_consulta_literal_de_objetivo_coincide_con_evaluar(partida: Path) -> None:
    kpi = evaluar(partida)
    fila = _consulta(partida, SQL_OBJETIVO)
    numerador = _consulta(
        partida,
        "SELECT SUM(CASE WHEN origen IN ('combinacion','interaccion','llm') "
        "THEN 1 ELSE 0 END), COUNT(*) FROM nodos WHERE estado = 'activo'",
    )

    assert float(fila["pct_fuera_arbol"]) == kpi.pct_fuera_arbol
    assert int(numerador[0]) == kpi.fuera_arbol
    assert int(numerador[1]) == kpi.activos
    assert (
        _consulta(partida, "SELECT COUNT(*) FROM nodos WHERE origen = 'llm' AND estado = 'activo'")[
            0
        ]
        > 0
    ), "el e2e debe tener nodos llm para que el cambio esté anclado"


def test_excluir_llm_del_numerador_daria_otro_numero(partida: Path) -> None:
    kpi = evaluar(partida)
    sin_llm = _consulta(
        partida,
        "SELECT ROUND(100.0 * SUM(CASE WHEN origen IN ('combinacion','interaccion') "
        "THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct FROM nodos WHERE estado = 'activo'",
    )

    assert float(sin_llm["pct"]) != kpi.pct_fuera_arbol


def test_ninguna_tradicion_copia_un_nodo_llm_ni_pasa_el_tope_por_rama(partida: Path) -> None:
    with sqlite3.connect(partida) as conexion:
        conexion.row_factory = sqlite3.Row
        tradiciones = conexion.execute(
            "SELECT id, tipo, requisitos, estado FROM nodos WHERE origen = 'interaccion'"
        ).fetchall()
        origenes = {
            fila["id"]: fila["origen"] for fila in conexion.execute("SELECT id, origen FROM nodos")
        }

    assert tradiciones
    por_rama: dict[str, int] = {}
    for fila in tradiciones:
        assert fila["id"].startswith("tradicion_")
        requisitos = json.loads(fila["requisitos"])
        assert len(requisitos) == 1
        assert origenes.get(requisitos[0]) != "llm", "tradición copiada de un nodo llm"
        por_rama[fila["tipo"]] = por_rama.get(fila["tipo"], 0) + 1
    assert max(por_rama.values()) <= 1, por_rama


def test_la_partida_cumple_el_umbral_de_objetivo(partida: Path) -> None:
    assert evaluar(partida).pct_fuera_arbol >= UMBRAL_PCT


def test_report_kpi_json_publica_hitos_porcentaje_y_veredicto(
    partida: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["report", "kpi", "--db", str(partida), "--json"]) == 0

    datos = json.loads(capsys.readouterr().out)
    assert set(datos["hitos"]) == {
        "fuego",
        "herramienta_compuesta",
        "proto_lenguaje",
        "mito",
    }
    assert datos["pct_fuera_arbol"] == evaluar(partida).pct_fuera_arbol
    assert datos["umbral"] == UMBRAL_PCT
    assert datos["veredicto"] is True


def test_report_kpi_texto_muestra_los_cuatro_hitos(
    partida: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["report", "kpi", "--db", str(partida)]) == 0

    salida = capsys.readouterr().out
    for hito in ("fuego", "herramienta_compuesta", "proto_lenguaje", "mito"):
        assert hito in salida
    assert "veredicto" in salida


def test_report_kpi_de_un_fichero_que_no_es_partida_sale_con_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    ruta = tmp_path / "no-es-tribu.db"
    ruta.write_bytes(b"no soy sqlite")

    assert main(["report", "kpi", "--db", str(ruta)]) == 2
    assert "error:" in capsys.readouterr().err
