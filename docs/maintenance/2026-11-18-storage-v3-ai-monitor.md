# Incidente de almacenamiento V1–V3 — Linux Mint / CompressOS

**Fecha de cierre diagnóstico:** 2026-11-18 (CST). **Equipo:** Linux Mint 22.3 Zena XFCE; Ryzen 5 3600, 15 GiB RAM, AMD Navi 24 (amdgpu), raíz ext4 `/dev/nvme0n1p2` 217G. **Alcance:** evidencia operativa aportada en sesiones de mantenimiento; no equivale a telemetría continua. **Uso futuro:** casos de prueba y especificación inicial de CompressOS IA Monitor. No incluye cambios de código, servicios o limpieza adicional.

## Cronología y grado de evidencia

| Fecha | Evento | Evidencia / límites |
|---|---|---|
| 12 nov | Pruebas de memoria de CompressOS: ZRAM LZ4 ~7.8G, swap de disco ~6.3G; contadores de intercambio y diagnóstico `compressoctl doctor`. | Observaciones de terminal. El mensaje CRITICAL anterior se relacionaba con la discrepancia `/zram0` frente a `/dev/zram0`, no demuestra que ZRAM estuviera inactiva. |
| 12–17 nov | Instalaciones, cargas y pruebas locales de Lemonade, SDXL Turbo, SDXL Base, SD 1.5, SD Turbo, Anything V5, Anima y modelos de texto; Vulkan y escalado de imágenes. | Secuencia de trabajo documentada; no existe un inventario completo de bytes descargados por día. |
| 17 nov, ~21:14–21:22 | Logs de Lemonade: descarga de memoria/evicción de SDXL Turbo del backend Vulkan, carga de Anything V5 y posterior evicción. | Evicción del modelo en memoria **no significa borrado del modelo en disco**. |
| 17–18 nov | Mantenimiento anterior: raíz ~205G usados; Timeshift ~88G; `/var` ~75G; `/home` ~36G. Eliminación de snapshots del 12 al 15 nov; después ~27G libres. | Lecturas de terminal; no extrapolar diferencias de tamaños como descargas exactas. |
| 18 nov, V3 | Saturación de raíz: 217G, 210–216G usados, 0 disponible; inodos ~10% ocupados. Timeshift ~102–109G aparentes, `/var` 66G, `/home` 34G. | `df`, `du`, `free`; valores redondeados y en distintos instantes. |
| 18 nov, V3 | En Timeshift RSYNC se encontraron dos instantáneas: 2026-11-16_13-00-01 (diaria) y 2026-11-18_16-00-01 (semanal). Timeshift almacena en la misma partición raíz. | El tamaño `du` de instantáneas con hardlinks **no equivale a espacio exclusivo recuperable**. |
| 18 nov, V3 | Eliminación mediante `timeshift --delete --snapshot '2026-11-16_13-00-01'`. Raíz pasó a 182G usados, 25G disponibles (88%); recuperación estimada ~34G respecto a lectura anterior. | Resultado comprobado con `df -h /`; no se borraron modelos. |
| 18 nov, V3 | Instantánea restante 2026-11-18_16-00-01 ~74G aparentes. Su árbol `var/lib/lemonade` ~58G y `var/cache/lemonade` ~6.4G; `var` total ~66G. | Tamaños aparentes de respaldo, **no** 64.4G de espacio físico duplicado necesariamente. |
| 18 nov, V3 | En `/etc/timeshift/timeshift.json` se añadieron `/var/lib/lemonade/**` y `/var/cache/lemonade/**`; copia `/etc/timeshift/timeshift.json.backup-20261118-161353`. | Configuración persistida, **aún no validada** en una instantánea nueva. |
| 18 nov, V3 | Kernel activo 7.0.0-43; alternativo 6.14.0-37. Simulación APT de purga: 5 paquetes antiguos, sin dependencias adicionales propuestas. Se decidió **no purgar** para conservar fallback. | Simulación, no ejecución. |
| 18 nov, V3 | `compresso-memoryd` habilitado, `active (exited)`, SUCCESS; `compresso-supervisord` y `compresso-metricsd` deshabilitados e inactivos; journal sin warnings recientes. `amdgpu` y `zram` cargados. | No implica prueba de inferencia Vulkan ni de restauración Timeshift. |

## Causas, factores y datos pendientes

