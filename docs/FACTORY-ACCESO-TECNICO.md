# Acceso técnico y conexión de un equipo

- Cliente: [Portal de soporte](https://hegonhernandez-pixel.github.io/CompressOS-HAL/).
- Técnico: [Acceso técnico](https://hegonhernandez-pixel.github.io/CompressOS-HAL/?rol=tecnico). Entra con el correo confirmado y la contraseña de Supabase. Google estará disponible cuando el administrador active el proveedor.

## Administración en Supabase

El administrador del proyecto usa **SQL Editor**, con permisos sobre el esquema privado. En **Authentication → Users**, copia el UID de una cuenta confirmada. La tabla privada contiene un registro por técnico. `tecnico1` es una etiqueta de ese registro.

```sql
-- Alta o reactivación; cambia ambos valores para otros técnicos.
insert into factory_private.technicians (user_id, label)
select id, 'tecnico1' from auth.users
where id = 'UUID_DE_AUTH'::uuid and email_confirmed_at is not null and not is_anonymous
on conflict (user_id) do update set label = excluded.label;

-- Consulta de administración.
select label, user_id from factory_private.technicians order by label;

-- Revocación del permiso técnico.
delete from factory_private.technicians where user_id = 'UUID_DE_AUTH'::uuid;
```

La revocación bloquea nuevas acciones técnicas en la base. Para cerrar una sesión de soporte ya vinculada, usa **Detener** antes de revocar o pide al cliente que pulse **Desconectar**. Las cinco tablas del portal en Realtime son `factory_lobby`, `factory_messages`, `factory_agents`, `factory_actions` y `factory_audit`. El registro de técnicos, los emparejamientos y las credenciales se administran en `factory_private`.

### Habilitar Google

1. En Google Cloud, crea un cliente OAuth de tipo **Web application**. Agrega `https://kpwumjotcnteygymqlmf.supabase.co/auth/v1/callback` como URI de redirección autorizada.
2. En Supabase, **Authentication → Sign In / Providers → Google**, activa Google y guarda el Client ID y el Client Secret directamente en el panel.
3. En **Authentication → URL Configuration**, agrega `https://hegonhernandez-pixel.github.io/CompressOS-HAL/?rol=tecnico` a **Redirect URLs**.
4. En el portal, entra con una cuenta Google cuyo correo verificado corresponda al usuario autorizado. Si Supabase crea otro UID, revisa **Authentication → Users** antes de asignar el permiso. La contraseña sigue disponible como alternativa.

## Conectar una computadora nueva

1. **Cliente, en Linux:** abre el portal y envía un mensaje. Descarga `agent.py` y ejecuta el comando que muestra el portal. Deja control de servicios desactivado para la primera prueba.
2. **Técnico, en el celular:** entra a Acceso técnico, selecciona al visitante, responde y pulsa **Generar y enviar token**.
3. **Cliente:** copia el token del chat y el código local de la terminal al formulario del portal. Marca **Compartir diagnósticos y telemetría**, pulsa **Solicitar enlace** y autoriza el acceso local si el navegador lo solicita.
4. **Técnico:** pulsa **Activar** y verifica un diagnóstico de lectura. Para terminar, el cliente pulsa **Desconectar**.
