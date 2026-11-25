# CompressOS Agent Factory

Portal de soporte Linux, consola del técnico, mensajería y Laboratorio. El portal usa Supabase Auth y Postgres Changes. El agente usa HTTPS saliente para reclamar diagnósticos de una lista fija. El único servidor HTTP del agente escucha en 127.0.0.1. El estado «Túnel activo» representa un canal de soporte limitado a estas operaciones.

## Entradas y publicación en GitHub Pages

La entrada del cliente es la raíz del portal. Ahí están el chat y la preparación del equipo. La entrada del técnico añade `?rol=tecnico` y exige una cuenta autorizada. `laboratorio.html` abre los presets y la bitácora local del navegador. La ruta anterior `mensajes.html` lleva al chat de soporte. La sala interna de Factory y Arcade se administra en sus ChatGPT Sites privados.

1. En GitHub, abre **Settings → Pages → Build and deployment** con una cuenta administradora.
2. Selecciona **Deploy from a branch**, la rama **factory-compressos** y **/ (root)**. La rama tiene `index.html` en su raíz. Guarda y revisa la ejecución de Pages en **Actions**.
3. Cuando GitHub indique que el despliegue terminó, usa la URL que muestra **Visit site**. La URL esperada es `https://hegonhernandez-pixel.github.io/CompressOS-HAL/`. La vista del técnico agrega `?rol=tecnico`.
4. Si el repositorio privado no ofrece Pages o la visibilidad pública, comprueba el plan y las políticas de la cuenta. Conserva la visibilidad del repositorio. Para un despliegue público alternativo, publica únicamente los archivos del portal autorizados para distribución.
5. Opcionalmente, agrega la URL verificada como **Website** en **About** del repositorio. Ese enlace es independiente de la activación de Pages.

Antes de aceptar la prueba desde dos equipos, confirma que el visitante puede enviar un mensaje, que el técnico lo recibe desde el celular y que el visitante recibe su respuesta. El agente ya incluye el origen HTTPS de Pages. `--origin` se usa únicamente para desarrollo en localhost. Para la primera prueba basta el permiso de diagnóstico.

El historial de la rama está en [CHANGELOG-factory.md](./CHANGELOG-factory.md). Consulta también la [guía breve de acceso y conexión](./docs/FACTORY-ACCESO-TECNICO.md).

## Activación manual en Supabase

Configura un proyecto nuevo llamado `compressos-agent-factory` dentro de la organización `mozaxdepxhzkloylkbun`. Usa una cuenta de la organización con permiso para crear proyectos y administrar Auth y la base de datos. En **New project**, elige la región y el plan de la organización. Guarda la contraseña de la base de datos en tu gestor de contraseñas. El portal requiere la URL del proyecto y su clave pública.

| Pestaña | Acción |
| --- | --- |
| **SQL Editor → New query** | Abre `supabase_schema.sql`, copia el archivo completo y pulsa **Run** una vez en el proyecto nuevo. Crea tablas, funciones, políticas RLS y la publicación de los cambios. |
| **Authentication → Sign In / Providers** | Activa **Allow new users to sign up** y **Allow anonymous sign-ins**. Conserva habilitado **Email** para el acceso del técnico con correo y contraseña. Los visitantes reciben una identidad anónima de Supabase. |
| **Authentication → Users → Add user → Create new user** | Crea la cuenta del técnico con correo y contraseña. Completa la confirmación del correo o usa **Auto Confirm User** si controlas esa dirección. Copia el **User UID**. |
| **SQL Editor → New query** | Autoriza el UID del técnico con la consulta de abajo. La pertenencia a la lista se valida en la base de datos. |
| **Database → Publications → supabase_realtime** | Comprueba que estén incluidas las cinco tablas de Factory. El esquema ya las incorpora. |
| **Connect** o **Settings → API Keys** | Copia el **Project URL** y la **Publishable key** (`sb_publishable_…`). La antigua clave `anon` también es compatible. Mantén la contraseña de base de datos y las claves `secret` y `service_role` fuera de `config.js` y de GitHub. |

En la consulta de alta, sustituye `UUID_DEL_TÉCNICO` por el UID de **Authentication → Users**. Esta autorización permite a esa cuenta ver la sala de espera, los mensajes de soporte y los datos de las sesiones que habiliten diagnóstico.

