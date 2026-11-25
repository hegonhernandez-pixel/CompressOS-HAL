# Historial de CompressOS Agent Factory

## 2026-11-25

- Añadido acceso técnico con Google condicionado a la configuración del proveedor en Supabase.
- Documentadas el alta y la revocación desde SQL Editor y la conexión inicial de una computadora.
- Las tablas privadas de técnicos y credenciales quedan fuera de Realtime. El portal conserva las cinco tablas operativas.

## 2026-11-23

- GitHub Pages publica el portal público desde `factory-compressos`, en la raíz. [Portal](https://hegonhernandez-pixel.github.io/CompressOS-HAL/) · [Acceso técnico](https://hegonhernandez-pixel.github.io/CompressOS-HAL/?rol=tecnico)
- `mensajes.html` lleva al chat de soporte del portal. La sala interna del equipo sigue en el ChatGPT Site privado.
- El portal explica cuándo Supabase tiene deshabilitado el ingreso de visitantes. El comando de arranque propone diagnóstico y deja deshabilitado el control de servicios.
- El agente ya permite el origen de Pages. Su opción `--origin` acepta únicamente orígenes de desarrollo en localhost.
- Pendiente de aceptación: habilitar el ingreso público de visitantes con protección contra abuso y probar el chat y el agente entre Mint y el celular.

## Integración inicial del portal

- `96f8c39` unificó el portal de soporte y el Laboratorio de IA.
- `a3ae824` documentó la activación de Supabase y Linux.
- `44d2ed8` conectó la configuración del portal al proyecto de Supabase.
- `cbfc877`, `930be02`, `03c57b2` y `8b49c5b` separaron las entradas y documentaron GitHub Pages.
