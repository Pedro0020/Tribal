# Selección real de la divergencia — diagnóstico y arreglo de F1-004

> Estado: análisis técnico del fallo de la puerta F1→F2 (2026-11-18).

## Diagnóstico

El rasgo `divergencia` sube en crisis por **cuatro canales que premian el rasgo
directamente**, no porque la conducta divergente produzca más energía:

| Canal | Dónde | Qué hace |
|---|---|---|
| Penalización al no-divergente al comer | `tribal/core/acciones.py` `PENALIZACION_CONFORMISTA_CRISIS=0.20` | El mismo bocado da 20 % menos si `divergencia < umbral` |
| Sed extra al no-divergente | `tribal/sim.py` `factor_sed_crisis=1.3` | El rasgo, no la conducta, decide cuánta sed |
| Ventaja reproductiva | `tribal/sim.py` `VENTAJA_REPRODUCTIVA_DIVERGENTE` | El divergente cría antes por decreto |
| Plasticidad numérica | `tribal/sim.py` `_plasmar_divergencia` / `_moldear_divergencia` | Se edita el valor del rasgo con `+= delta` |

Los cuatro son "fitness por decreto": el código decide que el divergente gana,
en vez de dejar que gane porque su conducta (experimentar) descubrió algo útil.

Además, la sequía es **energéticamente favorable** por dos subsidios:

- `UMBRAL_REPRODUCCION_CRISIS = 30` frente a `65` en calma → se reproduce con la
  mitad de energía.
- `ENERGIA_CRIA = 80` > umbral → cada cría inyecta energía neta a la población.

Resultado: baby-boom en crisis y la sequía acaba siendo el régimen favorable.

## Principio

> La divergencia solo debe cambiar **lo que el agente hace**; la aptitud solo
> debe venir de **lo que esa conducta produce en el mundo**.

## Arreglo

1. **Borrar los cuatro canales** de la tabla: sin penalización al comer, sin sed
   extra, sin ventaja reproductiva, sin plasticidad numérica. El rasgo queda
   como mero selector de conducta.
2. **Conservar la conducta**: `_intentar_combinacion` (el divergente gasta el tick
   experimentando, con coste de no comer/beber ese tick) e `_practicar` (el
   conformista imita y transmite).
3. **Conservar `beneficios`**: el multiplicador de la combinación se aplica a
   quien tenga el nodo activo, sea divergente o no. Es la utilidad emergente.
4. **Hacer que la utilidad importe solo bajo escasez** (selección real):
   - La crisis baja la **capacidad de carga** (menos bayas/agua) hasta que el
     +X % de comida de una combinación sea la diferencia entre sobrevivir y
     morir. En calma el bonus es irrelevante (sobra comida); en crisis es
     decisivo.
   - Solo el divergente puede *descubrir* la combinación → por eso, en crisis,
     el linaje divergente sobrevive más. Eso es selección dependiente de
     frecuencia **emergente**, no codificada.
5. **Corregir la reproducción**: umbral de crisis ≥ calma (o mayor), y la cría
   no debe inyectar energía neta (o nace restando energía a la madre).

## Cómo probar la puerta (mecanismo, no resultado)

- En crisis, la ventaja debe ser **del descubridor**, no del rasgo: comparar
  supervivencia/energía de quienes *descubrieron* una combinación útil frente a
  quienes no, independientemente de su `divergencia`.
- Un divergente que **no** descubre nada debe ir igual que un conformista.
- Medir la **distribución completa** de semillas (≥ 8/10), no una selección
  favorable. Reportar la tabla, no solo pasar/fallar.