```sql
insert into factory_private.technicians (user_id)
values ('UUID_DEL_TÉCNICO'::uuid)
on conflict (user_id) do nothing;
```

Para comprobar el esquema desde **SQL Editor**, esta consulta devuelve cinco filas con `rls = true` y `realtime = true`.

```sql
select t.relname as tabla, t.relrowsecurity as rls,
       exists (
         select 1
         from pg_publication_tables p
         where p.pubname = 'supabase_realtime'
           and p.schemaname = 'public' and p.tablename = t.relname
       ) as realtime
from pg_class t join pg_namespace s on s.oid = t.relnamespace
where s.nspname = 'public'
  and t.relname in ('factory_lobby', 'factory_messages', 'factory_agents',
                    'factory_actions', 'factory_audit')
order by 1;
```

Para la prueba privada, la versión actual de Factory usa el flujo anónimo sin formulario CAPTCHA. Conserva los límites de **Authentication → Rate Limits**. Para publicar el portal abierto, integra la protección CAPTCHA en el flujo de inicio anónimo antes de habilitarla y define la retención de cuentas de visitantes.

Referencias de Supabase. [Inicio anónimo](https://supabase.com/docs/guides/auth/auth-anonymous) · [Claves de API](https://supabase.com/docs/guides/api/api-keys) · [Postgres Changes](https://supabase.com/docs/guides/realtime/postgres-changes)

## Conectar el portal

En la rama `factory-compressos`, sustituye las dos cadenas vacías en `config.js` con los valores del proyecto. Conserva los demás valores del archivo.

```js
export const SUPABASE_URL = 'https://REFERENCIA_DEL_PROYECTO.supabase.co';
export const SUPABASE_ANON_KEY = 'sb_publishable_CLAVE_PUBLICA';
```

- **ChatGPT Site**. Publica nuevamente `/soporte/` con ese `config.js`. Comprueba que el portal ya pueda registrar a un visitante y que el técnico lo vea.
- **GitHub Pages**. Con acceso a **Settings → Pages**, selecciona **Deploy from a branch**, rama `factory-compressos`, carpeta **/ (root)** y guarda. El repositorio privado requiere un plan compatible con Pages. Comprueba el resultado en **Settings → Pages**.
- **Prueba local**. Desde el directorio con los archivos configurados, ejecuta `python3 -m http.server 8000 --bind 127.0.0.1` y abre `http://127.0.0.1:8000/`. Añade `--origin http://127.0.0.1:8000` al comando del agente. Cada computadora que use este modo debe servir su propia copia con las mismas claves públicas de proyecto.

## Activación en Linux y prueba con dos computadoras

1. En el equipo que recibirá soporte, abre el portal configurado, descarga `agent.py` y abre una terminal en la carpeta de descarga. Comprueba `python3 --version` (3.8 o superior).
2. Arranca el agente como tu usuario Linux. Para la primera prueba, habilita diagnóstico y deja desactivado el permiso para iniciar o detener servicios. El puente escucha en `127.0.0.1:7890` de la misma computadora.

   ```sh
   FACTORY_ALLOW_REMOTE_DIAGNOSTICS=1 FACTORY_ALLOW_SERVICE_CONTROL=0 \
     python3 agent.py --supabase-url 'https://REFERENCIA_DEL_PROYECTO.supabase.co' \
     --anon-key 'sb_publishable_CLAVE_PUBLICA'
   ```

3. En la computadora del técnico, abre el portal con `?rol=tecnico`. Inicia sesión, selecciona al visitante y pulsa **Generar y enviar token**.
4. En la computadora Linux, pega el token del chat en **Token del técnico** y el código que imprimió el agente en **Código local de la terminal**. Marca **Compartir diagnósticos y telemetría**, pulsa **Solicitar enlace** y permite el acceso a la red local si el navegador lo solicita.
5. Desde la vista del técnico, pulsa **Activar**, ejecuta el diagnóstico `uptime` y confirma que llega el resultado. Finaliza con **Desconectar** en el portal del usuario o `Ctrl+C` en la terminal del agente.
6. El token vence a los cinco minutos y la sesión del agente tiene una duración máxima de una hora. Después de reiniciar el agente, solicita un token nuevo.

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
