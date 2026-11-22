-- Proyecto nuevo: compressos-agent-factory. Organización: mozaxdepxhzkloylkbun.
-- SUPABASE_URL y SUPABASE_ANON_KEY: pendientes de provisionamiento. Véase config.js.
-- Habilitar inicio anónimo en Auth. Crear cada técnico en Auth y añadir su UUID
-- a factory_private.technicians con el editor SQL. Las escrituras pasan por RPC.
begin;
create schema if not exists extensions;
create extension if not exists pgcrypto with schema extensions;
create schema factory_private;
revoke all on schema factory_private from public, anon, authenticated;
create table factory_private.technicians (
  user_id uuid primary key references auth.users(id) on delete cascade
);

create table public.factory_lobby (
  session_id uuid primary key references auth.users(id) on delete cascade,
  visitor_name text not null check (char_length(visitor_name) between 1 and 60),
  status text not null default 'waiting' check (status in
    ('waiting','token_sent','link_requested','active','paused','stopped')),
  assigned_token boolean not null default false,
  device_id uuid unique,
  last_seen timestamptz not null default now()
);
create table public.factory_messages (
  id bigint generated always as identity primary key,
  session_id uuid not null references public.factory_lobby on delete cascade,
  sender text not null check (sender in ('user','tech')),
  content text not null check (char_length(content) between 1 and 2000),
  is_token boolean not null default false,
  created_at timestamptz not null default now()
);
create table public.factory_agents (
  device_id uuid primary key,
  session_id uuid not null references public.factory_lobby on delete cascade,
  control_desired text not null default 'paused' check (control_desired in ('active','paused','stopped')),
  control_revision bigint not null default 0,
  consent_service_control boolean not null default false,
  consent_remote_diagnostics boolean not null default false,
  last_heartbeat timestamptz,
  telemetry_json jsonb not null default '{}',
  control_result text not null default 'pending',
  expires_at timestamptz not null default now() + interval '1 hour',
  revoked boolean not null default false
);
create table factory_private.pairings (
  session_id uuid primary key references public.factory_lobby on delete cascade,
  digest bytea not null,
  expires_at timestamptz not null
);
create table factory_private.device_credentials (
  device_id uuid primary key references public.factory_agents on delete cascade,
  token_hash bytea not null
);
create table public.factory_actions (
  task_id uuid primary key default gen_random_uuid(),
  device_id uuid not null references public.factory_agents on delete cascade,
  kind text not null check (kind in ('status','uptime','disk','systemctl','swapon','hal_metrics')),
  status text not null default 'pending' check (status in ('pending','completed','rejected')),
  result_json jsonb,
  created_at timestamptz not null default now(),
  claimed_at timestamptz,
  finished_at timestamptz,
  requested_by uuid
);
create table public.factory_audit (
  id bigint generated always as identity primary key,
  session_id uuid not null references public.factory_lobby on delete cascade,
  actor uuid,
  event text not null,
  detail jsonb not null default '{}',
  created_at timestamptz not null default now()
);
create index on public.factory_lobby(last_seen desc);
create index on public.factory_messages(session_id,id desc);
create index on public.factory_agents(session_id);
create index on public.factory_actions(device_id,created_at desc);
create index on public.factory_audit(session_id,id desc);

create function public.factory_is_tech() returns boolean
language sql stable security definer set search_path = '' as $$
  select exists (select 1 from factory_private.technicians where user_id = auth.uid())
    and coalesce(auth.jwt()->>'is_anonymous','true') = 'false';
$$;

alter table public.factory_lobby enable row level security;
alter table public.factory_messages enable row level security;
alter table public.factory_agents enable row level security;
alter table public.factory_actions enable row level security;
alter table public.factory_audit enable row level security;
create policy read_lobby on public.factory_lobby for select to authenticated
  using (session_id = (select auth.uid()) or (select public.factory_is_tech()));
create policy read_messages on public.factory_messages for select to authenticated
  using (session_id = (select auth.uid()) or ((select public.factory_is_tech()) and not is_token));
create policy read_agents on public.factory_agents for select to authenticated
  using (session_id = (select auth.uid()) or (select public.factory_is_tech()));
create policy read_actions on public.factory_actions for select to authenticated
  using (exists (select 1 from public.factory_agents a where a.device_id = factory_actions.device_id));
create policy read_audit on public.factory_audit for select to authenticated
  using (session_id = (select auth.uid()) or (select public.factory_is_tech()));

revoke all on public.factory_lobby,public.factory_messages,public.factory_agents,public.factory_actions,
  public.factory_audit from public, anon, authenticated;
