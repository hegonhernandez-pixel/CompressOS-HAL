-- Restore staff visibility while preserving visitor isolation.
alter policy read_lobby on public.factory_lobby to authenticated
  using (session_id = (select auth.uid()) or (select public.factory_is_tech()));
alter policy read_agents on public.factory_agents to authenticated
  using (session_id = (select auth.uid()) or (select public.factory_is_tech()));
alter policy read_messages on public.factory_messages to authenticated
  using (session_id = (select auth.uid()) or ((select public.factory_is_tech()) and not is_token));
alter policy read_actions on public.factory_actions to authenticated
  using (exists (select 1 from public.factory_agents a where a.device_id = factory_actions.device_id));
alter policy read_audit on public.factory_audit to authenticated
  using (session_id = (select auth.uid()) or (select public.factory_is_tech()));
