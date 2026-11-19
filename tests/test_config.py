"""`SimConfig`: JSON de ida y vuelta, validación y reproducibilidad de una partida."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from tribal.agents import necesidades
from tribal.cli import main
from tribal.config import MIN_INDIVIDUOS, SimConfig
from tribal.core.modelos import Genoma, Necesidades
from tribal.sim import run

CLAVES = {
    "seed",
    "individuos",
    "ancho",
    "alto",
    "tasa_sed",
    "tasa_energia",
    "tasa_salud",
    "cooldown_reproduccion",
    "depredadores",
    "depredador_activo",
    "crisis",
    "sequia_ticks",
    "migracion",
    "ticks_por_estacion",
    "umbral_agotamiento",
    "ticks_migracion",
    "max_pensando",
    "ticks_guardado",
}


def _escribir(tmp_path: Path, contenido: dict[str, object]) -> Path:
    destino = tmp_path / "cfg.json"
    destino.write_text(json.dumps(contenido), encoding="utf-8")
    return destino


def test_los_defaults_son_los_documentados() -> None:
    """Los defaults de Fase 0 más el gradiente ambiental (eje 3).

    El mapa, las tasas y la reproducción son los de siempre. De AMB-001 llegan
    `migracion` (encendida: los parches agotados migran), `ticks_por_estacion`
    (0 = sin estaciones, así que el clima no cambia nada por defecto) y el
    umbral de agotamiento de un parche.
    """
    config = SimConfig()

    assert config.a_json() == {
        "seed": 42,
        "individuos": 12,
        "ancho": 60,
        "alto": 34,
        "tasa_sed": 0.16,
        "tasa_energia": 0.15,
        "tasa_salud": 0.6,
        "cooldown_reproduccion": 600,
        "depredadores": 1,
        "depredador_activo": True,
        "crisis": False,
        "sequia_ticks": 0,
        "migracion": True,
        "ticks_por_estacion": 0,
        "umbral_agotamiento": 0.25,
        "ticks_migracion": 3000,
        "max_pensando": 4,
        "ticks_guardado": 300,
    }
    assert set(config.a_json()) == CLAVES


def test_las_tasas_no_se_desincronizan_de_necesidades() -> None:
    config = SimConfig()

    assert config.tasa_sed == necesidades.SED_POR_TICK
    assert config.tasa_energia == necesidades.ENERGIA_POR_TICK
    assert config.tasa_salud == necesidades.DANO_SALUD


def test_json_ida_y_vuelta(tmp_path: Path) -> None:
    original = SimConfig(seed=7, individuos=9, ancho=40, alto=20, tasa_sed=0.2)
    destino = tmp_path / "cfg.json"
    destino.write_text(json.dumps(original.a_json()), encoding="utf-8")

    assert SimConfig.desde_json(destino) == original


def test_config_sin_claves_toma_los_defaults(tmp_path: Path) -> None:
    ruta = _escribir(tmp_path, {"seed": 3})

    assert SimConfig.desde_json(ruta) == SimConfig(seed=3)


@pytest.mark.parametrize(
    ("datos", "clave"),
    [
        ({"ancho": 6}, "ancho"),
        ({"ancho": 60.7}, "ancho"),
        ({"tasa_sed": "0.2"}, "tasa_sed"),
        ({"seed": "hola"}, "seed"),
        ({"individuos": MIN_INDIVIDUOS - 3}, "individuos"),
        ({"individuos": True}, "individuos"),
        ({"tasa_salud": -0.1}, "tasa_salud"),
        ({"depredadores": -1}, "depredadores"),
        ({"cooldown_reproduccion": 0}, "cooldown_reproduccion"),
        ({"depredador_activo": 1}, "depredador_activo"),
        ({"ticks_por_estacion": -5}, "ticks_por_estacion"),
        ({"ticks_migracion": 0}, "ticks_migracion"),
        ({"ticks_migracion": -10}, "ticks_migracion"),
        ({"umbral_agotamiento": 0.0}, "umbral_agotamiento"),
        ({"umbral_agotamiento": 1.5}, "umbral_agotamiento"),
        ({"umbral_agotamiento": "0.2"}, "umbral_agotamiento"),
        ({"migracion": 1}, "migracion"),
        ({"gravedad": 9.8}, "gravedad"),
    ],
)
def test_cli_rechaza_config_invalida_sin_traza(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    datos: dict[str, object],
    clave: str,
) -> None:
    ruta = _escribir(tmp_path, datos)

    assert main(["run", "--headless", "--json", "--ticks", "30", "--config", str(ruta)]) == 2
    capturado = capsys.readouterr()
    assert capturado.out == ""
    assert "error:" in capturado.err
    assert clave in capturado.err
    assert "Traceback" not in capturado.err


def test_el_error_de_validacion_nombra_clave_y_valor(tmp_path: Path) -> None:
    ruta = _escribir(tmp_path, {"tasa_sed": "0.2"})

    with pytest.raises(ValueError) as exc:
        SimConfig.desde_json(ruta)
    assert "tasa_sed" in str(exc.value)
    assert "'0.2'" in str(exc.value)


def test_clave_desconocida_falla_con_su_nombre(tmp_path: Path) -> None:
    ruta = _escribir(tmp_path, {"seed": 1, "gravedad": 9.8})

    with pytest.raises(ValueError) as exc:
        SimConfig.desde_json(ruta)
    assert "gravedad" in str(exc.value)


def test_evolucionar_aplica_la_tasa_recibida() -> None:
    urgencias = Necesidades(energia=80.0, sed=10.0)

    necesidades.evolucionar(urgencias, Genoma(), tasa_sed=0.5, tasa_energia=0.25)

    assert urgencias.sed == 10.5
    assert urgencias.energia == 79.75


def test_misma_semilla_y_config_dan_el_mismo_resumen() -> None:
    config = SimConfig(seed=11, individuos=10)

    def correr() -> dict[str, object]:
        return run(ticks=300, seed=config.seed, headless=True, config=config).resumen()

    assert correr() == correr()


def _metricas(resumen: dict[str, object]) -> dict[str, object]:
    """Resumen sin el eco de la config: `config` difiere por construcción y no prueba nada."""
    return {clave: valor for clave, valor in resumen.items() if clave != "config"}


def test_cambiar_una_tasa_cambia_el_resumen() -> None:
    base = SimConfig(seed=11, individuos=10)
    alterada = SimConfig(seed=11, individuos=10, tasa_sed=0.3)

    def correr(config: SimConfig) -> dict[str, object]:
        return run(ticks=300, seed=config.seed, headless=True, config=config).resumen()

    assert _metricas(correr(base)) != _metricas(correr(alterada))
    assert correr(base)["media_sed"] != correr(alterada)["media_sed"]


def test_cli_con_config_usa_y_refleja_los_parametros(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config = SimConfig(seed=5, individuos=9, tasa_sed=0.25)
    ruta = tmp_path / "cfg.json"
    ruta.write_text(json.dumps(config.a_json()), encoding="utf-8")

    assert main(["run", "--headless", "--json", "--ticks", "90", "--config", str(ruta)]) == 0
    datos = json.loads(capsys.readouterr().out)
    assert datos["config"] == config.a_json()
    assert datos["seed"] == 5
    assert datos["poblacion_inicial"] == 9


def test_cli_seed_y_individuos_mandan_sobre_el_fichero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    ruta = tmp_path / "cfg.json"
    ruta.write_text(json.dumps(SimConfig(seed=5, individuos=9).a_json()), encoding="utf-8")

    assert (
        main(
            [
                "run",
                "--headless",
                "--json",
                "--ticks",
                "30",
                "--config",
                str(ruta),
                "--seed",
                "8",
                "--individuos",
                "10",
            ]
        )
        == 0
    )
    datos = json.loads(capsys.readouterr().out)
    assert datos["seed"] == 8
    assert datos["poblacion_inicial"] == 10
    assert datos["config"]["seed"] == 8
    assert datos["config"]["individuos"] == 10


def test_dos_ejecuciones_del_cli_con_la_misma_config_son_identicas(tmp_path: Path) -> None:
    """Repetibilidad real: dos procesos, mismo fichero, misma salida byte a byte."""
    config = SimConfig(seed=4, individuos=9)
    ruta = tmp_path / "cfg.json"
    ruta.write_text(json.dumps(config.a_json()), encoding="utf-8")
    comando = [
        sys.executable,
        "-m",
        "tribal",
        "run",
        "--headless",
        "--json",
        "--ticks",
        "60",
        "--config",
        str(ruta),
    ]

    primera = subprocess.run(comando, capture_output=True, text=True, check=True)
    segunda = subprocess.run(comando, capture_output=True, text=True, check=True)

    assert primera.stdout == segunda.stdout
    assert json.loads(primera.stdout)["config"] == config.a_json()


def test_cli_con_config_invalida_sale_con_2_sin_traza(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    ruta = _escribir(tmp_path, {"individuos": 3})

    assert main(["run", "--headless", "--json", "--ticks", "30", "--config", str(ruta)]) == 2
    capturado = capsys.readouterr()
    assert capturado.out == ""
    assert "error:" in capturado.err
    assert "individuos" in capturado.err
    assert "Traceback" not in capturado.err


def test_cli_con_config_inexistente_sale_con_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    ruta = tmp_path / "no-existe.json"

    assert main(["run", "--headless", "--json", "--ticks", "30", "--config", str(ruta)]) == 2
    assert "error:" in capsys.readouterr().err