grant select on public.factory_lobby,public.factory_messages,public.factory_agents,public.factory_actions,
  public.factory_audit to authenticated;

create function public.factory_send(p_session uuid,p_text text) returns void
language plpgsql security definer set search_path = '' as $$
declare tech boolean := public.factory_is_tech();
begin
  if auth.uid() is null or (p_session is distinct from auth.uid() and not tech) then
    raise exception 'Sesión ajena' using errcode='42501';
  end if;
  perform 1 from public.factory_lobby where session_id=p_session for update;
  if not found then raise exception 'Sesión desconocida'; end if;
  if (select count(*) from public.factory_messages
      where session_id=p_session and sender=(case when tech then 'tech' else 'user' end)
        and created_at > now()-interval '1 minute') >= 30 then
    raise exception 'Límite temporal de mensajes';
  end if;
  insert into public.factory_messages(session_id,sender,content)
    values (p_session,case when tech then 'tech' else 'user' end,trim(p_text));
end $$;

create function public.factory_issue(p_session uuid) returns void
language plpgsql security definer set search_path = '' as $$
declare secret uuid := gen_random_uuid();
begin
  if not public.factory_is_tech() then raise exception 'Técnico requerido' using errcode='42501'; end if;
  update public.factory_lobby set status='token_sent',assigned_token=true
    where session_id=p_session and status in ('waiting','token_sent','stopped')
    and last_seen > now()-interval '30 seconds';
  if not found then raise exception 'Visitante no disponible para enlace'; end if;
  if exists (select 1 from factory_private.pairings where session_id=p_session
             and expires_at > now()+interval '4 minutes 50 seconds') then
    raise exception 'Espera unos segundos antes de renovar el token';
  end if;
  insert into factory_private.pairings values(p_session,extensions.digest(secret::text,'sha256'),now()+interval '5 minutes')
    on conflict (session_id) do update set digest=excluded.digest,expires_at=excluded.expires_at;
  update public.factory_messages set content='[Token sustituido]'
    where session_id=p_session and is_token and content !~ '^\[';
  insert into public.factory_messages(session_id,sender,content,is_token) values (p_session,'tech',secret::text,true);
  insert into public.factory_audit(session_id,actor,event) values(p_session,auth.uid(),'token_issued');
end $$;

create function public.factory_pair(p_session uuid,p_token uuid,p_device uuid,p_secret text,
  p_service boolean,p_diagnostics boolean) returns void
language plpgsql security definer set search_path = '' as $$
begin
  if p_secret is null or p_secret !~ '^[0-9a-f]{64}$' then raise exception 'Credencial inválida'; end if;
  perform 1 from public.factory_lobby where session_id=p_session for update;
  if exists (select 1 from public.factory_agents a join factory_private.device_credentials c using(device_id)
      where a.device_id=p_device and a.session_id=p_session and not a.revoked and a.expires_at>now()
      and c.token_hash=extensions.digest(p_secret,'sha256')) then return; end if;
  delete from factory_private.pairings where session_id=p_session and expires_at>now()
    and digest=extensions.digest(p_token::text,'sha256');
  if not found then raise exception 'Token inválido, usado o vencido' using errcode='42501'; end if;
  insert into public.factory_agents(device_id,session_id,consent_service_control,consent_remote_diagnostics)
    values(p_device,p_session,p_service,p_diagnostics);
  insert into factory_private.device_credentials values(p_device,extensions.digest(p_secret,'sha256'));
  update public.factory_lobby set status='link_requested',assigned_token=false,device_id=p_device where session_id=p_session;
  update public.factory_messages set content='[Token utilizado]' where session_id=p_session and is_token and content=p_token::text;
  insert into public.factory_audit(session_id,event,detail) values(p_session,'device_link_requested',jsonb_build_object('device_id',p_device));
end $$;

create function factory_private.revoke_device(p_device uuid,p_reason text) returns void
language plpgsql security definer set search_path = '' as $$
declare visitor uuid;
begin
  update public.factory_agents set revoked=true,control_desired='stopped',control_revision=control_revision+1,
    telemetry_json='{}',control_result=p_reason where device_id=p_device and not revoked returning session_id into visitor;
  if found then
    update public.factory_lobby set status='stopped',assigned_token=false where session_id=visitor and device_id=p_device;
    update public.factory_actions set status='rejected',finished_at=now(), result_json=jsonb_build_object('code',p_reason)
      where device_id=p_device and status='pending';
    insert into public.factory_audit(session_id,actor,event,detail)
      values(visitor,auth.uid(),'device_revoked',jsonb_build_object('device_id',p_device,'reason',p_reason));
  end if;
end $$;

