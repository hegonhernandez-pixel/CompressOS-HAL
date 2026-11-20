# Agent Factory — decisiones y consolidación · 2026-11-20

Este registro complementa `LAUNCH-ROADMAP.md`. Las decisiones más recientes prevalecen donde el documento de 14 de noviembre difiere. Estado de las afirmaciones: **decidido**, **observado**, **reportado** o **pendiente**.

## Decisiones vigentes

- **Decidido:** la prioridad comercial es crear, administrar y ofrecer agentes de IA con instalación, mantenimiento y soporte. La producción de esta línea se concentra en **Linux**; las secciones anteriores de Windows del roadmap quedan históricas y requieren revisión antes de usarse.
- **Decidido:** mantener separadas Agent Factory, el núcleo de investigación Fast RAM de HAL y las investigaciones de hardware de Arcade.
- **Decidido:** la campaña SDXL Turbo de generación de imágenes quedó cerrada por ahora. Sus pruebas son evidencia técnica, no una oferta comercial validada.
- **Reportado por el usuario:** ya envió a revisión su mensaje de reclamación sobre Google Cloud/Gemini. La recepción, la respuesta y la solución no han sido verificadas aquí. No dar por resuelta la facturación ni usar Cloud Run como decisión cerrada.

## Catálogo y operación

| Estado | Oferta o capacidad | Condición para avanzar |
|---|---|---|
| Diseño para piloto | Creación y administración de agentes Linux para clientes; inventario de equipo, instalación reproducible, mantenimiento, soporte y escalamiento | Definir primer perfil, agente, alcance, precio, contrato, diagnóstico y prueba de aceptación |
| Capacidad interna inicial | ChatGPT Work coordinando investigación, decisiones y Site privado de Factory | Mantener bitácora y evidencia; no presentarlo como inferencia autónoma desplegada en el cliente |
| Candidato técnico | AnythingLLM y motor local Lemonade/Qwen | Verificar instalación, API, autenticación, recursos, latencia, permisos y conectividad antes de integrarlo |
| Fuera del catálogo actual | Fast RAM, optimizaciones GPU no medidas, firmware Arcade y producto de imágenes | Investigación y evidencia independientes; no prometer resultados comerciales |

Flujo esperado: solicitud → ficha de cliente y máquina → elección de agente y perfil → instalación versionada → prueba de aceptación → monitor y logs → mantenimiento → escalamiento humano cuando proceda. Registrar cada intervención, costo real y límites del servicio.

## Alojamiento y seguridad pendientes

La revisión documental de Moose (20-nov) encontró un servidor Express experimental en `MASTERCODE-MCP`, sin MCP remoto HTTP verificado y con `package.json` ausente en la revisión. La arquitectura del puente, el alojamiento, la autenticación, la facturación y las pruebas siguen pendientes. No publicar rutas internas, secretos, administración ni documentación privada. El Site actual coordina la implementación; no prueba por sí solo que el backend MCP o AnythingLLM estén conectados.

## Checklist verificable

- [ ] Consolidar Factory: catálogo sí/no, precios y límites, instalación, cliente/equipo, soporte, rollback y mantenimiento.
- [ ] Consolidar el monitor residente en su rama técnica: telemetría real, umbrales, alertas, seguridad y pruebas bajo carga.
- [ ] Confirmar alojamiento y acceso al servidor MCP; resolver bloqueos de facturación sin asumir créditos.
- [ ] Integrar el primer motor local solo después de verificar API, autenticación y red segura.
- [ ] Mantener un registro por fecha, rama, commit, fuente, prueba, resultado y pendiente; enlazar PR cuando exista.

No se declaran completas estas tareas ni se afirma que la reclamación a Google haya sido resuelta.
