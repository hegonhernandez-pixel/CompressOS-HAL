# SDXL Turbo FP16 en AMD RX 6500 XT (4 GiB) — cierre de pruebas

**Fecha de registro:** 2026-11-19  
**Estado:** Pruebas operativas concluidas por ahora; resultados reportados y medidos, sin atribución causal definitiva.  
**Alcance:** Investigación secundaria de CompressOS-HAL. Prioridad de producto: CompressOS Agent Factory.

## Entorno

- Linux Mint 22.3 Zena XFCE.
- CPU AMD Ryzen 5 3600 (6 núcleos físicos / 12 hilos lógicos).
- GPU AMD Radeon RX 6500 XT (RADV NAVI24), 4080 MiB de VRAM reportados por amdgpu.
- RAM física aproximadamente 15 GiB.
- Lemonade + `sd-cpp` backend Vulkan0; modelo `sd_xl_turbo_1.0_fp16.safetensors`.
- Ejecución observada: `sd-server --listen-port 8001 ... --vae-tiling --diffusion-fa --threads 8 --backend Vulkan0`. **Los 8 hilos son un ajuste manual del operador**, no una limitación por defecto demostrada del motor.
- Configuración de imagen de pruebas comparables: 512×512, 4 pasos, CFG 1, semilla 42, prompt de gato naranja.

## Resultados observados

| Prueba | ZRAM | Zswap | Tiempo de generación | Observación |
|---|---|---|---:|---|
| A0 | Activa | Desactivada | 50.85 s | Generación completada |
| A | Desactivada | Desactivada | 47.97 s | Generación completada; ralentización del cursor/escritorio reportada |
| B | Activa | Desactivada | 48.52 s | Generación completada; escritorio fluido reportado |

- Durante B: uso GPU máximo observado ~99%; VRAM máximo observado ~2.72 GiB; GTT máximo observado ~6.61 GiB; RAM disponible ~5.8–6 GiB.
- Swap sin actividad relevante; ZRAM reportó ~4096 bytes de datos originales, ~64 bytes comprimidos y ~20480 bytes asignados en la medición. Esto **no demuestra** compresión de gigabytes del modelo mediante ZRAM.
- Medición posterior en reposo: `sd-server` RSS 185.50 MiB, PSS 152.61 MiB; Firefox PSS 1967.42 MiB. No representan máximos durante generación.
- Registro de arranque de amdgpu: 4080 MiB de VRAM y 7937 MiB de GTT **disponibles/capacidad**, no consumo real de SDXL Turbo.
- No sumar automáticamente VRAM + GTT + RSS/PSS: hay posibles solapamientos y asignaciones GTT que no necesariamente equivalen a residencia física.
- El operador reportó que también ejecutaba otra IA en segundo plano durante parte de las pruebas anteriores, posible fuente de competencia por recursos y fallos de generación; causalidad no verificada.

## Valor del resultado

Se consiguió generar imágenes con SDXL Turbo FP16 mediante Vulkan en una GPU de consumo con 4 GiB VRAM, manteniendo usabilidad del escritorio en las pruebas con ZRAM activa. Es un **logro operativo comprobado** en esta configuración, sin afirmar que la causa exclusiva de la fluidez sea ZRAM o CompressOS.

## Estado de documentación externa

**No se identificó en la investigación realizada un benchmark publicado exactamente equivalente** que documente simultáneamente RX 6500 XT 4 GiB + Linux Mint 22.3 XFCE + Lemonade/`sd-cpp` Vulkan + SDXL Turbo FP16 y la interactividad del escritorio. Esto **no equivale a demostrar que no exista** documentación o que la tarjeta esté universalmente excluida del soporte. No usar benchmarks de A100/H100/TensorRT como comparación directa.

## Cierre y continuidad

- Campaña de generación de imágenes: **pausada/cerrada para el flujo actual**, sin nuevas pruebas solicitadas.
- No declarar validación de producción, mejora causal exclusiva ni compatibilidad universal.
- Investigación futura de HAL: **Fast RAM**, concepto propio para estudiar reutilización de páginas/librerías entre procesos, políticas de compresión y posible aceleración GPU con integración al kernel. Distinguir mecanismos ya presentes en Linux (page cache, bibliotecas compartidas, copy-on-write, KSM, ZRAM/Zswap) de oportunidades adicionales medibles.
- Prioridad inmediata: **CompressOS Agent Factory** (creación y operación de agentes IA). Moose debe investigar arquitectura de agente residente para inventariar procesos, servicios y recursos de Linux Mint y producir un plan sin modificar código hasta autorización.
