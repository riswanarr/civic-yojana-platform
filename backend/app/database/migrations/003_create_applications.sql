create extension if not exists "pgcrypto";

do $$
begin
  if not exists (select 1 from pg_type where typname = 'application_status') then
    create type public.application_status as enum (
      'not_started',
      'in_progress',
      'submitted',
      'approved',
      'rejected'
    );
  end if;
end;
$$;

create table if not exists public.applications (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  scheme_id uuid not null references public.schemes(id) on delete cascade,
  status public.application_status not null default 'not_started',
  notes text,
  applied_at timestamptz,
  updated_at timestamptz not null default now()
);

create index if not exists applications_user_id_idx on public.applications (user_id);
create index if not exists applications_scheme_id_idx on public.applications (scheme_id);
create index if not exists applications_status_idx on public.applications (status);
create index if not exists applications_applied_at_idx on public.applications (applied_at);

alter table public.applications enable row level security;

drop policy if exists "Users can read their applications" on public.applications;
create policy "Users can read their applications"
on public.applications
for select
using (auth.uid() = user_id);

drop policy if exists "Users can create their applications" on public.applications;
create policy "Users can create their applications"
on public.applications
for insert
with check (auth.uid() = user_id);

drop policy if exists "Users can update their applications" on public.applications;
create policy "Users can update their applications"
on public.applications
for update
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

drop policy if exists "Users can delete their applications" on public.applications;
create policy "Users can delete their applications"
on public.applications
for delete
using (auth.uid() = user_id);

create or replace function public.set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists set_applications_updated_at on public.applications;

create trigger set_applications_updated_at
before update on public.applications
for each row
execute function public.set_updated_at();
