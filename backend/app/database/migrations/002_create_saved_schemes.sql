create extension if not exists "pgcrypto";

create table if not exists public.saved_schemes (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  scheme_id uuid not null references public.schemes(id) on delete cascade,
  created_at timestamptz not null default now(),
  constraint saved_schemes_user_scheme_unique unique (user_id, scheme_id)
);

create index if not exists saved_schemes_user_id_idx on public.saved_schemes (user_id);
create index if not exists saved_schemes_scheme_id_idx on public.saved_schemes (scheme_id);

alter table public.saved_schemes enable row level security;

drop policy if exists "Users can read their saved schemes" on public.saved_schemes;
create policy "Users can read their saved schemes"
on public.saved_schemes
for select
using (auth.uid() = user_id);

drop policy if exists "Users can save schemes" on public.saved_schemes;
create policy "Users can save schemes"
on public.saved_schemes
for insert
with check (auth.uid() = user_id);

drop policy if exists "Users can delete their saved schemes" on public.saved_schemes;
create policy "Users can delete their saved schemes"
on public.saved_schemes
for delete
using (auth.uid() = user_id);
