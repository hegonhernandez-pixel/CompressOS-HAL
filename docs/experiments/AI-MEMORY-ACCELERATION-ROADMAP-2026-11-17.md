# CompressOS — plan de aceleración y observador IA

Fecha de registro: 2026-11-17 (hora local del laboratorio).  
Rama de investigación: `exp/volatile-memory-shader-pipeline`.  
Estado: propuesta documentada; no implica implementación ni validación de aceleración.

## Alcance y objetivos

Investigar una ruta de procesamiento de datos en memoria RAM -> Vulkan/shader -> RAM, y la gestión adaptativa de RAM, VRAM, GTT, ZRAM, Zswap y swap NVMe. Separar estrictamente la compresión real de swap Linux de los experimentos de buffers Vulkan: GTT no es VRAM física adicional, y ZRAM no es memoria GPU. Medir primero; optimizar únicamente con pruebas reproducibles y reversibles.

## Evidencia existente que no debe perderse

- `docs/experiments/ZRAM-FAST-BASELINE-2026-11-14.md`: ensayo físico ZRAM/LZ4 con `stress-ng`, 13 GiB/60 s, sin OOM; conservar intacto.
- Monitor local provisional: `~/Documentos/CompressOS-AI-Monitor/monitor.sh`; CSV `memory-20261117-220947.csv` (222 líneas, incluida cabecera). La muestra reporta RAM disponible, swap libre, ZRAM datos/comprimido, VRAM y GTT. Aún no se ha incorporado al repositorio ni se ha revisado su código completo.
- SDXL Turbo y Remotion: objetivos de pruebas de imagen y render de video, respectivamente. Remotion produce movimiento a partir de imágenes; no es generación de video nativa con SDXL Turbo.
- Anything V5 + LoRA: pruebas suspendidas tras fallos SIGSEGV/SIGABRT en sd-cpp Vulkan; no reactivar como parte de esta campaña. Descarga de memoria confirmada por `lemonade unload anything-V5`.
- Codex, Gemini CLI y OpenCode: ejecutables presentes en el equipo. Existe `~/CompressOS-Memory/shared/memory.jsonl` (114 bytes); las conexiones MCP y la colaboración efectiva entre agentes NO están verificadas.
- Lemonade 2026.48 y modelos locales: integración pendiente de comprobación; la lista de modelos instalados no implica que estén cargados ni que sean aptos como observadores.

## Diseño propuesto

1. **Telemetría determinista, solo lectura:** CSV/JSON con marcas de tiempo, RAM disponible, VRAM/GTT, ZRAM, Zswap si existe, actividad de swap, procesos, eventos OOM y tiempos de generación. Identificar valores ausentes como `NA`; no inventar mediciones.
2. **Observador IA local:** proceso `ai_observer.py` separado del monitor; calcula estadísticas deterministas y solicita a un modelo de Lemonade una interpretación y recomendaciones con evidencia. No ejecutar comandos propuestos por la IA. Preferir análisis fuera de la ventana de carga para no sesgar el benchmark.
3. **Orquestación multiagente opcional:** validar MCP y permisos de Codex/Gemini/OpenCode antes de compartir informes; memoria compartida es un recurso local, no material para Git.
4. **Investigación de aceleración:** benchmark aislado RAM -> shader Vulkan -> RAM, comparado contra alternativa CPU; medir transferencia, latencia, throughput, presión de memoria y coste energético si hay datos fiables. No alterar el kernel ni el swap de producción en la fase de observación.
5. **Puerta de seguridad:** pruebas unitarias, integración local, recuperación de errores, métricas antes/después y autorización humana explícita para cualquier cambio activo de memoria.

## Calendario tentativo (no son validaciones)

| Fecha objetivo | Entregable | Estado |
|---|---|---|
| 18 nov 2026 | Inventario de ramas, preservar evidencia, revisar monitor y baseline | En progreso |
| 19 nov | Dos imágenes SDXL Turbo con monitor, tiempos y logs | Pendiente |
| 20 nov | Render corto Remotion con monitor y logs | Pendiente |
| 21 nov | Prueba controlada del modelo local observador y contrato JSON | Pendiente |
| 22 nov | Informe de IA contrastado con estadísticas verificables | Pendiente |
| 23–24 nov | Verificar MCP multiagente y documentar recomendaciones | Pendiente |
| 25–26 nov | Prototipo de benchmark RAM/Vulkan y comparativa sin ajustes automáticos | Pendiente |
| 27 nov | Revisión de estabilidad y decisión de pasar a testers | Pendiente |

## Organización y preservación

- **No crear más ramas** para esta línea de investigación hasta revisar el inventario actual.
- Esta rama es experimental y está divergida de `main`; no hacer merge, rebase ni force-push sin revisión.
- Separar CompressOS-HAL (núcleo técnico privado) de la plataforma comercial y los servicios de clientes.
- Mantener README/CHANGELOG y `docs/IMPLEMENTATION-STATUS.md` sincronizados cuando se implementen módulos, no antes.
- No versionar CSV con datos del host, rutas sensibles, memoria MCP, tokens, modelos ni logs privados.
- Registrar por cada prueba: fecha, comando, versión, hardware, parámetros, resultado, evidencia, commit y criterio de aceptación.
- Revisar ramas existentes antes de archivar o eliminar alguna; los nombres por sí solos no prueban que CodeRabbit las haya creado.

## Criterios para considerar la fase validada

- Monitor reproducible con datos completos y tolerancia a sensores ausentes.
- Observador IA produce recomendaciones respaldadas por métricas; errores y alucinaciones se registran.
- Integración MCP verificada con pruebas de lectura y límites de permisos.
- Benchmark con línea base, repeticiones, tiempos, uso de RAM/VRAM/GTT y sin regresiones críticas.
- Ninguna afirmación de aceleración comercial sin resultados reproducibles.
