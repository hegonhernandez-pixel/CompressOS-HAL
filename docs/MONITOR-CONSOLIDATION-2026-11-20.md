# Consolidación del monitor residente · 2026-11-20

**Alcance:** inventario, pruebas y criterios de aceptación del monitor para Linux Mint 22.3 Xfce. La investigación Fast RAM a nivel kernel permanece separada de este agente operativo.

## Evidencia disponible

- **Reportado en sesiones anteriores:** `compresso-monitor-agent` estuvo activo; ZRAM alrededor de 7.8 GiB, swap NVMe alrededor de 6.3 GiB y Zswap deshabilitado en una observación. Repetir lectura en el equipo antes de inferir estado actual.
- **Revisión de Moose, 20-nov:** HAL se mantiene separado del puente MCP de Agent Factory. La revisión fue documental; no certificó telemetría en el equipo.
- **Pendiente:** mediciones sincronizadas de CPU, RAM, GPU/VRAM/GTT cuando el controlador las exponga, ZRAM, Zswap, swap, disco, latencia y consumo del propio agente. No equiparar memoria reservada, comprimida y liberada.
- **Pendiente:** distinguir una recomendación externa de cambios que exigirían instrumentar un motor de inferencia o Vulkan.

## Checklist de cierre

- [ ] Inventariar código, versión, configuración y unidades systemd realmente instaladas; vincular rama/commit.
- [ ] Capturar estado en reposo y con dos cargas reproducibles; anotar modelo, backend, parámetros, duración, p50/p95, errores y uso de recursos.
- [ ] Confirmar origen y permisos de cada métrica, frecuencia de muestreo, datos faltantes y sobrecarga.
- [ ] Definir umbrales, alertas, recuperación permitida, registro de antes/después y reversión.
- [ ] Ensayar fallos controlados de servicios y ausencia de telemetría sin publicar credenciales ni alterar swap automáticamente.
- [ ] Revisar resultados y límites antes de integrar el monitor como capacidad de Factory o vender soporte basado en él.

**Criterio de validación:** evidencia reproducible en hardware objetivo, pruebas focalizadas, logs y referencia de commit/PR; hasta entonces el estado es **pendiente de consolidación**.

La documentación comercial y el catálogo se registran por separado en `exp/business-model-launch`.