1. **Causa demostrada del crecimiento de los respaldos:** Timeshift RSYNC incluye directorios voluminosos de Lemonade, porque originalmente solo excluía `/home/x4rim4x/**` y `/root/**`. Las instantáneas residen en el mismo volumen de 217G. Los hardlinks complican atribuir el uso físico a cada snapshot.
2. **Consumo base de modelos y aplicaciones:** `/var/lib/lemonade` ~58G, caché `/var/cache/lemonade` ~6.4–6.5G. En `/home` se observaron Trellis Studio ~16G y AnythingLLM Desktop ~11G. Los modelos no se eliminaron.
3. **Cachés adicionales:** navegador Firefox/Chromium, perfiles, miniaturas, compilación Vulkan, logs y APT pueden crecer por pruebas y navegación. **No hay medición por ruta ni prueba de que la caché del navegador causara la saturación.** La interacción con ChatGPT puede generar caché, pero no cuantificarla sin diagnóstico.
4. **No fue agotamiento de RAM:** `free -h` mostró ~10GiB disponibles; ZRAM ~7.8G, ~618MiB usados, prioridad 100; swap en NVMe ~6.3G, 0B usados. `df` mostró el verdadero cuello de botella.
5. **Duración:** existen mediciones y acciones entre el 12 y 18 de noviembre, con episodios documentados de limpieza el 17–18. No se conoce el instante exacto de inicio de cada acumulación ni la duración continua del 100% de uso.

## Política operativa del futuro IA Monitor

**Recolectar en modo lectura:** `df -B1 /`, `df -i /`, `free -b`, `swapon --show --bytes`, `zramctl`, `findmnt`, `uname -r`, `du` limitado a rutas permitidas, `journalctl --disk-usage`, `timeshift --list`, paquetes kernel instalados, estado de servicios y métricas de directorios de modelos/cachés. Muestrear series temporales con marca de tiempo, host, filesystem, unidades y versión de software. Para navegador, medir solo **tamaños agregados** de directorios de caché por perfil; no leer cookies, historial, credenciales ni contenido de sesiones.

**Correlacionar:** cambios de uso libre con eventos de descarga, carga de modelo, generación de imágenes, actualización, creación de snapshots y crecimiento de cachés. Distinguir `RAM disponible` de `disco disponible`, `modelo cargado en RAM/VRAM` de `modelo almacenado`, y tamaño aparente de snapshot de bloques exclusivos. Registrar intervalos y confianza de causalidad; no adjudicar bytes a una descarga sin medición antes/después.

**Alertar:** advertencia bajo 15% libre, crítica bajo 10% o 10 GiB libres (umbrales configurables; aquí 25G/217G ≈11.5%, advertencia). Detectar snapshots en misma partición, crecimiento acelerado, exclusiones ausentes, falta de respaldo verificable y ausencia de kernel alternativo. La reserva ext4 puede hacer que `df` muestre 0 disponible antes de agotarse todos los bloques; nunca modificarla automáticamente.

**Acciones permitidas sin aprobación:** diagnóstico, clasificación, informe, predicción de agotamiento, propuesta de exclusiones y simulación de paquetes. **Requieren aprobación explícita:** eliminar snapshots, limpiar cachés, purgar kernels, cambiar Timeshift, modificar swap/ZRAM o detener servicios. No borrar modelos, LoRA, outputs, proyectos, datos de usuario, logs de evidencia ni el último respaldo de recuperación automáticamente. Validar árbol de dependencias y posibilidad de reversión antes de actuar.

**Casos de prueba iniciales:**
- Raíz al 100%, RAM disponible ~10GiB → alerta DISCO, no OOM.
- Dos snapshots con hardlinks → no sumar `du` como espacio recuperable.
- Snapshot incluye modelos 58G y caché 6.4G → sugerir exclusiones futuras; conservar original.
- Exclusión escrita pero sin snapshot nuevo → estado PENDIENTE_DE_VALIDACIÓN.
- `amdgpu` cargado → controlador presente, NO inferencia Vulkan validada.
- Servicios systemd `disabled/inactive` → no reportar fallo sin política de habilitación.
- Caché navegador sin medición → factor POSIBLE, no causa CONFIRMADA.
- `apt-get -s purge` retira cinco paquetes → propuesta, no autorización de ejecución.

## Próximas verificaciones

1. Medir cachés de Firefox/Chromium y otros consumidores sin leer datos privados ni borrar nada.
2. Verificar las reglas de exclusión de Timeshift en una nueva instantánea cuando exista espacio suficiente y un plan para conservar restauración.
3. Validar restaurabilidad del respaldo y prueba de inferencia Vulkan por separado.
4. Instrumentar métricas de crecimiento y eventos en el monitor, con almacenamiento limitado y rotación de logs.
5. Conservar investigación CompressOS-Research-Hardware-Lab (OpenWorld, AURKNIX, Yocto) fuera de este mantenimiento.

**Resultado V3:** ~34G recuperados; 25G libres; kernel alternativo, modelos, ZRAM y respaldo semanal conservados. No se declara que el problema futuro esté completamente resuelto hasta verificar exclusiones y tendencias.