create function public.factory_presence(p_name text) returns void
language plpgsql security definer set search_path = '' as $$
begin
  if auth.uid() is null or coalesce(auth.jwt()->>'is_anonymous','false') <> 'true' then
    raise exception 'Sesión de visitante requerida' using errcode='42501';
  end if;
  insert into public.factory_lobby(session_id,visitor_name) values (auth.uid(),left(coalesce(nullif(trim(p_name),''),'Visitante'),60))
  on conflict (session_id) do update set visitor_name=excluded.visitor_name,last_seen=now()
  where factory_lobby.last_seen < now() - interval '3 seconds';
  perform 1 from public.factory_lobby where session_id=auth.uid() for update;
  perform factory_private.revoke_device(a.device_id,'lease_ended')
    from public.factory_agents a join public.factory_lobby l on l.device_id=a.device_id
    where l.session_id=auth.uid() and not a.revoked and
      (a.expires_at<=now() or coalesce(a.last_heartbeat,a.expires_at-interval '1 hour') < now()-interval '1 minute');
end $$;

create function public.factory_disconnect() returns void
language plpgsql security definer set search_path = '' as $$
declare device uuid;
begin
  if auth.uid() is null then raise exception 'Sesión requerida' using errcode='42501'; end if;
  select device_id into device from public.factory_lobby where session_id=auth.uid() for update;
  perform factory_private.revoke_device(device,'visitor_disconnect');
  delete from factory_private.pairings where session_id=auth.uid();
  update public.factory_messages set content='[Token revocado]' where session_id=auth.uid() and is_token and content !~ '^\[';
  update public.factory_lobby set status='stopped',assigned_token=false where session_id=auth.uid();
end $$;

create function public.factory_control(p_device uuid,p_state text) returns void
language plpgsql security definer set search_path = '' as $$
declare agent public.factory_agents;
begin
  if not public.factory_is_tech() then raise exception 'Técnico requerido' using errcode='42501'; end if;
  if p_state is null or p_state not in ('active','paused','stopped') then raise exception 'Estado inválido'; end if;
  select a.* into agent from public.factory_agents a where device_id=p_device;
  perform 1 from public.factory_lobby where session_id=agent.session_id for update;
  select a.* into agent from public.factory_agents a where device_id=p_device for update;
  if not found or agent.revoked or agent.expires_at<=now() then raise exception 'Enlace vencido o revocado'; end if;
  if p_state='stopped' then
    perform factory_private.revoke_device(p_device,'technician_stop');
    return;
  end if;
  if p_state='active' and coalesce(agent.last_heartbeat,now()-interval '1 day') < now()-interval '30 seconds' then
    raise exception 'El agente está desconectado';
  end if;
  update public.factory_agents set control_desired=p_state,control_revision=control_revision+1,control_result='pending',
    telemetry_json=case when p_state='paused' then '{}'::jsonb else telemetry_json end where device_id=p_device;
  if p_state='paused' then
    update public.factory_lobby set status='paused' where session_id=agent.session_id and device_id=p_device;
    update public.factory_actions set status='rejected',finished_at=now(),result_json='{"code":"paused"}'
      where device_id=p_device and status='pending';
  end if;
  insert into public.factory_audit(session_id,actor,event,detail)
    values(agent.session_id,auth.uid(),'control_requested',jsonb_build_object('device_id',p_device,'state',p_state,'revision',agent.control_revision+1));
end $$;

create function public.factory_enqueue(p_device uuid,p_kind text) returns uuid
language plpgsql security definer set search_path = '' as $$
declare agent public.factory_agents; task uuid;
begin
  if not public.factory_is_tech() then raise exception 'Técnico requerido' using errcode='42501'; end if;
  select a.* into agent from public.factory_agents a where device_id=p_device for update;
  if not found or agent.revoked or agent.expires_at<=now() or agent.control_desired <> 'active'
    or agent.last_heartbeat is null or agent.last_heartbeat < now()-interval '25 seconds'
    or agent.control_result not in ('applied','session_only') or not agent.consent_remote_diagnostics then
    raise exception 'Diagnósticos no disponibles para este equipo';
  end if;
  if (select count(*) from public.factory_actions where device_id=p_device and created_at>now()-interval '1 minute') >= 12 then
    raise exception 'Límite temporal de diagnósticos';
  end if;
  insert into public.factory_actions(device_id,kind,requested_by) values(p_device,p_kind,auth.uid()) returning task_id into task;
  return task;
end $$;

create function public.factory_agent_sync(p_device uuid,p_secret text,p_service boolean,p_diagnostics boolean,
  p_revision bigint,p_ack text,p_telemetry jsonb,p_task uuid,p_result jsonb,p_revoke boolean)
