-- Apply as the Supabase project database administrator after supabase_schema.sql.
alter table factory_private.technicians add column if not exists label text;
create unique index if not exists technicians_label_unique on factory_private.technicians(label);

revoke all on schema factory_private from public, anon, authenticated;
revoke all on all tables in schema factory_private from public, anon, authenticated;
revoke execute on all functions in schema factory_private from public, anon, authenticated;
revoke execute on function public.factory_is_tech() from public, anon;
grant execute on function public.factory_is_tech() to authenticated;

do $$
declare item record;
begin
  for item in select tablename from pg_publication_tables
    where pubname = 'supabase_realtime' and schemaname = 'factory_private'
  loop
    execute format('alter publication supabase_realtime drop table factory_private.%I', item.tablename);
  end loop;
end $$;
