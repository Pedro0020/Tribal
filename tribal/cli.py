"""
tribal.cli — punto de entrada del proyecto: `python -m tribal` o `make run`.

argparse de la stdlib. `hello` se mantiene como humo del renombrado; `run`
arranca la simulación en ventana o en modo headless, `report culture` resume
el árbol de conocimiento de una corrida headless corta, `report diary` publica
los últimos hitos narrados y `report gate-f1` / `report gate-f2` publican los
barridos de las puertas F1→F2 y F2→F3 con su veredicto.
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
from tribal.gate_f2 import SEMILLAS_PUERTA_F2, TICKS_PUERTA_F2, medir_puerta
from tribal.llm.cliente import (
    ENDPOINT_POR_DEFECTO,
    MODELO_POR_DEFECTO,
    TIMEOUT_POR_DEFECTO,
    ClienteLLM,
    backend_stub,
)
from tribal.llm.cola import MAX_EN_VUELO_POR_DEFECTO, ColaLLM
from tribal.llm.embeddings import embedder_por_defecto
from tribal.llm.eval import ESCENARIOS_POR_DEFECTO, backend_competente, escenarios, evaluar
from tribal.sim import MS_FRAME, run_muestreado
from tribal.sim import run as run_sim
from tribal.store.repositorio import BaseInvalida, Repositorio

#: Ticks por defecto de `report culture`: con 600 la tribu ya comió y el árbol
#: tiene nodos. La corrida es headless, corta y determinista — ver `_report`.
TICKS_INFORME = 600
#: Cada cuántos ticks muestrea `report telemetry`: 10 filas para 600 ticks.
INTERVALO_TELEMETRIA = 60
#: Entradas de diario que publica `report diary` si no se pide otra cosa.
DIARIO_ULTIMAS = 5


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
    run.add_argument(
        "--db",
        type=Path,
        default=None,
        help="Escribe la partida en esa base SQLite (se vuelca al cerrar y cada "
        "`ticks_guardado` ticks).",
    )
    run.add_argument("--benchmark", action="store_true", help="Falla si no cabe en 16.67 ms/tick.")
    run.add_argument(
        "--llm",
        choices=("off", "stub", "http"),
        default="off",
        help="Capa LLM: `off` (instinto, default), `stub` (backend falso determinista) "
        "o `http` (Ollama en 127.0.0.1:11434).",
    )
    run.add_argument(
        "--llm-sincrono",
        action="store_true",
        help="Sin hilo: la petición se resuelve en el tick. Determinista; para tests.",
    )
    run.add_argument(
        "--llm-max-en-vuelo",
        type=int,
        default=MAX_EN_VUELO_POR_DEFECTO,
        help=f"Peticiones aceptadas sin respuesta (default {MAX_EN_VUELO_POR_DEFECTO}).",
    )

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

    telemetria = informes.add_parser(
        "telemetry",
        help="Telemetría por intervalo: población, temperamentos, grafo y medias.",
        description=(
            "Corre una partida headless y toma una muestra cada --intervalo ticks "
            "(población, divergentes, conformistas, neutros, nodos, aristas y medias "
            "de energía y sed). Con --llm añade a cada muestra peticiones, aplicadas, "
            "descartadas, fallos y latencia media del LLM. Determinista: mismo seed, "
            "ticks e intervalo, mismas muestras. Todavía no lee una partida persistida."
        ),
    )
    telemetria.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Semilla del mundo; manda sobre la del --config (default 42).",
    )
    telemetria.add_argument(
        "--ticks",
        type=int,
        default=TICKS_INFORME,
        help=f"Ticks a simular (default {TICKS_INFORME}).",
    )
    telemetria.add_argument(
        "--intervalo",
        type=int,
        default=INTERVALO_TELEMETRIA,
        help=f"Ticks entre muestras (default {INTERVALO_TELEMETRIA}).",
    )
    telemetria.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Fichero JSON con los parámetros de la partida (ver docs/config-ejemplo.json).",
    )
    telemetria.add_argument(
        "--crisis",
        action="store_true",
        help="Simula la crisis (sequía) durante la toma de muestras.",
    )
    telemetria.add_argument(
        "--llm",
        choices=("off", "stub", "http"),
        default="off",
        help="Capa LLM cuyos contadores se muestrean: `off` (default), `stub` o `http`.",
    )
    telemetria.add_argument(
        "--llm-sincrono",
        action="store_true",
        help="Sin hilo: la petición se resuelve en el tick. Determinista; para tests.",
    )
    telemetria.add_argument(
        "--json", action="store_true", help="Muestras como un único objeto JSON."
    )

    diario = informes.add_parser(
        "diary",
        help="Diario: los últimos hitos de una corrida y su frase, si la hubo.",
        description=(
            "Corre una partida headless (--ticks, 600 por defecto) y publica las "
            "últimas --last entradas del diario: tick, tipo, individuo, texto y si "
            "la frase la puso el LLM. Sin capa LLM el hito se registra igual, sin "
            "narración; `--llm stub --llm-sincrono` es el modo reproducible."
        ),
    )
    diario.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Semilla del mundo; manda sobre la del --config (default 42).",
    )
    diario.add_argument(
        "--ticks",
        type=int,
        default=TICKS_INFORME,
        help=f"Ticks a simular (default {TICKS_INFORME}).",
    )
    diario.add_argument(
        "--last",
        type=int,
        default=DIARIO_ULTIMAS,
        help=f"Entradas más recientes a mostrar (default {DIARIO_ULTIMAS}).",
    )
    diario.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Fichero JSON con los parámetros de la partida (ver docs/config-ejemplo.json).",
    )
    diario.add_argument(
        "--crisis",
        action="store_true",
        help="Simula la crisis (sequía) antes de leer el diario.",
    )
    diario.add_argument(
        "--llm",
        choices=("off", "stub", "http"),
        default="off",
        help="Capa LLM que narra los hitos: `off` (default), `stub` o `http`.",
    )
    diario.add_argument(
        "--llm-sincrono",
        action="store_true",
        help="Sin hilo: la frase se resuelve en el tick. Determinista; para tests.",
    )
    diario.add_argument("--json", action="store_true", help="Diario como un único objeto JSON.")

    base_datos = informes.add_parser(
        "db",
        help="Partida persistida: población, nodos por origen, aristas, diario y telemetría.",
        description=(
            "Abre una base escrita por `run --db` y cuenta lo que hay dentro: "
            "individuos vivos, nodos por origen, aristas, diario, telemetría y "
            "recursos. No simula ni modifica nada; sale con 2 si el fichero no "
            "es una partida SQLite válida."
        ),
    )
    base_datos.add_argument("--db", type=Path, required=True, help="Base SQLite de la partida.")
    base_datos.add_argument(
        "--json", action="store_true", help="Informe como un único objeto JSON."
    )

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

    gate_f2 = informes.add_parser(
        "gate-f2",
        help="Puerta F2→F3: nodos fuera del árbol propuestos por el LLM y narración.",
        description=(
            "Corre una partida por semilla con un backend guionizado determinista y "
            "publica nodos totales y por origen, nodos fuera del árbol con autor y "
            "tick, porcentaje fuera del árbol, narraciones por individuo, concentración "
            "top-3 y el veredicto. Los valores por defecto son los de la puerta: "
            f"{SEMILLAS_PUERTA_F2[0]}-{SEMILLAS_PUERTA_F2[-1]} x {TICKS_PUERTA_F2} en crisis."
        ),
    )
    gate_f2.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Una sola semilla; manda sobre --seeds.",
    )
    gate_f2.add_argument(
        "--seeds",
        default=f"{SEMILLAS_PUERTA_F2[0]}-{SEMILLAS_PUERTA_F2[-1]}",
        help=(
            "Semillas a correr: `1-5`, `1,3,5` o una mezcla "
            f"(default {SEMILLAS_PUERTA_F2[0]}-{SEMILLAS_PUERTA_F2[-1]})."
        ),
    )
    gate_f2.add_argument(
        "--ticks",
        type=int,
        default=TICKS_PUERTA_F2,
        help=f"Ticks por corrida (default {TICKS_PUERTA_F2}).",
    )
    gate_f2.add_argument(
        "--crisis",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Crisis (sequía) antes de medir; `--no-crisis` la apaga (default crisis).",
    )
    gate_f2.add_argument(
        "--llm",
        choices=("off", "stub", "http", "script"),
        default="script",
        help="Capa LLM de la puerta: `script` (guion determinista, default), `stub`, "
        "`http` u `off`.",
    )
    gate_f2.add_argument(
        "--llm-sincrono",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Resuelve la petición en el tick (default); `--no-llm-sincrono` usa la cola "
        "asíncrona.",
    )
    gate_f2.add_argument(
        "--json", action="store_true", help="Tabla y veredicto como un único objeto JSON."
    )

    llm = sub.add_parser("llm", help="Capa LLM local (Ollama).")
    llm_sub = llm.add_subparsers(dest="llm", required=True)
    selfcheck = llm_sub.add_parser(
        "selfcheck",
        help="Comprueba si el servicio y el modelo responden.",
        description=(
            "Hace `GET /api/tags` al endpoint de Ollama y publica disponible, "
            "latencia y error. Si no hay servicio no es un fallo del comando: "
            "la tribu funciona sin LLM por diseño."
        ),
    )
    selfcheck.add_argument(
        "--endpoint",
        default=ENDPOINT_POR_DEFECTO,
        help=f"Endpoint de Ollama (default {ENDPOINT_POR_DEFECTO}).",
    )
    selfcheck.add_argument(
        "--modelo",
        default=MODELO_POR_DEFECTO,
        help=f"Identificador del modelo (default {MODELO_POR_DEFECTO}).",
    )
    selfcheck.add_argument(
        "--timeout",
        type=float,
        default=TIMEOUT_POR_DEFECTO,
        help=f"Timeout en segundos (default {TIMEOUT_POR_DEFECTO}).",
    )
    selfcheck.add_argument("--json", action="store_true", help="Informe como un único objeto JSON.")

    evaluar_llm = llm_sub.add_parser(
        "eval",
        help="Acierto del contrato candidatas → elige → valida en escenarios simples.",
        description=(
            "Corre escenarios con una acción claramente correcta y publica el "
            "acierto. `--backend simulado` (default) usa un backend competente y "
            "prueba el contrato, no el modelo; `--backend http` mide el modelo "
            "real contra Ollama y no revienta si el servicio no está."
        ),
    )
    evaluar_llm.add_argument(
        "--backend",
        choices=("simulado", "http"),
        default="simulado",
        help="`simulado` (contrato, CI) o `http` (Ollama real).",
    )
    evaluar_llm.add_argument(
        "--escenarios",
        type=int,
        default=ESCENARIOS_POR_DEFECTO,
        help=f"Cuántos escenarios correr (default {ESCENARIOS_POR_DEFECTO}).",
    )
    evaluar_llm.add_argument(
        "--endpoint",
        default=ENDPOINT_POR_DEFECTO,
        help=f"Endpoint de Ollama para `--backend http` (default {ENDPOINT_POR_DEFECTO}).",
    )
    evaluar_llm.add_argument(
        "--modelo",
        default=MODELO_POR_DEFECTO,
        help=f"Identificador del modelo (default {MODELO_POR_DEFECTO}).",
    )
    evaluar_llm.add_argument(
        "--timeout",
        type=float,
        default=TIMEOUT_POR_DEFECTO,
        help=f"Timeout en segundos (default {TIMEOUT_POR_DEFECTO}).",
    )
    evaluar_llm.add_argument("--json", action="store_true", help="Informe como objeto JSON.")

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
        if args.report == "gate-f2":
            return _report_gate_f2(args)
        if args.report == "telemetry":
            return _report_telemetry(args)
        if args.report == "diary":
            return _report_diary(args)
        if args.report == "db":
            return _report_db(args)
        return _report(args)
    if args.command == "llm":
        if args.llm == "eval":
            return _llm_eval(args)
        return _llm_selfcheck(args)
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
    if args.llm_max_en_vuelo < 1:
        print("error: --llm-max-en-vuelo debe ser mayor que 0", file=sys.stderr)
        return 2
    if args.llm_sincrono and args.llm == "http":
        print(
            "error: --llm-sincrono solo vale con --llm stub: resolver http en el tick "
            "congelaría el bucle hasta el timeout",
            file=sys.stderr,
        )
        return 2

    cola = None
    if args.llm != "off":
        cliente = ClienteLLM(transporte=backend_stub()) if args.llm == "stub" else ClienteLLM()
        cola = ColaLLM(
            cliente,
            max_en_vuelo=args.llm_max_en_vuelo,
            sincrona=args.llm_sincrono,
        )

    config = replace(base, seed=seed, individuos=individuos, crisis=base.crisis or args.crisis)
    try:
        simulacion = run_sim(
            args.ticks,
            seed,
            args.headless,
            individuos=individuos,
            config=config,
            cola=cola,
            db=args.db,
        )
    except BaseInvalida as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if cola is not None and not cola.cerrar():
        print(
            "warning: la capa LLM no cerró limpia: el hilo tribal-llm sigue vivo",
            file=sys.stderr,
        )
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
    grafo = simulacion.grafo.a_json()
    informe: dict[str, Any] = {
        "seed": seed,
        "ticks": args.ticks,
        "crisis": config.crisis,
        **grafo,
        #: Nodos que no son escalones del árbol, con su origen y su autor. El KPI
        #: `pct_fuera_arbol` solo cuenta `combinacion` e `interaccion`; `llm` se
        #: publica aquí porque también nació fuera del árbol (F2-006).
        "fuera_arbol": [
            nodo
            for nodo in grafo["nodos"]
            if nodo["origen"] in ("combinacion", "interaccion", "llm")
        ],
    }
    if args.json:
        print(json.dumps(informe, ensure_ascii=True))
    else:
        print(_texto_cultura(informe))
    return 0


def _report_telemetry(args: argparse.Namespace) -> int:
    """`report telemetry`: una fila por intervalo, no por tick.

    La corrida es la misma que la de `run --headless` con esos `--seed/--ticks`
    y esa `--config`; la última muestra es el estado final, así que coincide con
    el resumen de esa partida.
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
    if args.intervalo <= 0:
        print("error: --intervalo debe ser mayor que 0", file=sys.stderr)
        return 2
    if args.llm_sincrono and args.llm == "http":
        print(
            "error: --llm-sincrono solo vale con --llm stub: resolver http en el tick "
            "congelaría el bucle hasta el timeout",
            file=sys.stderr,
        )
        return 2

    cola = None
    if args.llm != "off":
        cliente = ClienteLLM(transporte=backend_stub()) if args.llm == "stub" else ClienteLLM()
        cola = ColaLLM(cliente, sincrona=args.llm_sincrono)

    config = replace(base, seed=seed, crisis=base.crisis or args.crisis)
    _, muestras = run_muestreado(
        args.ticks,
        seed,
        args.intervalo,
        individuos=config.individuos,
        config=config,
        cola=cola,
    )
    informe: dict[str, Any] = {
        "seed": seed,
        "ticks": args.ticks,
        "intervalo": args.intervalo,
        "crisis": config.crisis,
        "llm": args.llm,
        "muestras": muestras,
    }
    if args.json:
        print(json.dumps(informe, ensure_ascii=True))
    else:
        print(_texto_telemetria(informe))
    return 0


