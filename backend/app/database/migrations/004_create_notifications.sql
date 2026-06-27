create extension if not exists "pgcrypto";

create table if not exists public.notifications (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  title text not null,
  message text not null,
  is_read boolean not null default false,
  created_at timestamptz not null default now(),
  scheme_id uuid null references public.schemes(id) on delete set null
);

alter table public.notifications
  add column if not exists scheme_id uuid null references public.schemes(id) on delete set null;

alter table public.notifications
  drop column if exists type;

create index if not exists notifications_user_id_idx on public.notifications (user_id);
create index if not exists notifications_user_read_idx on public.notifications (user_id, is_read);
create index if not exists notifications_created_at_idx on public.notifications (created_at desc);
create index if not exists notifications_scheme_id_idx on public.notifications (scheme_id);

alter table public.notifications enable row level security;

drop policy if exists "Users can read their notifications" on public.notifications;
create policy "Users can read their notifications"
on public.notifications
for select
using (auth.uid() = user_id);

drop policy if exists "Users can create their notifications" on public.notifications;
create policy "Users can create their notifications"
on public.notifications
for insert
with check (auth.uid() = user_id);

drop policy if exists "Users can update their notifications" on public.notifications;
create policy "Users can update their notifications"
on public.notifications
for update
using (auth.uid() = user_id)
with check (auth.uid() = user_id);