returns jsonb language plpgsql security definer set search_path = '' as $$
declare agent public.factory_agents; next_task jsonb; visitor uuid;
begin
  if p_secret is null or p_secret !~ '^[0-9a-f]{64}$' then raise exception 'Agente no autorizado' using errcode='42501'; end if;
  select a.session_id into visitor from public.factory_agents a join factory_private.device_credentials c using(device_id)
    where a.device_id=p_device and c.token_hash=extensions.digest(p_secret,'sha256');
  if not found then raise exception 'Agente no autorizado' using errcode='42501'; end if;
  perform 1 from public.factory_lobby where session_id=visitor for update;
  select a.* into agent from public.factory_agents a where a.device_id=p_device for update;
  if p_revoke or agent.expires_at<=now() or (agent.last_heartbeat is not null and agent.last_heartbeat<now()-interval '1 minute') then
    perform factory_private.revoke_device(p_device,'lease_ended');
    agent.revoked := true;
  end if;
  if agent.revoked then return '{"stopped":true}'; end if;
  if p_ack is not null and p_ack not in ('applied','unavailable','session_only') then raise exception 'Acuse inválido'; end if;
  if octet_length(p_telemetry::text)>8192 or octet_length(p_result::text)>8192 then raise exception 'Carga demasiado grande'; end if;
  update public.factory_agents set last_heartbeat=now(),consent_service_control=p_service,
    consent_remote_diagnostics=p_diagnostics,
    control_result=case when p_revision=agent.control_revision and p_ack is not null then p_ack else control_result end,
    telemetry_json=case when agent.control_desired='active' and p_revision=agent.control_revision and p_diagnostics
      then coalesce(p_telemetry,telemetry_json) else '{}'::jsonb end where device_id=p_device returning * into agent;
  if agent.control_revision>0 and p_revision=agent.control_revision and p_ack is not null then
    update public.factory_lobby set status=case when agent.control_desired='active' and p_ack in ('applied','session_only')
      then 'active' else 'paused' end where session_id=visitor and device_id=p_device and status is distinct from
      case when agent.control_desired='active' and p_ack in ('applied','session_only') then 'active' else 'paused' end;
  end if;
  if p_task is not null and p_result is not null then
    update public.factory_actions set status=case when p_result->>'ok'='true' then 'completed' else 'rejected' end,
      result_json=p_result,finished_at=now() where task_id=p_task and device_id=p_device and status='pending'
      and claimed_at is not null and agent.control_desired='active' and p_diagnostics and p_revision=agent.control_revision;
  end if;
  update public.factory_actions set status='rejected',finished_at=now(),result_json='{"code":"expired_or_unavailable"}'
    where device_id=p_device and status='pending' and (created_at<now()-interval '30 seconds' or not p_diagnostics);
  if agent.control_desired='active' and p_revision=agent.control_revision
    and agent.control_result in ('applied','session_only') and p_diagnostics then
    update public.factory_actions set claimed_at=now()
      where task_id=(select task_id from public.factory_actions where device_id=p_device and status='pending'
        and claimed_at is null order by created_at,task_id limit 1)
      returning jsonb_build_object('id',task_id,'kind',kind) into next_task;
  end if;
  return jsonb_build_object('stopped',false,'desired',agent.control_desired,'revision',agent.control_revision,
    'task',next_task,'expires_at',agent.expires_at);
end $$;

revoke execute on all functions in schema factory_private from public,anon,authenticated;
revoke execute on function public.factory_is_tech(),public.factory_presence(text),public.factory_send(uuid,text),
  public.factory_issue(uuid),public.factory_pair(uuid,uuid,uuid,text,boolean,boolean),public.factory_disconnect(),
  public.factory_control(uuid,text),public.factory_enqueue(uuid,text),
  public.factory_agent_sync(uuid,text,boolean,boolean,bigint,text,jsonb,uuid,jsonb,boolean) from public,anon,authenticated;
grant execute on function public.factory_is_tech(),public.factory_presence(text),public.factory_send(uuid,text),
  public.factory_issue(uuid),public.factory_disconnect(),public.factory_control(uuid,text),public.factory_enqueue(uuid,text) to authenticated;
grant execute on function public.factory_pair(uuid,uuid,uuid,text,boolean,boolean),
  public.factory_agent_sync(uuid,text,boolean,boolean,bigint,text,jsonb,uuid,jsonb,boolean) to anon;

alter publication supabase_realtime add table public.factory_lobby,public.factory_messages,
  public.factory_agents,public.factory_actions,public.factory_audit;
commit;
