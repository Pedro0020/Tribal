"""
La puerta F2→F3 de concepto §15, medida en vez de discutida.

La puerta pide dos cosas: que el LLM proponga nodos **fuera del árbol** (nivel 1
de §8b) que pasen la validación de plausibilidad a un ritmo no trivial, y que la
saliencia concentre la narración en pocos individuos (§10b). Este módulo corre
una partida por semilla con un **backend guionizado** —determinista, sin red— y
publica la tabla completa, los nodos fuera del árbol con su autor y su tick, y
el veredicto.

El backend guionizado hace tres cosas a la vez:

- propone combinaciones del catálogo (`combinaciones.py`) cuando sus dos
  requisitos ya están activos;
- propone cruces nuevos que el motor debe aceptar como `origen="llm"` si la
  pareja es de la misma rama o de ramas adyacentes;
- intercala propuestas imposibles (prerrequisitos inexistentes o ramas lejanas)
  para demostrar que el motor **rechaza**, no que todo lo que llega entra.

La narración se mide contra el **área bajo la curva de saliencia** (cuánto
protagonismo acumuló cada individuo en toda la partida), no contra un top
instantáneo: con `SALIENCIA_MAX = 10` muchos individuos empatan al final y el
top-3 por id sería un empate arbitrario. El cronista es el sujeto del hito si
está en el top-3 vivo; si no, el más saliente. Solo se narra cuando alguien
tiene saliencia positiva, y esa decisión no toca el rasgo ni el genoma.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Any

from tribal.config import SimConfig
from tribal.culture.arbol import ARBOL, RAMAS
from tribal.culture.combinaciones import COMBINACIONES
from tribal.llm.cliente import ClienteLLM, Transporte, backend_stub
from tribal.llm.cola import ColaLLM
from tribal.sim import Simulacion, run

#: K de la puerta: las cinco combinaciones del catálogo, el nivel 1 completo de
#: §8b. Es no trivial porque no basta un cruce afortunado: en cada semilla tienen
#: que cuajar todos los cruces posibles del catálogo, y además al menos un nodo
#: `llm` que no está en él (si no, el canal del modelo no se ha ejercitado).
K_NODOS_FUERA = 5
#: Fracción mínima de líneas narradas que deben concentrar los tres individuos
#: con más saliencia acumulada.
CONCENTRACION_MINIMA = 0.5
#: Barrido que publica la puerta: las cinco primeras semillas, 3000 ticks.
SEMILLAS_PUERTA_F2: tuple[int, ...] = tuple(range(1, 6))
TICKS_PUERTA_F2 = 3000
#: Orígenes que cuentan como «fuera del árbol» en el informe. `llm` no entra en
#: el KPI de `objetivo.md` §3.2 (`pct_fuera_arbol`), pero sí en la puerta F2.
ORIGENES_FUERA: tuple[str, ...] = ("combinacion", "interaccion", "llm")
#: Un backend guionizado intercala un rechazo cada seis propuestas: uno por
#: prerrequisito inexistente y otro por ramas no adyacentes.
CADENCIA_RECHAZO = 6


@dataclass(frozen=True, slots=True)
class FilaF2:
    """Lo que publica una semilla de la puerta F2→F3."""

    seed: int
    ticks: int
    crisis: bool
    nodos_totales: int
    por_origen: dict[str, int]
    fuera_arbol: tuple[dict[str, Any], ...]
    pct_fuera_arbol: float
    pct_fuera_arbol_llm: float
    lineas_narradas: int
    narraciones_por_individuo: dict[int, int]
    top3: tuple[tuple[int, float], ...]
    concentracion: float
    propuestas: dict[str, Any]

    @property
    def nodos_fuera(self) -> int:
        return self.por_origen.get("combinacion", 0) + self.por_origen.get("llm", 0)

    def veredicto(self) -> dict[str, Any]:
        """Los cuatro criterios de la puerta, uno por uno y sin promedios."""
        nodos = self.nodos_fuera >= K_NODOS_FUERA
        llm = self.por_origen.get("llm", 0) >= 1
        concentracion = self.concentracion >= CONCENTRACION_MINIMA
        rechazo = self.propuestas.get("rechazadas", 0) >= 1
        return {
            "nodos_fuera": self.nodos_fuera,
            "k": K_NODOS_FUERA,
            "nodos_fuera_ok": nodos,
            "llm_ok": llm,
            "concentracion": round(self.concentracion, 3),
            "concentracion_minima": CONCENTRACION_MINIMA,
            "concentracion_ok": concentracion,
            "propuestas_rechazadas": self.propuestas.get("rechazadas", 0),
            "rechazo_ok": rechazo,
            "success": nodos and llm and concentracion and rechazo,
        }

    def a_json(self) -> dict[str, Any]:
        return {
            "seed": self.seed,
            "ticks": self.ticks,
            "crisis": self.crisis,
            "nodos_totales": self.nodos_totales,
            "por_origen": self.por_origen,
            "fuera_arbol": list(self.fuera_arbol),
            "pct_fuera_arbol": self.pct_fuera_arbol,
            "pct_fuera_arbol_llm": self.pct_fuera_arbol_llm,
            "lineas_narradas": self.lineas_narradas,
            "narraciones_por_individuo": {
                str(individuo): lineas
                for individuo, lineas in sorted(self.narraciones_por_individuo.items())
            },
            "top3": [[individuo, round(saliencia, 3)] for individuo, saliencia in self.top3],
            "concentracion": round(self.concentracion, 3),
            "propuestas": self.propuestas,
            "veredicto": self.veredicto(),
        }


@dataclass(frozen=True, slots=True)
class BarridoF2:
    """La tabla completa y su veredicto, serializables."""

    ticks: int
    crisis: bool
    llm: str
    filas: tuple[FilaF2, ...]

    @property
    def success(self) -> bool:
        return bool(self.filas) and all(fila.veredicto()["success"] for fila in self.filas)

    def veredicto(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "semillas": len(self.filas),
            "semillas_ok": sum(1 for fila in self.filas if fila.veredicto()["success"]),
            "k": K_NODOS_FUERA,
            "concentracion_minima": CONCENTRACION_MINIMA,
            "criterios": {
                "k_nodos_fuera": all(fila.veredicto()["nodos_fuera_ok"] for fila in self.filas),
                "al_menos_un_llm": all(fila.veredicto()["llm_ok"] for fila in self.filas),
                "concentracion_top3": all(
                    fila.veredicto()["concentracion_ok"] for fila in self.filas
                ),
                "rechazo_demostrado": all(fila.veredicto()["rechazo_ok"] for fila in self.filas),
            },
        }

    def a_json(self) -> dict[str, Any]:
        return {
            "ticks": self.ticks,
            "crisis": self.crisis,
            "llm": self.llm,
            "filas": [fila.a_json() for fila in self.filas],
            "veredicto": self.veredicto(),
        }

    def texto(self) -> str:
        """La tabla en texto plano, más los nodos fuera del árbol y el veredicto."""
        lineas = [
            "seed | nodos | arbol comb inter llm | fuera | %fuera | %+llm | lineas | "
            "top3 (peso narrativo) | conc | propuestas sol/ok/rech | ok"
        ]
        for fila in self.filas:
            por = fila.por_origen
            top3 = " ".join(f"{individuo}:{saliencia:.1f}" for individuo, saliencia in fila.top3)
            propuestas = fila.propuestas
            lineas.append(
                f"{fila.seed:4d} | {fila.nodos_totales:5d} | "
                f"{por['arbol']:4d} {por['combinacion']:4d} {por['interaccion']:5d} "
                f"{por['llm']:3d} | {fila.nodos_fuera:5d} | "
                f"{fila.pct_fuera_arbol:5.1f}% | {fila.pct_fuera_arbol_llm:5.1f}% | "
                f"{fila.lineas_narradas:6d} | "
                f"{top3:<30} | {fila.concentracion:5.1f} | "
                f"{propuestas['solicitadas']:3d}/{propuestas['aceptadas']:2d}/"
                f"{propuestas['rechazadas']:2d} | {fila.veredicto()['success']}"
            )
        lineas.append("")
        lineas.append("NODOS FUERA DEL ÁRBOL")
        for fila in self.filas:
            lineas.append(f"  seed {fila.seed}:")
            if not fila.fuera_arbol:
                lineas.append("    (ninguno)")
            for nodo in fila.fuera_arbol:
                lineas.append(
                    f"    {nodo['id']:<24} {nodo['rama']:<9} nivel {nodo['nivel']} "
                    f"{nodo['origen']:<12} autor {nodo['autor']:<3} tick {nodo['tick']}"
                )
        veredicto = self.veredicto()
        lineas.extend(
            [
                "",
                f"VEREDICTO F2->F3: {veredicto['semillas_ok']}/{veredicto['semillas']} semillas | "
                f"K={K_NODOS_FUERA} nodos fuera | "
                f"concentración top-3 >= {CONCENTRACION_MINIMA:.0%} | "
                f"SUCCESS {veredicto['success']}",
            ]
        )
        return "\n".join(lineas)


def medir_semilla(
    seed: int,
    *,
    ticks: int = TICKS_PUERTA_F2,
    crisis: bool = True,
    llm: str = "script",
    sincrono: bool = True,
    individuos: int = 12,
) -> FilaF2:
    """Corre una partida y devuelve lo que la puerta publica de esa semilla."""
    if ticks <= 0:
        raise ValueError(f"ticks debe ser mayor que 0 (recibido {ticks})")
    config = replace(SimConfig(seed=seed, individuos=individuos), crisis=crisis)
    cola = _crear_cola(llm, sincrono)
    simulacion = run(
        ticks,
        seed,
        headless=True,
        individuos=config.individuos,
        config=config,
        cola=cola,
    )
    return _fila(simulacion, seed=seed, ticks=ticks, crisis=crisis, llm=llm)


def medir_puerta(
    semillas: Sequence[int],
    *,
    ticks: int = TICKS_PUERTA_F2,
    crisis: bool = True,
    llm: str = "script",
    sincrono: bool = True,
    individuos: int = 12,
) -> BarridoF2:
    """La puerta para cada semilla, con la misma configuración."""
    if not semillas:
        raise ValueError("la puerta necesita al menos una semilla")
    if len(semillas) != len(set(semillas)):
        raise ValueError("hay semillas repetidas")
    filas = tuple(
        medir_semilla(
            seed,
            ticks=ticks,
            crisis=crisis,
            llm=llm,
            sincrono=sincrono,
            individuos=individuos,
        )
        for seed in semillas
    )
    return BarridoF2(ticks=ticks, crisis=crisis, llm=llm, filas=filas)


def _crear_cola(llm: str, sincrono: bool) -> ColaLLM | None:
    if llm == "off":
        return None
    if llm == "script":
        return ColaLLM(ClienteLLM(transporte=backend_guionizado()), sincrona=sincrono)
    if llm == "stub":
        return ColaLLM(ClienteLLM(transporte=backend_stub()), sincrona=sincrono)
    if llm == "http":
        return ColaLLM(ClienteLLM(), sincrona=False)
    raise ValueError(f"capa LLM desconocida: {llm!r}")


def _fila(simulacion: Simulacion, *, seed: int, ticks: int, crisis: bool, llm: str) -> FilaF2:
    resumen = simulacion.resumen()
    nodos = resumen["nodos"]
    por_origen = dict(resumen["nodos_por_origen"])
    fuera = tuple(nodo for nodo in nodos if nodo["origen"] in ORIGENES_FUERA)
    fuera_llm = sum(por_origen.get(origen, 0) for origen in ("combinacion", "interaccion", "llm"))
    lineas = [
        entrada
        for entrada in simulacion.diario.entradas
        if entrada.narrada and entrada.narrador_id is not None
    ]
    por_individuo = Counter(
        entrada.narrador_id for entrada in lineas if entrada.narrador_id is not None
    )
    acumulada = simulacion.saliencia_acumulada
    top3 = tuple(
        (individuo, saliencia)
        for individuo, saliencia in sorted(
            ((individuo, valor) for individuo, valor in acumulada.items() if valor > 0.0),
            key=lambda par: (-par[1], par[0]),
        )[:3]
    )
    total = len(lineas)
    concentracion = (
        sum(por_individuo.get(individuo, 0) for individuo, _ in top3) / total if total else 0.0
    )
    return FilaF2(
        seed=seed,
        ticks=ticks,
        crisis=crisis,
        nodos_totales=len(nodos),
        por_origen=por_origen,
        fuera_arbol=fuera,
        pct_fuera_arbol=resumen["pct_fuera_arbol"],
        pct_fuera_arbol_llm=round(100.0 * fuera_llm / len(nodos), 1) if nodos else 0.0,
        lineas_narradas=total,
        narraciones_por_individuo=dict(por_individuo),
        top3=top3,
        concentracion=concentracion,
        propuestas=simulacion.propuestas_llm,
    )


def backend_guionizado() -> Transporte:
    """Backend determinista de la puerta: propuestas válidas, imposibles y frases.

    No hay estado global ni red: cada petición se responde por su contenido. El
    contador de propuestas solo sirve para intercalar los rechazos de forma
    reproducible. Las propuestas del catálogo se leen de `combinaciones.py`; las
    nuevas combinan dos nodos activos de ramas iguales o adyacentes.
    """
    estado = {"propuestas": 0}

    def transporte(
        _metodo: str,
        _url: str,
        cuerpo: dict[str, Any] | None,
        _timeout: float,
    ) -> tuple[int, bytes]:
        if _metodo != "POST" or cuerpo is None:
            return 200, b'{"models": []}'
        propiedades = _propiedades(cuerpo)
        prompt = _prompt(cuerpo)
        if "texto" in propiedades:
            return _sobre({"texto": _frase(prompt)})
        if "requisitos" in propiedades:
            estado["propuestas"] += 1
            return _sobre(_propuesta(_estado(prompt), estado["propuestas"]))
        candidatas = _candidatas(prompt)
        if not candidatas:
            return 500, b'{"error": "sin candidatas"}'
        return _sobre(
            {
                "accion": candidatas[0],
                "objetivo": "",
                "razon": "guion: la primera candidata por urgencia",
                "dialogo": "",
            }
        )

    return transporte


def _propuesta(estado: Mapping[str, Any], n: int) -> dict[str, Any]:
    """Una propuesta por turno: catálogo primero, luego un cruce nuevo."""
    activos = [
        nodo
        for nodo in estado.get("nodos_activos", [])
        if isinstance(nodo, Mapping) and isinstance(nodo.get("id"), str)
    ]
    ids = {nodo["id"] for nodo in activos}
    ramas = {nodo["id"]: nodo.get("rama") for nodo in activos if isinstance(nodo.get("rama"), str)}
    existentes = {nodo for nodo in estado.get("nodos", []) if isinstance(nodo, str)}

    if n % CADENCIA_RECHAZO == 0:
        return _imposible(n, motivo="prerrequisito")
    if n % CADENCIA_RECHAZO == 3:
        return _lejana(n, activos, ramas)

    for combinacion in COMBINACIONES.values():
        if combinacion.id in existentes:
            continue
        if all(requisito in ids for requisito in combinacion.requisitos):
            return {
                "id": combinacion.id,
                "rama": combinacion.rama,
                "requisitos": list(combinacion.requisitos),
                "titulo": combinacion.titulo,
                "contenido": combinacion.contenido,
            }

    pares = [
        (primero, segundo)
        for primero in sorted(ids)
        for segundo in sorted(ids)
        if primero < segundo and _adyacentes(ramas.get(primero), ramas.get(segundo))
    ]
    for primero, segundo in pares:
        nodo_id = _id_nuevo(primero, segundo)
        if nodo_id in existentes or nodo_id in ARBOL or nodo_id in COMBINACIONES:
            continue
        return {
            "id": nodo_id,
            "rama": ramas[primero],
            "requisitos": [primero, segundo],
            "titulo": f"Cruce de {primero} y {segundo}"[:80],
            "contenido": f"Combinar {primero} con {segundo} abre una técnica nueva."[:240],
        }
    return _imposible(n, motivo="prerrequisito")


def _imposible(n: int, *, motivo: str) -> dict[str, Any]:
    """Propuesta que el motor debe rechazar: el nodo no existe."""
    return {
        "id": f"propuesta_imposible_{n}",
        "rama": "litica",
        "requisitos": [f"nodo_inexistente_{n}", f"nodo_inexistente_{n + 1}"],
        "titulo": f"Propuesta imposible {n}",
        "contenido": f"El guion sabe que esta propuesta no tiene {motivo}.",
    }


def _lejana(
    n: int, activos: Sequence[Mapping[str, Any]], ramas: Mapping[str, Any]
) -> dict[str, Any]:
    """Propuesta con dos ramas no adyacentes; si no hay pareja, una imposible."""
    por_rama: dict[str, list[str]] = {}
    for nodo in activos:
        rama = ramas.get(nodo["id"])
        if isinstance(rama, str):
            por_rama.setdefault(rama, []).append(nodo["id"])
    for primera in ("litica", "fuego", "lenguaje"):
        for segunda in ("simbolico", "roles"):
            if por_rama.get(primera) and por_rama.get(segunda):
                return {
                    "id": f"propuesta_lejana_{n}",
                    "rama": primera,
                    "requisitos": [sorted(por_rama[primera])[0], sorted(por_rama[segunda])[0]],
                    "titulo": f"Cruce lejano {n}",
                    "contenido": "Dos ramas que no son vecinas: la propuesta debe caer.",
                }
    return _imposible(n, motivo="rama")


def _adyacentes(primera: object, segunda: object) -> bool:
    if not isinstance(primera, str) or not isinstance(segunda, str):
        return False
    if primera not in RAMAS or segunda not in RAMAS:
        return False
    return abs(RAMAS.index(primera) - RAMAS.index(segunda)) <= 1


def _id_nuevo(primero: str, segundo: str) -> str:
    """Id estable y corto: el par, no el título, identifica la propuesta."""
    digest = hashlib.sha256(f"{primero}|{segundo}".encode()).hexdigest()[:12]
    return f"llm_{digest}"


def _frase(prompt: str) -> str:
    hito = next(
        (
            linea.split(":", 1)[1].strip()
            for linea in prompt.splitlines()
            if linea.startswith("Hito:")
        ),
        "hito",
    )
    return f"la tribu recordó {hito}"


def _sobre(contenido: Mapping[str, Any]) -> tuple[int, bytes]:
    sobre = {"message": {"role": "assistant", "content": json.dumps(contenido, ensure_ascii=False)}}
    return 200, json.dumps(sobre, ensure_ascii=False).encode("utf-8")


def _propiedades(cuerpo: Mapping[str, Any]) -> Mapping[str, Any]:
    formato = cuerpo.get("format")
    if not isinstance(formato, Mapping):
        return {}
    propiedades = formato.get("properties")
    return propiedades if isinstance(propiedades, Mapping) else {}


def _prompt(cuerpo: Mapping[str, Any]) -> str:
    mensajes = cuerpo.get("messages")
    if not isinstance(mensajes, list):
        return ""
    for mensaje in reversed(mensajes):
        if not isinstance(mensaje, Mapping) or mensaje.get("role") != "user":
            continue
        contenido = mensaje.get("content")
        if isinstance(contenido, str):
            return contenido
    return ""


def _estado(prompt: str) -> Mapping[str, Any]:
    for linea in prompt.splitlines():
        if not linea.startswith("Estado: "):
            continue
        try:
            datos = json.loads(linea.split(": ", 1)[1])
        except ValueError:
            return {}
        return datos if isinstance(datos, Mapping) else {}
    return {}


def _candidatas(prompt: str) -> tuple[str, ...]:
    for linea in prompt.splitlines():
        if not linea.startswith("Acciones candidatas:"):
            continue
        return tuple(parte.strip() for parte in linea.split(":", 1)[1].split(",") if parte.strip())
    return ()
