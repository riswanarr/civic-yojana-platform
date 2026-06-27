create extension if not exists "pgcrypto";

create table if not exists public.sources (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  url text not null,
  category text not null,
  source_type text not null check (source_type in ('api', 'rss', 'scrape')),
  parser_name text not null,
  last_checked timestamptz,
  active boolean not null default true
);

create index if not exists sources_active_idx on public.sources (active);
create index if not exists sources_parser_name_idx on public.sources (parser_name);
create unique index if not exists sources_url_idx on public.sources (url);

insert into public.sources (name, url, category, source_type, parser_name, active)
values
  ('National Scholarship Portal', 'https://scholarships.gov.in', 'Scholarship', 'scrape', 'nsp', true),
  ('AICTE', 'https://www.aicte-india.org', 'Scholarship', 'scrape', 'aicte', true),
  ('National Career Service', 'https://www.ncs.gov.in', 'Government Job', 'scrape', 'ncs', true),
  ('PM Internship Scheme', 'https://pminternship.mca.gov.in', 'Internship', 'scrape', 'pm_internship', true),
  ('Startup India', 'https://www.startupindia.gov.in', 'Startup / Job Creation', 'scrape', 'startup_india', true)
on conflict (url) do nothing;
