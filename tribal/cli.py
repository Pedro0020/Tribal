"""
tribal.cli — punto de entrada del proyecto: `python -m tribal` o `make run`.

argparse de la stdlib. `hello` se mantiene como humo del renombrado; `run`
arranca la simulación de Fase 0 en ventana o en modo headless.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

from tribal import __version__
from tribal.sim import MS_FRAME
from tribal.sim import run as run_sim

#: Rango jugable de Fase 0: por debajo no hay tribu, por encima no hay frame.
MIN_INDIVIDUOS = 8
MAX_INDIVIDUOS = 15


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tribal", description="La Tribu.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    sub = parser.add_subparsers(dest="command", required=True)
    hello = sub.add_parser("hello", help="Comando de ejemplo: saluda y sale.")
    hello.add_argument("--name", default="mundo", help="A quién saludar.")

    run = sub.add_parser("run", help="Ejecuta la simulación de Fase 0.")
    run.add_argument("--seed", type=int, default=42, help="Semilla del mundo (default 42).")
    run.add_argument(
        "--individuos",
        type=int,
        default=12,
        help=f"Población inicial, {MIN_INDIVIDUOS}-{MAX_INDIVIDUOS} (default 12).",
    )
    run.add_argument("--ticks", type=int, default=0, help="Ticks a simular; 0 = sin límite.")
    run.add_argument("--headless", action="store_true", help="Sin ventana.")
    run.add_argument("--json", action="store_true", help="Resumen como un único objeto JSON.")
    run.add_argument("--benchmark", action="store_true", help="Falla si no cabe en 16.67 ms/tick.")

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
    return 1


def _run(args: argparse.Namespace) -> int:
    if not MIN_INDIVIDUOS <= args.individuos <= MAX_INDIVIDUOS:
        print(
            f"error: --individuos debe estar entre {MIN_INDIVIDUOS} y {MAX_INDIVIDUOS} "
            f"(recibido {args.individuos})",
            file=sys.stderr,
        )
        return 2
    if args.headless and args.ticks <= 0:
        print("error: --headless necesita --ticks mayor que 0", file=sys.stderr)
        return 2

    simulacion = run_sim(args.ticks, args.seed, args.headless, individuos=args.individuos)
    resumen = simulacion.resumen()

    if args.json:
        print(json.dumps(resumen, ensure_ascii=True))
    else:
        print(_texto_resumen(resumen))

    if args.benchmark:
        return _benchmark(simulacion.ms_tick_medio)
    return 0


def _benchmark(ms_tick_medio: float) -> int:
    """Presupuesto de frame. Va a stderr: no contamina la salida JSON ni la del resumen."""
    if ms_tick_medio >= MS_FRAME:
        print(
            f"benchmark: {ms_tick_medio:.2f} ms/tick, por encima de {MS_FRAME} ms", file=sys.stderr
        )
        return 1
    print(f"benchmark: {ms_tick_medio:.2f} ms/tick, cabe en {MS_FRAME} ms", file=sys.stderr)
    return 0


def _texto_resumen(resumen: dict[str, int | float]) -> str:
    return "\n".join(
        [
            f"seed {resumen['seed']}  ticks {resumen['ticks']}  "
            f"poblacion {resumen['poblacion_inicial']} -> {resumen['poblacion_final']}",
            f"muertes {resumen['muertes']}  nacimientos {resumen['nacimientos']}  "
            f"individuos movidos {resumen['individuos_movidos']}",
            f"media energia {resumen['media_energia']}  media sed {resumen['media_sed']}",
        ]
    )


if __name__ == "__main__":
    sys.exit(main())
