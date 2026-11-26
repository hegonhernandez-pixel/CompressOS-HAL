# Conciliación de fuentes Factory / HAL — 25 de noviembre de 2026 (CDMX)

Objetivo: conservar el trabajo antes de sincronizar una computadora. Inventario de solo lectura salvo los dos commits de documentación de esta revisión. No hubo merge, despliegue nuevo ni modificación de Supabase.

| Superficie | Estado verificado | Relación |
| --- | --- | --- |
| GitHub `CompressOS-HAL` | Repositorio **público**; rama por defecto `main`. Rama `factory-compressos` con portal GitHub Pages, `agent.py`, esquema Supabase y guías. Antes de documentar: 31 commits por delante y 4 detrás de `main`, base común `36987d01`; `main` en `14f1b778`. | El portal está separado en la rama, pero la visibilidad pública aplica al repositorio entero. Revisar IP y secretos antes de mantener HAL público. |
| GitHub Pages | Guía de la rama documenta publicación de `factory-compressos` en la raíz y URL `https://hegonhernandez-pixel.github.io/CompressOS-HAL/`. | Portal cliente/técnico servido desde GitHub; requiere comprobar estado de Actions/Settings para cada commit posterior. |
| ChatGPT Site Factory | Versión publicada **V14**, fuente `c83fc0409fec7c1615aba3a01ddcfd3cc28d270f`; V13 `0b5622ce`, V12 `44e1e020`. El Site conserva su D1 y MCP propios. | La copia de código disponible en el espacio de trabajo de Codex estaba en `44e1e020` (V12): **no usarla para sobrescribir V14**. |
| Supabase | Proyecto `compressos-agent-factory` activo; seis tablas públicas operativas con RLS. `factory_private` guarda acceso técnico, pares y credenciales. Una sesión activa con heartbeat y diagnósticos; ver evidencia adjunta. | Es la fuente de verdad del túnel de soporte actual. Las tablas de D1 del Site no reciben ese heartbeat automáticamente. |
| Pages de ChatGPT | La búsqueda de páginas personales por “CompressOS” no devolvió resultados. El listado personal accesible mostró una página vacía y no se hallaron Spaces accesibles. | Esto no demuestra que el contenido histórico no exista; se requiere una URL o acceso al espacio correcto para conciliarlo. |
| PC Linux Mint | Solo se recibió salida de terminal del puente y reporte del usuario. El espacio de trabajo de Codex no es la PC Mint y no permite leer su `git status`, archivos sin commit ni ramas locales. | **Estado local de la PC pendiente de inspección.** No hacer `git reset --hard`, `git clean` ni pull automático. |

## Cambios registrados y límites

- El repositorio HAL es público (confirmado por GitHub). La razón operativa reportada fue habilitar la URL pública del portal; la rama `factory-compressos` contiene los archivos distribuibles, pero no es una frontera de privacidad para el resto del repositorio.
- El técnico y cliente completaron un enlace de sesión mediante Supabase y el puente local; los datos de aceptación se detallan en `docs/FACTORY-SUPABASE-ENLACE-EVIDENCIA-2026-11-25.md`.
- El acceso Google está documentado como opcional y condicionado al proveedor OAuth. La base consultada mostró una identidad de proveedor `email` y ninguna `google`; el inicio con Google queda **sin verificar**. No existe evidencia de que Google sea una vía automática de alta de un técnico. La autorización técnica se controla aparte en `factory_private.technicians`.
- El token de emparejamiento y el código local son temporales; no deben incluirse en documentación, commits ni capturas. La clave `sb_publishable_` del portal es pública por diseño; RLS y funciones RPC establecen el alcance, no la ocultación de esa clave.
- Las tablas `factory_heartbeat_history` de D1 y `factory_agents.last_heartbeat` de Supabase son sistemas distintos. No migrar ni borrar registros sin un mapeo de identidad, autorización y auditoría.

## Ruta segura para actualizar la PC Mint

Desde el clon existente, **antes de actualizar**:

```sh
cd ~/CompressOS-HAL
git status --short --branch
git remote -v
git branch -vv
git fetch origin
git log --oneline --decorate --graph --all -20
git rev-list --left-right --count HEAD...origin/factory-compressos
```

Si `git status` muestra archivos locales, crear una rama de respaldo y un commit local revisado o una copia externa antes de integrar. Si la rama local es `factory-compressos` y no tiene commits propios ni cambios pendientes, entonces `git pull --ff-only origin factory-compressos` trae estos dos commits. Si diverge, comparar `git diff` y conciliar cambios uno por uno; **no** forzar la rama. Tampoco mezclar automáticamente `main` con `factory-compressos`: había 4 commits nuevos en `main` y 31 exclusivos en Factory antes de esta documentación.

## Siguientes decisiones

1. Auditar qué archivos del núcleo HAL y qué historial quedaron públicos; decidir si mantener el repositorio así o separar el portal distribuible en un repositorio público independiente. Cambiar visibilidad requiere revisar enlaces Pages y distribución.
2. Capturar el estado real de `~/CompressOS-HAL` y `~/Descargas/agent.py` en Mint antes de sincronizar.
3. Localizar las páginas históricas con URL o Space ID y contrastar sus versiones con GitHub y Site V14; preservar las que contengan decisiones o pruebas únicas.
4. Definir si se necesita integrar telemetría Supabase con el Monitor del Site; hacerlo como cambio explícito con pruebas de autorización y no mediante copia manual de tokens.
