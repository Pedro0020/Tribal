"""
tribal.cli — punto de entrada del proyecto: `python -m tribal` o `make run`.

argparse de la stdlib. `hello` se mantiene como humo del renombrado; `run`
arranca la simulación en ventana o en modo headless, `report culture` resume
el árbol de conocimiento de una corrida headless corta y `report gate-f1`
publica el barrido de la puerta F1→F2 con su veredicto.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path
from typing import Any

from tribal import __version__
from tribal.config import MAX_INDIVIDUOS, MIN_INDIVIDUOS, SimConfig
from tribal.gate_f1 import (
    MAX_INDIVIDUOS_BARRIDO,
    SEMILLAS_PUERTA,
    TICKS_PUERTA,
    medir_barrido,
    parsear_semillas,
)
from tribal.sim import MS_FRAME
from tribal.sim import run as run_sim

#: Ticks por defecto de `report culture`: con 600 la tribu ya comió y el árbol
#: tiene nodos. La corrida es headless, corta y determinista — ver `_report`.
TICKS_INFORME = 600


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tribal", description="La Tribu.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    sub = parser.add_subparsers(dest="command", required=True)
    hello = sub.add_parser("hello", help="Comando de ejemplo: saluda y sale.")
    hello.add_argument("--name", default="mundo", help="A quién saludar.")

    run = sub.add_parser("run", help="Ejecuta la simulación de Fase 0.")
    run.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Semilla del mundo; manda sobre la del --config (default 42).",
    )
    run.add_argument(
        "--individuos",
        type=int,
        default=None,
        help=f"Población inicial, {MIN_INDIVIDUOS}-{MAX_INDIVIDUOS}; manda sobre el --config "
        "(default 12).",
    )
    run.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Fichero JSON con los parámetros de la partida (ver docs/config-ejemplo.json).",
    )
    run.add_argument("--ticks", type=int, default=0, help="Ticks a simular; 0 = sin límite.")
    run.add_argument(
        "--crisis",
        action="store_true",
        help="Sequía (concepto §13): menos agua y bayas, más sed y más intentos divergentes.",
    )
    run.add_argument("--headless", action="store_true", help="Sin ventana.")
    run.add_argument("--json", action="store_true", help="Resumen como un único objeto JSON.")
    run.add_argument("--benchmark", action="store_true", help="Falla si no cabe en 16.67 ms/tick.")

    report = sub.add_parser("report", help="Informes de la tribu, sin abrir ventana.")
    informes = report.add_subparsers(dest="report", required=True)
    culture = informes.add_parser(
        "culture",
        help="Árbol de conocimiento: nodos, aristas y porcentaje fuera del árbol.",
        description=(
            "Corre una partida headless corta (--ticks, 600 por defecto) y resume el "
            "grafo de cultura de esa corrida. Todavía no hay partida persistida: "
            "cuando exista `tribu.db`, este comando leerá el grafo guardado en vez "
            "de simular."
        ),
    )
    culture.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Semilla del mundo; manda sobre la del --config (default 42).",
    )
    culture.add_argument(
        "--ticks",
        type=int,
        default=TICKS_INFORME,
        help=f"Ticks a simular antes del informe (default {TICKS_INFORME}).",
    )
    culture.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Fichero JSON con los parámetros de la partida (ver docs/config-ejemplo.json).",
    )
    culture.add_argument(
        "--crisis",
        action="store_true",
        help="Simula la crisis (sequía) antes de resumir el grafo.",
    )
    culture.add_argument("--json", action="store_true", help="Informe como un único objeto JSON.")

    gate = informes.add_parser(
        "gate-f1",
        help="Barrido de la puerta F1→F2: proporción divergente en calma y en crisis.",
        description=(
            "Corre las dos ramas (calma y crisis, la misma configuración salvo `crisis`) "
            "sobre las semillas pedidas y publica div%, media y sigma, nacidos, nodos "
            "nuevos, población y extinciones, con un veredicto booleano por criterio. "
            "Los valores por defecto son el barrido que publica la puerta: 1-10 x 8000."
        ),
    )
    gate.add_argument(
        "--seeds",
        default=f"{SEMILLAS_PUERTA[0]}-{SEMILLAS_PUERTA[-1]}",
        help=f"Semillas a correr: `1-10`, `1,3,5` o una mezcla (default {SEMILLAS_PUERTA[0]}-{SEMILLAS_PUERTA[-1]}).",
    )
    gate.add_argument(
        "--ticks",
        type=int,
        default=TICKS_PUERTA,
        help=f"Ticks por corrida (default {TICKS_PUERTA}).",
    )
    gate.add_argument(
        "--individuos",
        type=int,
        default=12,
        help=(
            f"Población inicial del barrido, {MIN_INDIVIDUOS}-{MAX_INDIVIDUOS_BARRIDO} "
            "(el juego sigue 8-15; default 12)."
        ),
    )
    gate.add_argument("--json", action="store_true", help="Barrido como un único objeto JSON.")

    return parser


def hello(name: str) -> str:
    return f"Hola, {name}."


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "hello":
        print(hello(args.name))
        return 0
    if args.command == "run":
        return _run(args)
    if args.command == "report":
        if args.report == "gate-f1":
            return _report_gate_f1(args)
        return _report(args)
    return 1


def _run(args: argparse.Namespace) -> int:
    try:
        base = SimConfig.desde_json(args.config) if args.config else SimConfig()
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    # Precedencia: CLI > fichero > defaults.
    individuos = base.individuos if args.individuos is None else args.individuos
    seed = base.seed if args.seed is None else args.seed

    if not MIN_INDIVIDUOS <= individuos <= MAX_INDIVIDUOS:
        print(
            f"error: --individuos debe estar entre {MIN_INDIVIDUOS} y {MAX_INDIVIDUOS} "
            f"(recibido {individuos})",
            file=sys.stderr,
        )
        return 2
    if args.headless and args.ticks <= 0:
        print("error: --headless necesita --ticks mayor que 0", file=sys.stderr)
        return 2

    config = replace(base, seed=seed, individuos=individuos, crisis=base.crisis or args.crisis)
    simulacion = run_sim(args.ticks, seed, args.headless, individuos=individuos, config=config)
    resumen = simulacion.resumen()

    if args.json:
        print(json.dumps(resumen, ensure_ascii=True))
    else:
        print(_texto_resumen(resumen))

    if args.benchmark:
        return _benchmark(simulacion.ms_tick_medio)
    return 0


def _report(args: argparse.Namespace) -> int:
    """`report culture`: grafo de una corrida headless determinista.

    En Fase 1 la cultura aún no se persiste, así que el informe sale de simular
    `--ticks` ticks con la semilla y la config pedidas. Mismo `--seed/--ticks`
    → mismo informe.
    """
    try:
        base = SimConfig.desde_json(args.config) if args.config else SimConfig()
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    seed = base.seed if args.seed is None else args.seed
    if args.ticks <= 0:
        print("error: --ticks debe ser mayor que 0", file=sys.stderr)
        return 2

    config = replace(base, seed=seed, crisis=base.crisis or args.crisis)
    simulacion = run_sim(
        args.ticks, seed, headless=True, individuos=config.individuos, config=config
    )
    informe: dict[str, Any] = {
        "seed": seed,
        "ticks": args.ticks,
        "crisis": config.crisis,
        **simulacion.grafo.a_json(),
    }
    if args.json:
        print(json.dumps(informe, ensure_ascii=True))
    else:
        print(_texto_cultura(informe))
    return 0


def _report_gate_f1(args: argparse.Namespace) -> int:
    """`report gate-f1`: los dos brazos sobre las mismas semillas y su veredicto.

    No es un test: es la herramienta con la que el barrido se publica entero.
    Misma semilla y misma config salvo `crisis`; el barrido no elige semillas.
    """
    try:
        semillas = parsear_semillas(args.seeds)
        barrido = medir_barrido(semillas, ticks=args.ticks, individuos=args.individuos)
    except (ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(barrido.a_json(), ensure_ascii=True))
    else:
        print(barrido.texto())
    return 0


def _texto_cultura(informe: dict[str, Any]) -> str:
    lineas = [
        f"seed {informe['seed']}  ticks {informe['ticks']}",
        f"nodos {len(informe['nodos'])}  aristas {len(informe['aristas'])}  "
        f"pct_fuera_arbol {informe['pct_fuera_arbol']}  nivel_max {informe['nivel_max']}",
    ]
    lineas.extend(
        f"  {nodo['rama']:<9} {nodo['nivel']}  {nodo['titulo']:<20} "
        f"({nodo['origen']}, autor {nodo['autor']}, tick {nodo['tick']})"
        for nodo in informe["nodos"]
    )
    return "\n".join(lineas)


def _benchmark(ms_tick_medio: float) -> int:
    """Presupuesto de frame. Va a stderr: no contamina la salida JSON ni la del resumen."""
    if ms_tick_medio >= MS_FRAME:
        print(
            f"benchmark: {ms_tick_medio:.2f} ms/tick, por encima de {MS_FRAME} ms", file=sys.stderr
        )
        return 1
    print(f"benchmark: {ms_tick_medio:.2f} ms/tick, cabe en {MS_FRAME} ms", file=sys.stderr)
    return 0


def _texto_resumen(resumen: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"seed {resumen['seed']}  ticks {resumen['ticks']}  "
            f"poblacion {resumen['poblacion_inicial']} -> {resumen['poblacion_final']}",
            f"muertes {resumen['muertes']}  nacimientos {resumen['nacimientos']}  "
            f"individuos movidos {resumen['individuos_movidos']}",
            f"depredadores {resumen['depredador']['activos']}  "
            f"ataques {resumen['depredador']['ataques']}  "
            f"agrupamiento max {resumen['agrupamiento_max']}  huidas {resumen['huidas']}",
            f"media energia {resumen['media_energia']}  media sed {resumen['media_sed']}",
            f"estacion {resumen['estacion'] or 'sin estacion'}  "
            f"parches {len(resumen['parches'])}  "
            f"migraciones {resumen['migraciones']}",
        ]
    )


if __name__ == "__main__":
    sys.exit(main())
