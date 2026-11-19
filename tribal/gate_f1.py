"""
La puerta F1→F2 de concepto §15, medida en vez de discutida.

La puerta pide dos cosas: que sin LLM la tribu descubra algo más allá del
primer paso forzado y que la proporción divergente/conformista **reaccione a
la crisis** (§9b). Este módulo corre las dos ramas —calma y crisis, la misma
configuración salvo `crisis`— sobre el mismo rango de semillas y publica la
tabla completa, sin elegir las semillas que salen bien.

Qué mide cada columna:

- **div%**: proporción de divergentes (`temperamento`) entre los vivos al
  terminar. Es la columna **secundaria**: con 12 fundadores es binomial y ruidosa.
- **nac_div**: media del rasgo `divergencia` de **todos los nacidos** acumulados
  en el brazo. No depende de cuántos sobrevivan al final.
- **S**: diferencial de selección = media de `divergencia` de los individuos
  que se reprodujeron (una vez por individuo) menos la media de la población
  **inicial** del brazo. El punto de partida es el tick 0, común a calma y
  crisis (la sequía se aplica desde el primer tick); el JSON publica también
  `mean_divergencia_inicial`. S no es medible sin reproductores: se publica
  `reproductores` y esas filas no cuentan para el umbral.
- **media / sigma**: media y desviación típica (poblacional) de `divergencia`
  entre los vivos al terminar.
- **nacidos**: crías de la corrida.
- **nodos nuevos**: nodos `combinacion` + `interaccion` (niveles 1 y 2 de
  §8b); el árbol y las tradiciones no cuentan como «más allá del primer paso».
- **población / extinciones**: vivos al terminar y cuántas corridas acabaron
  en cero.

El veredicto separa las dos cosas. La **medida primaria** es `senal` (alias
`primaria`): S > 0 en crisis en ≥6/10 y **S < 0 en calma en ≥6/10**. En
estabilidad manda la tradición (concepto §15); la neutralidad (|S| ≤ 0.01) era
un error de criterio, no una propiedad del mundo. La **secundaria** es
`secundaria` (div% sube en ≥8/10, no baja en ninguna, crisis ≤ calma en ≥6/10 y
extinciones en crisis ≤ calma): se publica, pero **no decide**; no existe una
clave `pasa` que pueda confundirse con el veredicto. El barrido es una
herramienta de medición: el test de CI usa tres semillas y comprueba la
dirección del mecanismo, no la tabla completa.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, replace
from typing import Any

from tribal.config import MIN_INDIVIDUOS, SimConfig
from tribal.sim import run

#: Barrido que publica la puerta: las diez primeras semillas, 8000 ticks.
SEMILLAS_PUERTA: tuple[int, ...] = tuple(range(1, 11))
TICKS_PUERTA = 8000
#: El juego vive en 8-15 individuos (concepto §1b), pero el barrido puede subir
#: la población fundadora para reducir deriva genética. Es un parámetro de la
#: medición, no de la escala del juego: `SimConfig` sigue con 12 por defecto.
MAX_INDIVIDUOS_BARRIDO = 100
#: Umbrales de concepto §15 y de la hoja de ruta (eje 6).
SUBE_MINIMO = 8
CRISIS_MENOS_POBLADA_MINIMO = 6
#: La medida primaria es la respuesta en la descendencia: S > 0 en crisis en
#: ≥6/10 y S < 0 en calma en ≥6/10 (en estabilidad manda la tradición).
S_MINIMO = 6
#: Tolerancia al comparar proporciones: dos recuentos iguales no pueden diferir.
EPSILON = 1e-9


@dataclass(frozen=True, slots=True)
class Brazo:
    """Lo que publica el barrido de un régimen (calma o crisis) en una semilla."""

    div_pct: float
    div_media: float
    div_sigma: float
    nacimientos: int
    nodos_nuevos: int
    poblacion: int
    combinaciones: int
    intentos: int
    #: Respuesta en la descendencia (medida primaria): rasgo medio de los
    #: nacidos, diferencial S de los reproductores contra los fundadores y
    #: cuántos individuos distintos se reprodujeron (0 = S no medible).
    mean_div_nacidos: float = 0.0
    S: float = 0.0
    reproductores: int = 0
    #: Ronda 6: viabilidad frente a fecundidad y tasas de descubrimiento,
    #: imitación y longevidad por temperamento.
    S_viabilidad: float = 0.0
    descubrimientos_divergentes: int = 0
    descubrimientos_conformistas: int = 0
    divergentes_registrados: int = 0
    conformistas_registrados: int = 0
    tasa_descubrimiento_divergente: float = 0.0
    tasa_descubrimiento_conformista: float = 0.0
    descubrimientos: int = 0
    imitaciones: int = 0
    tasa_imitacion: float = 0.0
    longevidad_descubridores: float = 0.0
    longevidad_conformistas: float = 0.0

    @property
    def extinta(self) -> bool:
        return self.poblacion == 0

    def a_json(self) -> dict[str, Any]:
        return {
            "div_pct": round(self.div_pct, 2),
            "div_media": round(self.div_media, 4),
            "div_sigma": round(self.div_sigma, 4),
            "nacimientos": self.nacimientos,
            "nodos_nuevos": self.nodos_nuevos,
            "poblacion": self.poblacion,
            "extinta": self.extinta,
            "combinaciones": self.combinaciones,
            "intentos": self.intentos,
            "mean_div_nacidos": round(self.mean_div_nacidos, 4),
            "S": round(self.S, 4),
            "S_fecundidad": round(self.S, 4),
            "S_viabilidad": round(self.S_viabilidad, 4),
            "reproductores": self.reproductores,
            "descubrimientos_divergentes": self.descubrimientos_divergentes,
            "descubrimientos_conformistas": self.descubrimientos_conformistas,
            "divergentes_registrados": self.divergentes_registrados,
            "conformistas_registrados": self.conformistas_registrados,
            "tasa_descubrimiento_divergente": round(self.tasa_descubrimiento_divergente, 4),
            "tasa_descubrimiento_conformista": round(self.tasa_descubrimiento_conformista, 4),
            "descubrimientos": self.descubrimientos,
            "imitaciones": self.imitaciones,
            "tasa_imitacion": round(self.tasa_imitacion, 4),
            "longevidad_descubridores": self.longevidad_descubridores,
            "longevidad_conformistas": self.longevidad_conformistas,
        }


@dataclass(frozen=True, slots=True)
class Fila:
    """Una semilla: la misma configuración corrida en calma y en crisis."""

    seed: int
    calma: Brazo
    crisis: Brazo

    @property
    def sube(self) -> bool:
        return self.crisis.div_pct > self.calma.div_pct + EPSILON

    @property
    def baja(self) -> bool:
        return self.crisis.div_pct < self.calma.div_pct - EPSILON

    def a_json(self) -> dict[str, Any]:
        return {"seed": self.seed, "calma": self.calma.a_json(), "crisis": self.crisis.a_json()}


@dataclass(frozen=True, slots=True)
class Barrido:
    """La tabla completa y su veredicto, serializables."""

    ticks: int
    individuos: int
    filas: tuple[Fila, ...]

    @property
    def sube(self) -> int:
        return sum(1 for fila in self.filas if fila.sube)

    @property
    def baja(self) -> int:
        return sum(1 for fila in self.filas if fila.baja)

    @property
    def empata(self) -> int:
        return len(self.filas) - self.sube - self.baja

    @property
    def crisis_menos_poblada(self) -> int:
        return sum(1 for fila in self.filas if fila.crisis.poblacion <= fila.calma.poblacion)

    @property
    def extinciones_calma(self) -> int:
        return sum(1 for fila in self.filas if fila.calma.extinta)

    @property
    def extinciones_crisis(self) -> int:
        return sum(1 for fila in self.filas if fila.crisis.extinta)

    @property
    def s_crisis_positivo(self) -> int:
        """Semillas con reproductores y S > 0 en crisis (medida primaria)."""
        return sum(
            1 for fila in self.filas if fila.crisis.reproductores > 0 and fila.crisis.S > EPSILON
        )

    @property
    def s_calma_negativo(self) -> int:
        """Semillas con reproductores y S < 0 en calma (manda la tradición)."""
        return sum(
            1 for fila in self.filas if fila.calma.reproductores > 0 and fila.calma.S < -EPSILON
        )

    def veredicto(self) -> dict[str, Any]:
        """Veredicto primario `senal`/`primaria` (S); `secundaria` (div%) no decide.

        Criterio corregido (ronda 6): en calma no se pide neutralidad
        (|S| ≤ 0.01 era un error de criterio), sino **S < 0**: la tradición
        manda en estabilidad (concepto §15). En crisis, S > 0: rastrear el
        parche migrado gana. Ambas cosas en ≥6/10. `secundaria` conserva los
        cuatro criterios de `div%` solo como información.
        """
        sube = self.sube >= SUBE_MINIMO
        no_baja = self.baja == 0
        crisis = self.crisis_menos_poblada >= CRISIS_MENOS_POBLADA_MINIMO
        extinciones = self.extinciones_crisis <= self.extinciones_calma
        s_crisis = self.s_crisis_positivo >= S_MINIMO
        s_calma = self.s_calma_negativo >= S_MINIMO
        primaria = s_crisis and s_calma
        return {
            "sube": self.sube,
            "empata": self.empata,
            "baja": self.baja,
            "sube_en_8_de_10": sube,
            "no_baja": no_baja,
            "crisis_menos_poblada": self.crisis_menos_poblada,
            "crisis_no_mas_poblada_en_6_de_10": crisis,
            "extinciones_calma": self.extinciones_calma,
            "extinciones_crisis": self.extinciones_crisis,
            "no_mas_extinciones_en_crisis": extinciones,
            "S_crisis_positivo": self.s_crisis_positivo,
            "S_calma_negativo": self.s_calma_negativo,
            "S_crisis_positivo_en_6_de_10": s_crisis,
            "S_calma_negativo_en_6_de_10": s_calma,
            "senal": primaria,
            "primaria": primaria,
            "secundaria": sube and no_baja and crisis and extinciones,
        }

    def a_json(self) -> dict[str, Any]:
        return {
            "ticks": self.ticks,
            "individuos": self.individuos,
            "seeds": [fila.seed for fila in self.filas],
            "filas": [fila.a_json() for fila in self.filas],
            "veredicto": self.veredicto(),
        }

    def texto(self) -> str:
        """La tabla en texto plano: una fila por semilla y el veredicto debajo."""
        lineas = [
            "seed | div% c->x | nac_div c/x | S_fec c/x | S_via c/x | desc/d c/x | "
            "desc/c c/x | imit/desc c/x | long_d c/x | long_c c/x | media c/x | "
            "sigma c/x | nac c/x | nodos c/x | pob c/x | ext"
        ]
        for fila in self.filas:
            calma, crisis = fila.calma, fila.crisis
            lineas.append(
                f"{fila.seed:4d} | {calma.div_pct: 5.1f}->{crisis.div_pct: 5.1f} | "
                f"{calma.mean_div_nacidos:.3f}/{crisis.mean_div_nacidos:.3f} | "
                f"{calma.S:+.3f}/{crisis.S:+.3f} | "
                f"{calma.S_viabilidad:+.3f}/{crisis.S_viabilidad:+.3f} | "
                f"{calma.tasa_descubrimiento_divergente:.3f}/{crisis.tasa_descubrimiento_divergente:.3f} | "
                f"{calma.tasa_descubrimiento_conformista:.3f}/{crisis.tasa_descubrimiento_conformista:.3f} | "
                f"{calma.tasa_imitacion:.2f}/{crisis.tasa_imitacion:.2f} | "
                f"{calma.longevidad_descubridores:.0f}/{crisis.longevidad_descubridores:.0f} | "
                f"{calma.longevidad_conformistas:.0f}/{crisis.longevidad_conformistas:.0f} | "
                f"{calma.div_media:.3f}/{crisis.div_media:.3f} | "
                f"{calma.div_sigma:.3f}/{crisis.div_sigma:.3f} | "
                f"{calma.nacimientos}/{crisis.nacimientos} | "
                f"{calma.nodos_nuevos}/{crisis.nodos_nuevos} | "
                f"{calma.poblacion:2d}/{crisis.poblacion:2d} | "
                f"{int(calma.extinta)}/{int(crisis.extinta)}"
            )
        veredicto = self.veredicto()
        lineas.extend(
            [
                "",
                "VEREDICTO PRIMARIO (S): "
                f"S crisis>0 {veredicto['S_crisis_positivo']}/{len(self.filas)} | "
                f"S calma<0 {veredicto['S_calma_negativo']}/{len(self.filas)} | "
                f"PRIMARIA {veredicto['primaria']}",
                "SECUNDARIO (div%, no decide): "
                f"sube {veredicto['sube']}/{len(self.filas)} | "
                f"empata {veredicto['empata']}/{len(self.filas)} | "
                f"baja {veredicto['baja']}/{len(self.filas)} | "
                f"sube>=8/10 {veredicto['sube_en_8_de_10']} | "
                f"no baja {veredicto['no_baja']} | "
                f"crisis<=calma>=6/10 {veredicto['crisis_no_mas_poblada_en_6_de_10']} | "
                f"extinciones crisis<=calma {veredicto['no_mas_extinciones_en_crisis']} | "
                f"SECUNDARIA {veredicto['secundaria']}",
            ]
        )
        return "\n".join(lineas)


def medir_brazo(seed: int, crisis: bool, *, ticks: int, individuos: int) -> Brazo:
    """Corre una partida y devuelve lo que el barrido publica de ese régimen."""
    config = replace(SimConfig(seed=seed, individuos=individuos), crisis=crisis)
    simulacion = run(ticks, seed, True, individuos=individuos, config=config)
    resumen = simulacion.resumen()
    divergencias = [individuo.genoma.divergencia for individuo in simulacion.mundo.individuos]
    poblacion = len(divergencias)
    nodos = resumen["nodos_por_origen"]
    return Brazo(
        div_pct=100.0 * resumen["n_divergentes"] / poblacion if poblacion else 0.0,
        div_media=statistics.fmean(divergencias) if divergencias else 0.0,
        div_sigma=statistics.pstdev(divergencias) if divergencias else 0.0,
        nacimientos=resumen["nacimientos"],
        nodos_nuevos=nodos["combinacion"] + nodos["interaccion"],
        poblacion=poblacion,
        combinaciones=nodos["combinacion"],
        intentos=resumen["intentos_divergentes"],
        mean_div_nacidos=resumen["mean_divergencia_nacidos"],
        S=resumen["S_fecundidad"],
        reproductores=resumen["reproductores"],
        S_viabilidad=resumen["S_viabilidad"],
        descubrimientos_divergentes=resumen["descubrimientos_divergentes"],
        descubrimientos_conformistas=resumen["descubrimientos_conformistas"],
        divergentes_registrados=resumen["divergentes_registrados"],
        conformistas_registrados=resumen["conformistas_registrados"],
        tasa_descubrimiento_divergente=resumen["tasa_descubrimiento_divergente"],
        tasa_descubrimiento_conformista=resumen["tasa_descubrimiento_conformista"],
        descubrimientos=resumen["descubrimientos"],
        imitaciones=resumen["imitaciones"],
        tasa_imitacion=resumen["tasa_imitacion"],
        longevidad_descubridores=resumen["longevidad_media_descubridores"],
        longevidad_conformistas=resumen["longevidad_media_conformistas"],
    )


def medir_barrido(
    semillas: tuple[int, ...], *, ticks: int = TICKS_PUERTA, individuos: int = 12
) -> Barrido:
    """Los dos brazos para cada semilla, con la misma configuración salvo `crisis`."""
    if not semillas:
        raise ValueError("el barrido necesita al menos una semilla")
    if ticks <= 0:
        raise ValueError(f"ticks debe ser mayor que 0 (recibido {ticks})")
    if not MIN_INDIVIDUOS <= individuos <= MAX_INDIVIDUOS_BARRIDO:
        raise ValueError(
            f"individuos debe estar entre {MIN_INDIVIDUOS} y {MAX_INDIVIDUOS_BARRIDO} "
            f"para el barrido (recibido {individuos})"
        )
    filas = tuple(
        Fila(
            seed=seed,
            calma=medir_brazo(seed, False, ticks=ticks, individuos=individuos),
            crisis=medir_brazo(seed, True, ticks=ticks, individuos=individuos),
        )
        for seed in semillas
    )
    return Barrido(ticks=ticks, individuos=individuos, filas=filas)


def parsear_semillas(texto: str) -> tuple[int, ...]:
    """`1-10`, `1,3,5` o una mezcla; devuelve las semillas ordenadas y sin repetir."""
    semillas: set[int] = set()
    for trozo in texto.split(","):
        trozo = trozo.strip()
        if not trozo:
            continue
        if "-" in trozo:
            inicio, _, fin = trozo.partition("-")
            try:
                primero, ultimo = int(inicio), int(fin)
            except ValueError:
                raise ValueError(f"rango de semillas inválido: {trozo!r}") from None
            if primero > ultimo:
                raise ValueError(f"rango de semillas al revés: {trozo!r}")
            semillas.update(range(primero, ultimo + 1))
        else:
            try:
                semillas.add(int(trozo))
            except ValueError:
                raise ValueError(f"semilla inválida: {trozo!r}") from None
    if not semillas:
        raise ValueError("no hay ninguna semilla en el rango")
    if min(semillas) < 1:
        raise ValueError("las semillas empiezan en 1")
    return tuple(sorted(semillas))
