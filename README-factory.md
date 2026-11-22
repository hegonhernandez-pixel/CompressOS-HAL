# CompressOS Agent Factory

Portal de soporte Linux, consola del técnico, mensajería y Laboratorio. El portal usa Supabase Auth y Postgres Changes. El agente usa HTTPS saliente para reclamar diagnósticos de una lista fija. El único servidor HTTP del agente escucha en 127.0.0.1. El estado «Túnel activo» representa un canal de soporte limitado a estas operaciones.

## Configurar el proyecto nuevo

1. Crea `compressos-agent-factory` en la organización `mozaxdepxhzkloylkbun`. Ejecuta `supabase_schema.sql` una vez con el editor SQL.
2. Habilita los inicios de sesión anónimos en Auth. Para una publicación abierta, configura los límites de Auth y la retención de cuentas de visitantes. Si habilitas CAPTCHA para Auth, integra su interfaz antes de habilitar el portal público.
3. Crea la cuenta del técnico en Auth. Usa su UUID de Auth en el editor SQL.

   ```sql
   insert into factory_private.technicians(user_id) values ('UUID_DEL_TÉCNICO');
   ```

4. Añade la URL HTTPS y la clave **publishable** o JWT **anon** del proyecto a `config.js`. La política RLS y la lista de técnicos se aplican en la base de datos. Mantén las claves privadas fuera de los archivos estáticos.
5. Sirve la raíz de `factory-compressos` con Pages. El Site existente ofrece la misma compilación en `/soporte/`, preservando las herramientas y la mensajería interna de Factory y Arcade en sus rutas originales.

## Probar en dos computadoras

1. Abre el portal en la computadora del usuario. Descarga `agent.py` y ejecuta el comando de la página como tu usuario Linux. Para una prueba local, sirve los estáticos con `python3 -m http.server 8000 --bind 127.0.0.1` y añade `--origin http://127.0.0.1:8000` al agente.
2. En otra computadora, abre `?rol=tecnico` e inicia sesión con la cuenta autorizada. Selecciona al visitante y envía el token.
3. En el equipo del usuario, copia el token del chat y el código de la terminal en sus campos respectivos, marca los permisos elegidos y solicita el enlace. Autoriza acceso a la red local si el navegador lo pide.
4. Pulsa **Activar** como técnico. Con permiso de diagnóstico, ejecuta `uptime` y revisa el resultado y la auditoría. Prueba Pausar, Detener y la revocación desde el portal. Tras cerrar el agente, comprueba que desapareció el archivo de credenciales y que una sesión ajena no puede leer el chat.
5. Los diagnósticos y la telemetría se limitan a la sesión vigente. El token de enlace vence a los cinco minutos y la sesión del agente tiene una duración máxima de una hora. Tras un reinicio del agente, solicita un token nuevo.

## Servicio local opcional

También puedes ejecutar el puente en una unidad transitoria de usuario. Configura primero `SUPABASE_URL` y `SUPABASE_ANON_KEY` con valores públicos y ejecuta el comando desde el directorio que contiene el agente.

```sh
systemd-run --user --unit=compressos-factory-agent --collect \
  --setenv="SUPABASE_URL=$SUPABASE_URL" --setenv="SUPABASE_ANON_KEY=$SUPABASE_ANON_KEY" \
  --setenv=FACTORY_ALLOW_REMOTE_DIAGNOSTICS=1 /usr/bin/python3 "$PWD/agent.py"
journalctl --user -u compressos-factory-agent -n 20 --no-pager
systemctl --user stop compressos-factory-agent
```

Para control de servicios, el administrador local instala previamente el helper adjunto, propiedad de root, en `/usr/local/sbin/compresso-factory-services`. Revisa que pertenezca a root y que conceda permisos sudo únicamente a los argumentos literales `start` y `stop` del helper. El permiso `FACTORY_ALLOW_SERVICE_CONTROL=1` habilita la opción de consentimiento en el puente. El helper opera sobre `compresso-metricsd.service` y `compresso-supervisord.service`. Si la estación carece de estas unidades, el agente puede usarse con permiso de diagnóstico y sin permiso de control local.

`--site` permite autorizar un origen adicional de ChatGPT Sites. El protocolo anterior del agente sigue disponible en el Site original. La bitácora del Laboratorio se conserva en el navegador y admite exportación e importación JSON.

## Origen y verificación

Los perfiles de IA y el flujo de la bitácora proceden de la versión 12 del Site privado. La rama recibe el portal, los perfiles, el agente, el esquema y la documentación de operación. La edición de registros operativos históricos sigue disponible en el Site privado. La clave pública no tiene permisos de técnico. Los técnicos y visitantes escriben por RPC y las lecturas se limitan con RLS. Los resultados de diagnósticos y el historial se almacenan en el proyecto nuevo cuando se configura.
