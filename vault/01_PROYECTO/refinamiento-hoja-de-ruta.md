# Hoja de ruta de refinamiento

> Estado: hoja de ruta, trabajo **posterior** a EMER-001, F2 y F3. No es una fase,
> es un conjunto de ejes para seguir refinando cuando el motor base esté honesto.
> Última revisión: 2026-11-18.

## Regla de oro

"Cmás complejo" no mejora nada; **"más acoplado" sí**. Cada mecanismo nuevo debe ser
un acoplamiento —la conducta de A cambia la recompensa de B, que cambia la conducta
de A— y debe tener **una consecuencia observable y un test**. Sin test que demuestre
que hace algo *no guionado*, es decorado, no delicadeza.

## Los seis ejes (por palanca)

1. **Utilidad situacional, no multiplicadores fijos.** Hoy `beneficios.py` asigna
   `raedera = +25 % bayas` fijo. La utilidad debe depender del contexto: una
   herramienta vale más cuando escasea su recurso, un refugio vale más en invierno,
   el fuego vale más de noche. Así el valor de un invento es **condicional** y la
   selección pasa a depender del estado.
   - *Medible:* en calma el invento no mueve la supervivencia; en crisis sí.

2. **Transmisión sesgada por prestigio (a quién copias).** Hoy el conformista imita
   lo que tiene cerca. Refinamiento: copiar al **exitoso**, no al mayoritario. Es la
   paradoja de Rogers: imitar es barato (el conformismo prospera), pero si todos
   imitan lo que ya no sirve, el grupo se estanca y en crisis lo paga. Esa tensión
   individuo/grupo es la delicadeza que produce cultura real.
   - *Medible:* los linajes de copiados prestigiosos divergen de los de copiados al
     azar y correlacionan con supervivencia.

3. **Gradiente ambiental: estaciones, parches, migración.** El mundo hoy es casi
   uniforme. Hacer que la comida migre, que los parches se agoten localmente y que
   haya estaciones convierte "dónde y cuándo estás" en una decisión. Eso es lo que
   hace que "explorar/migrar" (conducta divergente en calma) deje de ser decorativa.
   - *Medible:* la tribu que sigue a la presa sobrevive; la que se queda muere, sin
     que nadie lo escriba.

4. **Una necesidad social + estructura de edad.** Añadir pertenencia/afiliación
   (estar solo cuesta) y que los **ancianos concentren conocimiento** (su muerte =
   pérdida de técnicas, §9b). Esto hace emerger roles y cuidado de los viejos por
   que *conviene*, no por guion.
   - *Medible:* un grupo que pierde a su anciano pierde una técnica que ya no recupera.

5. **Saliencia como presupuesto narrativo (§10b).** El peso *ganado* (primero en
   encender fuego, líder, chamán) decide cuánto "piensa" cada agente. Convierte
   ruido en personajes — solo funciona sobre un motor honesto.

6. **Trazabilidad (transversal).** Linaje, causa de muerte, diferencial de
   selección, dos semillas → dos culturas. No se puede refinar lo que no se mide.
   Esta es la que hace que los otros cinco sean delicados en vez de opacos.

## Secuencia recomendada

1. Ejes **1 + 2** juntos (corazón: sin ellos todo lo demás flota).
2. Eje **3** (da razón de ser a la utilidad situacional).
3. Eje **4** (roles y transmisión).
4. Eje **6** desde el principio: cada eje entra **con su telemetría**, no al final.
5. Eje **5** sobre el motor ya honesto.

## Norte

La prueba de que el sistema es delicado de verdad no es que haga cosas bonitas:
es **path dependency** — dos semillas producen dos civilizaciones distintas (una
inventa fuego, otra fija un tabú) y ninguna estaba escrita.

## Advertencia

Delicado no es caótico. No se busca sensibilidad a todo (eso vuelve el sistema
inestable y la tribu muere al azar); se buscan **recompensas condicionales** — que
lo que haces valga distinto según el estado. Ahí está la magia.
