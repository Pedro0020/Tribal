# explorer · CORE-001

- **Fecha:** 2026-11-18
- **Veredicto:** ok

# CORE-001 - recon (explorer, 2026-11-18, verdict ok)

## Respuesta

1. `tribal/` tiene 4 ficheros: cli.py, paths.py, __init__.py, __main__.py. Solo hay un
   subcomando, `hello`. argparse con subparsers required=True; main() devuelve int.
2. pygame-ce NO esta instalado en ningun interprete de esta maquina. Solo hay un wheel
   desempaquetado en la cache de uv (pygame_ce-2.5.8). Probe con `uv run --with
   pygame-ce==2.5.8 --no-project`: funciona todo en headless dummy, sin warnings.
   Fuente por defecto = freesansbold.ttf incluida en el wheel (no depende de Windows).
   60fps de sobra: 3600 tiles 8x8 = 2.2 ms/frame.
3. Tests: pytest, `from __future__ import annotations`, type hints en todo, nombres en
   castellano, capsys tipado, tmp_path usado. Marker `slow` declarado pero sin uso.
4. La puerta corre `uv run pytest tests/ -q --no-header` (init.sh:274); `harness gate`
   ejecuta `bash init.sh --json` (harness_agent.py:416), o sea lo mismo. No existe
   conftest.py. Sin pygame declarado, cualquier test que lo importe falla en coleccion.
5. Anadir subcomando = un `sub.add_parser(...)` mas un branch en main(). `hello` y
   test_cli.py no se rompen.
6. No hay assets ni loader. Recomendado: Surfaces 8x8 generadas en codigo y cacheadas.
7. Riesgos Windows: DPI no gestionado por pygame (borroso, no crash), consola cp1252
   (un `->` en un print revienta), drift de version 0.1.1 vs 0.1.3, `run` no existe.

## Donde esta

- tribal/cli.py:20-36 build_parser (subparsers required, solo hello); :38-44 main
- tribal/cli.py:9-13 docstring: argparse de stdlib, hello es humo del renombrado
- tribal/__main__.py:1-8 sys.exit(main())
- tribal/paths.py:22-31 ROOT_DIR / PACKAGE_DIR / TESTS_DIR / ... ; ensure_dir:34
- tribal/__init__.py:14 __version__ = 0.1.1  (pyproject:3 y README:4 dicen 0.1.3)
- pyproject.toml:15 dependencies = [] ; :42-43 script tribal = tribal.cli:main
- pyproject.toml:74-79 testpaths = [tests, agents/tests]; markers = slow
- tests/test_cli.py:14-22 capsys + SystemExit code 2
- tests/test_paths.py:25-29 tmp_path
- init.sh:88 RUNNER=uv run ; init.sh:274 pytest tests/ -q --no-header
- agents/agents/harness_agent.py:410-416 gate() -> bash init.sh --json ; :474 finish usa gate
- Makefile:116-131 test = uv run pytest (testpaths completos), check = lint+typecheck+test+harness-check
- vault/01_PROYECTO/arquitectura.md:381-382 pygame-ce se anade en CORE-001
- vault/01_PROYECTO/arquitectura.md:314 frame budget 60 fps con 15 individuos y UI

## Salida literal del probe (pygame-ce 2.5.8, dummy)

    python 3.12.12
    pygame-ce 2.5.8 (SDL 2.32.10, Python 3.12.12)
    init rc: (5, 0)
    font init: True
    set_mode ok: True size (640, 360) driver dummy
    SysFont ok: Font height 9
    render size (46, 10)
    saved: ...\Temp\tribal_probe.png 2133 bytes
    clock.tick(60) x60: avg 16.63 ms/frame
    60 frames sin tick: avg 0.12 ms/frame (8263 fps)
    warnings: []

    fonts disponibles: 270
    match_font(None): C:\WINDOWS\Fonts\ARIALN.TTF
    SysFont(None,8) height=5 linesize=6
    SysFont(None,10) height=6 linesize=7
    SysFont(None,12) height=8 linesize=9
    SysFont(None,14) height=9 linesize=10
    SysFont(None,16) height=11 linesize=12
    SysFont(None,20) height=13 linesize=15
    desktop_sizes (dummy): [(1024, 768)]
    3600 rects 8x8: 2.22 ms/frame (451 fps)
    3600 rects directos: 2.14 ms/frame
    3600 blits 8x8 precacheados: 2.22 ms/frame

    display_driver real: windows
    ventana creada: (320, 180) en 148 ms
    mixer.init ok: None (44100, -16, 2)
    desktop real: [(1920, 1080)]
    wm_info keys: ['hdc', 'hinstance', 'window']

## CLI actual, literal

    $ uv run python -m tribal hello                 -> Hola, mundo.        EXIT=0
    $ uv run python -m tribal hello --name Tribu    -> Hola, Tribu.        EXIT=0
    $ uv run python -m tribal --version             -> tribal 0.1.1        EXIT=0
    $ uv run python -m tribal                       -> usage ... error: the following
                                                       arguments are required: command  EXIT=2
    $ uv run python -m tribal run                   -> error: argument command: invalid
                                                       choice: 'run' (choose from hello) EXIT=2
    $ uv run pytest tests/ -q --no-header           -> 7 passed in 0.30s

## Riesgos y sorpresas

- pygame-ce no esta instalado: CORE-001 tiene que anadirlo a [project].dependencies y
  ejecutar uv sync antes de que ningun test que lo importe pase la puerta.
- init.sh solo corre `pytest tests/`, no agents/tests (pyproject si los incluye). Un test
  nuevo en tests/ si entra en la puerta.
- Un test que haga set_mode real abriria ventana en la puerta y fallaria en CI. Hay que
  fijar SDL_VIDEODRIVER=dummy antes del display init, y no existe conftest.py.
- No asserts sobre desktop_sizes ni sobre la cola de eventos: en dummy desktop es
  (1024,768) y event.get() devuelve AudioDeviceAdded.
- pygame.init() inicializa mixer (audio). En headless conviene display.init()+font.init().
- __version__ 0.1.1 no coincide con pyproject 0.1.3: `tribal --version` miente y
  `describe` de agents ya peta por consola cp1252 con el caracter flecha. Evitar no-ASCII
  en salida de CLI.
- pygame-ce 2.5.8 trae py.typed y .pyi: mypy no necesitara stubs ni ignore.
- El default font es freesansbold.ttf del wheel, no una fuente de Windows: SysFont(None,n)
  es portable, pero a 8-10 px da altura 5-6 y se ve sucio. Para pixel art, texto dibujado
  a mano o directamente sin texto en el MVP.

## Sin verificar

- Que `uv sync` resuelva pygame-ce offline en otro clon (aqui hay wheel en cache;
  `uv pip install --dry-run` resolvio 1 package desde cache, sin red).
- Que 60 fps se mantengan con 15 individuos + IA por reglas: el probe mide solo dibujo.
- El comportamiento de DPI al 125/150% real (no cambie la escala de la pantalla).
- Que el gate `bash init.sh --json` se comporte igual bajo el bash de Git en Windows.