def _report_diary(args: argparse.Namespace) -> int:
    """`report diary`: los hitos de una corrida y la frase que les puso el LLM.

    La corrida es la misma que la de `run --headless`. Sin `--llm` no hay
    narraciones, pero los hitos se registran igual y salen con `narrada=false`.
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
    if args.last <= 0:
        print("error: --last debe ser mayor que 0", file=sys.stderr)
        return 2
    if args.llm_sincrono and args.llm == "http":
        print(
            "error: --llm-sincrono solo vale con --llm stub: resolver http en el tick "
            "congelaría el bucle hasta el timeout",
            file=sys.stderr,
        )
        return 2

    cola = None
    if args.llm != "off":
        cliente = ClienteLLM(transporte=backend_stub()) if args.llm == "stub" else ClienteLLM()
        cola = ColaLLM(cliente, sincrona=args.llm_sincrono)

    config = replace(base, seed=seed, crisis=base.crisis or args.crisis)
    try:
        simulacion = run_sim(
            args.ticks,
            seed,
            headless=True,
            individuos=config.individuos,
            config=config,
            cola=cola,
        )
    finally:
        if cola is not None:
            cola.cerrar()

    informe: dict[str, Any] = {
        "seed": seed,
        "ticks": args.ticks,
        "crisis": config.crisis,
        "llm": args.llm,
        **simulacion.diario.a_json(),
        "ultimas": [entrada.a_json() for entrada in simulacion.diario.ultimas(args.last)],
    }
    if args.json:
        print(json.dumps(informe, ensure_ascii=True))
    else:
        print(_texto_diario(informe))
    return 0


def _report_db(args: argparse.Namespace) -> int:
    """`report db`: recuentos de una partida escrita con `run --db`.

    No simula: abre la base en modo solo lectura lógica (`crear=False`, que
    valida las tablas sin ejecutar DDL) y publica lo que hay guardado. Un
    fichero que no es SQLite, o una base sin las tablas de la tribu, sale con 2.
    """
    if not args.db.exists():
        print(f"error: no existe la base {args.db}", file=sys.stderr)
        return 2
    try:
        repositorio = Repositorio(args.db, crear=False)
    except BaseInvalida as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    try:
        informe: dict[str, Any] = {"db": str(args.db), **repositorio.instantanea()}
    finally:
        repositorio.cerrar()

    if args.json:
        print(json.dumps(informe, ensure_ascii=True))
    else:
        print(_texto_db(informe))
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


def _report_gate_f2(args: argparse.Namespace) -> int:
    """`report gate-f2`: nodos fuera del árbol y concentración de la narración.

    No es un test: es la herramienta con la que la puerta F2→F3 se publica
    entera. El backend `script` es determinista y no toca la red; `--llm-sincrono`
    (default) hace reproducible hasta el orden de las respuestas.
    """
    if args.llm_sincrono and args.llm == "http":
        print(
            "error: --llm-sincrono no vale con --llm http: resolver http en el tick "
            "congelaría el bucle hasta el timeout",
            file=sys.stderr,
        )
        return 2
    try:
        semillas = (args.seed,) if args.seed is not None else parsear_semillas(args.seeds)
        barrido = medir_puerta(
            semillas,
            ticks=args.ticks,
            crisis=args.crisis,
            llm=args.llm,
            sincrono=args.llm_sincrono,
        )
    except (ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(barrido.a_json(), ensure_ascii=True))
    else:
        print(barrido.texto())
    return 0


def _llm_selfcheck(args: argparse.Namespace) -> int:
    """`llm selfcheck`: informa del servicio sin convertir su ausencia en fallo."""
    cliente = ClienteLLM(endpoint=args.endpoint, modelo=args.modelo, timeout=args.timeout)
    servicio = cliente.disponible()
    embeddings = embedder_por_defecto()
    informe = {
        "disponible": servicio.disponible,
        "endpoint": cliente.endpoint,
        "modelo": cliente.modelo,
        "modelo_presente": servicio.modelo_presente,
        "latencia_ms": servicio.latencia_ms,
        "error": servicio.error,
        #: Backend determinista en CPU: misma dimensión en cualquier máquina.
        "embeddings": {
            "backend": "hashing",
            "usa_gpu": embeddings.usa_gpu,
            "dim": embeddings.dim,
        },
    }
    if args.json:
        print(json.dumps(informe, ensure_ascii=True))
    else:
        estado = "disponible" if servicio.disponible else "no disponible"
        modelo = (
            ""
            if servicio.modelo_presente is None
            else (" (modelo presente)" if servicio.modelo_presente else " (modelo ausente)")
        )
        latencia = "" if servicio.latencia_ms is None else f" ({servicio.latencia_ms} ms)"
        error = "" if servicio.error is None else f": {servicio.error}"
        print(f"{cliente.modelo} en {cliente.endpoint}: {estado}{modelo}{latencia}{error}")
    return 0


def _llm_eval(args: argparse.Namespace) -> int:
    """`llm eval`: acierto del contrato, no de la calidad del modelo."""
    if args.escenarios <= 0:
        print("error: --escenarios debe ser mayor que 0", file=sys.stderr)
        return 2
    if args.backend == "http":
        cliente = ClienteLLM(endpoint=args.endpoint, modelo=args.modelo, timeout=args.timeout)
    else:
        cliente = ClienteLLM(transporte=backend_competente())

    casos = escenarios()
    if args.escenarios > len(casos):
        print(
            f"warning: la batería tiene {len(casos)} escenarios; se ejecutan {len(casos)}",
            file=sys.stderr,
        )
    informe = evaluar(cliente, casos[: args.escenarios])
    informe["backend"] = args.backend

    if args.json:
        print(json.dumps(informe, ensure_ascii=True))
    else:
        print(
            f"backend {informe['backend']}  escenarios {informe['escenarios']}  "
            f"aciertos {informe['aciertos']}  acierto {informe['acierto'] * 100:.1f}%  "
            f"corregidas {informe['corregidas']}  sin_decision {informe['sin_decision']}"
        )
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


def _texto_telemetria(informe: dict[str, Any]) -> str:
    con_llm = any("llm" in muestra for muestra in informe["muestras"])
    cabecera_llm = "  pet  apl  des  fal  lat" if con_llm else ""
    lineas = [
        f"seed {informe['seed']}  ticks {informe['ticks']}  "
        f"intervalo {informe['intervalo']}  crisis {informe['crisis']}  llm {informe['llm']}",
        f"  tick  pob  div  conf  neut  nodos  aristas  energia  sed{cabecera_llm}",
    ]
    for muestra in informe["muestras"]:
        linea = (
            f"  {muestra['tick']:>4}  {muestra['poblacion']:>3}  "
            f"{muestra['divergentes']:>3}  {muestra['conformistas']:>4}  "
            f"{muestra['neutros']:>4}  {muestra['nodos']:>5}  "
            f"{muestra['aristas']:>7}  {muestra['media_energia']:>7}  {muestra['media_sed']:>4}"
        )
        if "llm" in muestra:
            llm = muestra["llm"]
            linea += (
                f"  {llm['peticiones']:>3}  {llm['aplicadas']:>3}  {llm['descartadas']:>3}  "
                f"{llm['fallos']:>3}  {llm['latencia_ms_media']:>3}"
            )
        lineas.append(linea)
    return "\n".join(lineas)


def _texto_diario(informe: dict[str, Any]) -> str:
    lineas = [
        f"seed {informe['seed']}  ticks {informe['ticks']}  llm {informe['llm']}  "
        f"entradas {informe['entradas']}  narradas {informe['narradas']}  "
        f"dialogos {informe['dialogos']}"
    ]
    for entrada in informe["ultimas"]:
        quien = entrada["individuo_id"] if entrada["individuo_id"] is not None else "-"
        texto = entrada["texto"] or "(sin narracion)"
        lineas.append(f"  {entrada['tick']:>5}  {entrada['tipo']:<18} ind {quien:<3} {texto}")
    return "\n".join(lineas)


def _texto_db(informe: dict[str, Any]) -> str:
    origenes = "  ".join(
        f"{origen} {cuenta}" for origen, cuenta in informe["nodos_por_origen"].items()
    )
    return "\n".join(
        [
            f"seed {informe['seed']}  tick {informe['tick']}  "
            f"poblacion {informe['poblacion']}  estacion {informe['estacion'] or 'sin estacion'}",
            f"nodos {informe['nodos']}  aristas {informe['aristas']}  {origenes}",
            f"diario {informe['diario']}  telemetria {informe['telemetria']}  "
            f"recursos {informe['recursos']}  recuerdos {informe['recuerdos']}",
        ]
    )


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
    lineas = [
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
    if "llm" in resumen:
        llm = resumen["llm"]
        lineas.append(
            f"llm peticiones {llm['peticiones']}  aplicadas {llm['aplicadas']}  "
            f"descartadas {llm['descartadas']}  fallos {llm['fallos']}"
        )
    diario = resumen.get("diario")
    if diario and diario["entradas"]:
        lineas.append(
            f"diario entradas {diario['entradas']}  narradas {diario['narradas']}  "
            f"dialogos {diario['dialogos']}"
        )
        lineas.extend(
            f"  {entrada['tick']:>5}  {entrada['tipo']:<18} {entrada['texto'] or '(sin narracion)'}"
            for entrada in diario["ultimas"]
        )
    return "\n".join(lineas)


if __name__ == "__main__":
    sys.exit(main())
