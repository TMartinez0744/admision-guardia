# Revisión experimental de la Parte 2

15 de noviembre de 2026. Trabajo exploratorio: el experimento no modificó
`entrega.py`, los pesos ni los prompts. Después, la caché de la última sección
se incorporó al buscador de la entrega (ver INFORME, Parte 2).

## Preguntas y método

1. ¿Se reproducen los resultados del buscador del informe?
2. ¿El caso final fallido carecía de la evidencia necesaria?
3. ¿Recuperar secciones completas, ordenadas por su mejor párrafo, mejora la relación entre evidencia y contexto?
4. ¿Se repiten suficientes consultas como para que una caché sea útil?

Se usó la evaluación oficial del kit, sin modificarla, con las 60 consultas de
desarrollo y las normas originales. Se conservaron el modelo bge-m3 y su revisión
`5617a9f61b028005a4858fdac845db406aefb181`. La variante experimental selecciona
secciones distintas según el ranking de sus párrafos y devuelve su texto completo.
Se compararon tanto los resultados habituales como un presupuesto de 512 tokens.
Los tokens son la aproximación de la cátedra: cuatro caracteres por token.

También se escribieron 16 consultas adicionales: 13 coloquiales y 3 que requieren
dos secciones. Sus referencias y métricas son solo de las normas originales. Son consultas manuales
de exploración, no un test ciego ni una estimación de generalización.
Cada etiqueta exige recuperar el párrafo completo indicado; no se compara su dificultad
directamente con la de las 60 consultas oficiales, que usan fragmentos de evidencia.

## Reproducción y alternativa de fragmentación

Resultados sobre las 60 consultas oficiales:

| Variante | Recall | Precisión | Tokens | Completas | Recall con 512 tokens |
|---|---:|---:|---:|---:|---:|
| BM25 por párrafo, k=2 | 0,625 | 0,358 | 166 | 36/60 | 0,767 |
| bge-m3 por párrafo, k=2 | 0,792 | 0,458 | 179 | 46/60 | 0,950 |
| bge-m3 por párrafo, k=3, entrega actual | 0,883 | 0,339 | 270 | 52/60 | 0,950 |
| bge-m3 por párrafo, k=4 | 0,892 | 0,258 | 352 | 53/60 | 0,950 |
| bge-m3, dos secciones por su mejor párrafo | 0,933 | 0,533 | 617 | 56/60 | 0,833 |

Se reprodujeron las métricas publicadas de BM25 y de bge-m3. Las secciones
completas recuperan más evidencia sin límite de contexto, pero consumen 2,29 veces
el contexto de la entrega. Con presupuesto igual pierden frente a los párrafos.
No se justifica reemplazar el buscador actual basándose en el recall sin límite.
La precisión también depende de la unidad de fragmentación: un resultado que
contiene una evidencia cuenta como relevante aunque incluya mucho texto adicional.

En las 16 consultas adicionales:

| Variante | Recall | Tokens | Completas | Recall con 512 tokens |
|---|---:|---:|---:|---:|
| BM25 por párrafo, k=2 | 0,375 | 141 | 5/16 | 0,594 |
| bge-m3 por párrafo, k=2 | 0,844 | 184 | 13/16 | 1,000 |
| bge-m3 por párrafo, k=3 | 0,875 | 274 | 14/16 | 1,000 |
| bge-m3 por párrafo, k=4 | 0,938 | 351 | 15/16 | 1,000 |
| bge-m3, dos secciones por su mejor párrafo | 0,969 | 591 | 15/16 | 0,906 |

La comparación favorece nuevamente los párrafos con presupuesto igual. Estos datos
no prueban que aumentar el contexto mejore al agente entrenado: hay que evaluarlo
con el contexto modificado antes de adoptar un cambio.

## Corrección del diagnóstico de pev-049

En `evaluacion/corridas/entrega-original/trazas.jsonl`, el caso `pev-049` recibe
esta secuencia para «registro del paciente y ubicación en el box»:

1. NOR-ADM-01 §4: regla general por nivel de triage.
2. NOR-ADM-02 §2: precedencia de la regla para pacientes mayores.
3. NOR-ADM-02 §1, incluida la línea **P-ADM-2 = 67 años**.

El triage informa **71 años**, pero el agente registra `box_antes_del_registro: false`.
La reproducción local del ranking devuelve los mismos tres párrafos en ese orden.

La evidencia necesaria estaba en el contexto. Por lo tanto, no corresponde atribuir
el fallo a la ausencia del párrafo ni afirmar que el modelo hizo bien su parte.
El orden, la redundancia y la aplicación de la regla son hipótesis que requieren
pruebas controladas con el agente. La traza por sí sola no identifica la causa.

`INFORME.md` (Parte 2, «Cuánto rinde el agente con nuestro buscador», y las
conclusiones de la Parte 4) ya atribuye el fallo al modelo y no al buscador.

## Reutilización de búsquedas

Las 150 trazas finales contienen 496 búsquedas y 14 textos de consulta distintos.
La caché debe pertenecer a una instancia del buscador: no se pueden compartir
resultados entre versiones de normas.

| Normas | Búsquedas | Consultas distintas | Repeticiones evitables |
|---|---:|---:|---:|
| Original | 152 | 14 | 138 (90,8%) |
| b | 172 | 9 | 163 (94,8%) |
| c | 172 | 9 | 163 (94,8%) |

Se reprodujeron las 152 consultas originales en CPU, con cuatro hilos, sin caché
y con `functools.lru_cache(maxsize=128)`. En cada una de tres pasadas se vació la
caché; se comparó la salida completa, incluidos texto y orden de los párrafos.
Las salidas fueron idénticas. Los tiempos y su mediana están en
`corridas/cache-rag.json`; excluyen cargar el modelo.

La mediana fue **6,081 s sin caché y 0,541 s con caché**, una aceleración de
**11,24 veces del buscador** en esta máquina. Las 152 consultas requirieron
14 recuperaciones efectivas y 138 reutilizaciones en cada pasada.

Esto mide el buscador local con consultas grabadas. No mide el tiempo completo
del agente, el comportamiento con consultas nuevas ni la aceleración en la A100.
Este resultado llevó a incorporar la caché a `BuscadorHibrido`; `evaluacion.validar_cache`
y `evaluacion.validar_trazas` comprueban que no cambia los resultados en original, b y c.

## Cómo reproducir

Desde la raíz del repo, con el kit de la cátedra al lado, como en el README:

```bash
PYTHONPATH=../talksmith-ing/missions/TPFinal:. uv run --no-project --python 3.12 \
  --with sentence-transformers==6.2.0 --with torch==2.15.0 \
  --with transformers==5.23.0 --with numpy==2.5.5 --with pyyaml==6.0.3 \
  python -m evaluacion.diagnostico_rag

PYTHONPATH=../talksmith-ing/missions/TPFinal:. uv run --no-project --python 3.12 \
  --with sentence-transformers==6.2.0 --with torch==2.15.0 \
  --with transformers==5.23.0 --with numpy==2.5.5 --with pyyaml==6.0.3 \
  python -m evaluacion.cache_rag
```

El primer uso descarga bge-m3. Con sus archivos ya descargados se pueden ejecutar
los comandos con `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1` para impedir accesos
a Hugging Face. Se usó un entorno temporal de uv; no se cambió `uv.lock`.

Archivos reproducibles:

- `diagnostico_rag.py`: métricas, auditoría y comparación de fragmentación.
- `consultas_rag_adicionales.json`: consultas manuales y referencias por párrafo.
- `cache_rag.py`: prueba de reutilización exacta y tiempos de tres pasadas.
- `corridas/diagnostico-rag.json`: métricas completas, versiones, revisión y hashes.
- `corridas/cache-rag.json`: tiempos, controles de igualdad y hashes.

Los scripts incluyen asserts para las referencias, la selección de secciones y
la igualdad de las respuestas con caché. No se ejecutó el modelo del agente,
ningún entrenamiento ni recursos pagos de Modal.
