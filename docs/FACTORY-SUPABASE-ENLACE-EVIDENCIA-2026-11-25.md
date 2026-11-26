# Evidencia del enlace Factory en Supabase — 25 de noviembre de 2026 (CDMX)

Estado: **prueba observada**. Este informe registra una sesión del portal de soporte en GitHub Pages y Supabase. No describe el heartbeat de la D1 del ChatGPT Site: son sistemas de datos diferentes. No contiene tokens, códigos locales, credenciales, mensajes ni identificadores de clientes.

## Alcance y fuente

- Proyecto Supabase `compressos-agent-factory`, región us-east-1, activo al consultar. Consulta de solo lectura a tablas públicas y metadatos; no se cambió la base.
- Cliente Linux: puente Python 3.8+ en `127.0.0.1:7890`, iniciado por el usuario con `FACTORY_ALLOW_SERVICE_CONTROL=0` y `FACTORY_ALLOW_REMOTE_DIAGNOSTICS=1`. El cliente y el técnico en celular reportaron conexión estable.
- La rama `factory-compressos` publica el portal en GitHub Pages. El ChatGPT Site de Factory sigue siendo un despliegue distinto.

## Resultado observado

| Comprobación | Evidencia de Supabase | Límite |
| --- | --- | --- |
| Sesión | 1 fila de lobby `active`; otras 6 `waiting` | Una fila activa no prueba instalación permanente. |
| Enlace | 1 agente `active/session_only`, revisión de control 1, no revocado; permiso de diagnóstico verdadero, permiso de servicio falso | La activación es de sesión; no se inició ni detuvo un servicio Linux. |
| Primera señal | `last_heartbeat` se actualizó durante la consulta, por última vez a las 03:23:43 UTC del 26 de noviembre (21:23:43 CDMX del 25). | No es un heartbeat en D1 del Site. |
| Métricas | Campos `cpu_percent`, `ram_percent`, `disk_percent`, `services` presentes. Lectura puntual: CPU 3,3 %, RAM 46,1 %, disco 88,9 %. | Una muestra no determina rendimiento sostenido. |
| Diagnósticos | 10 tareas `completed`: status 3, uptime 2, disk 2, systemctl 1, swapon 1 y hal_metrics 1. | `completed` acredita respuesta de tarea, no éxito de cada comando; revisar `result_json` si se requiere. |
| Mensajería | 14 filas: 11 del cliente y 3 del técnico. | No se reproducen contenidos. |
| Auditoría | 4 eventos: dos `token_issued`, un `device_link_requested`, un `control_requested`. | No se observó una auditoría de servicio iniciado. |

### Scorecard adjunto por el usuario

El archivo `device-scorecard.json` marca 2026-11-26T03:27:49.220Z (21:27:49 CDMX del día 25), Firefox en Linux x86_64, DPR 1, lienzo CSS 421 × 236, `c2d_fps: 60`, `webgl_fps: 60` y `cpu: 4791`. El último campo no define unidad ni algoritmo; no equivale a `cpu_percent` del agente. La medición de FPS es una observación del navegador, no una prueba de GPU, estabilidad temporal ni del enlace remoto.

## Pendientes y reproducción

1. En un navegador nuevo repetir mensaje cliente → técnico → respuesta y comprobar el mismo hilo en Supabase.
2. Leer `result_json` de cada diagnóstico autorizado para distinguir tarea completada de comando exitoso; no imprimir secretos.
3. Finalizar la sesión y comprobar `stopped` y expiración; renovar el token y verificar que el anterior ya no sirve.
4. Mantener desactivado el control de servicios hasta instalar el helper local y otorgar consentimiento específico.
5. Si se necesita continuidad D1 ↔ Supabase, diseñar una sincronización explícita. La D1 del Site no se llena automáticamente por este puente.
