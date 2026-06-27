create extension if not exists "pgcrypto";

create table if not exists public.schemes (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  description text not null,
  ministry text,
  state text,
  category text not null,
  eligibility_criteria text,
  benefits text,
  application_link text,
  official_source text,
  deadline date,
  tags text[] not null default '{}',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists schemes_category_idx on public.schemes (category);
create index if not exists schemes_state_idx on public.schemes (state);
create index if not exists schemes_ministry_idx on public.schemes (ministry);
create index if not exists schemes_deadline_idx on public.schemes (deadline);
create index if not exists schemes_tags_idx on public.schemes using gin (tags);

alter table public.schemes enable row level security;

drop policy if exists "Authenticated users can read schemes" on public.schemes;
create policy "Authenticated users can read schemes"
on public.schemes
for select
to authenticated
using (true);

create or replace function public.set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists set_schemes_updated_at on public.schemes;

create trigger set_schemes_updated_at
before update on public.schemes
for each row
execute function public.set_updated_at();
