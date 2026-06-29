create extension if not exists "pgcrypto";

create table if not exists public.chat_sessions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  title text not null default 'New chat',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint chat_sessions_id_user_id_unique unique (id, user_id)
);

create table if not exists public.chat_messages (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null,
  user_id uuid not null references auth.users(id) on delete cascade,
  role text not null check (role in ('user', 'assistant')),
  content text not null,
  sources jsonb not null default '[]'::jsonb,
  follow_ups text[] not null default '{}',
  created_at timestamptz not null default now(),
  constraint chat_messages_session_owner_fk
    foreign key (session_id, user_id)
    references public.chat_sessions (id, user_id)
    on delete cascade
);

create index if not exists chat_sessions_user_id_idx on public.chat_sessions (user_id);
create index if not exists chat_sessions_user_updated_idx on public.chat_sessions (user_id, updated_at desc);
create index if not exists chat_messages_session_id_idx on public.chat_messages (session_id);
create index if not exists chat_messages_user_id_idx on public.chat_messages (user_id);
create index if not exists chat_messages_session_created_idx on public.chat_messages (session_id, created_at);

alter table public.chat_sessions enable row level security;
alter table public.chat_messages enable row level security;

drop policy if exists "Users can read their chat sessions" on public.chat_sessions;
create policy "Users can read their chat sessions"
on public.chat_sessions
for select
using (auth.uid() = user_id);

drop policy if exists "Users can create their chat sessions" on public.chat_sessions;
create policy "Users can create their chat sessions"
on public.chat_sessions
for insert
with check (auth.uid() = user_id);

drop policy if exists "Users can update their chat sessions" on public.chat_sessions;
create policy "Users can update their chat sessions"
on public.chat_sessions
for update
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

drop policy if exists "Users can delete their chat sessions" on public.chat_sessions;
create policy "Users can delete their chat sessions"
on public.chat_sessions
for delete
using (auth.uid() = user_id);

drop policy if exists "Users can read their chat messages" on public.chat_messages;
create policy "Users can read their chat messages"
on public.chat_messages
for select
using (auth.uid() = user_id);

drop policy if exists "Users can create their chat messages" on public.chat_messages;
create policy "Users can create their chat messages"
on public.chat_messages
for insert
with check (auth.uid() = user_id);

drop policy if exists "Users can update their chat messages" on public.chat_messages;
create policy "Users can update their chat messages"
on public.chat_messages
for update
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

drop policy if exists "Users can delete their chat messages" on public.chat_messages;
create policy "Users can delete their chat messages"
on public.chat_messages
for delete
using (auth.uid() = user_id);

create or replace function public.set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists set_chat_sessions_updated_at on public.chat_sessions;
create trigger set_chat_sessions_updated_at
before update on public.chat_sessions
for each row
execute function public.set_updated_at();

create or replace function public.touch_chat_session_updated_at()
returns trigger as $$
begin
  update public.chat_sessions
  set updated_at = now()
  where id = new.session_id
    and user_id = new.user_id;

  return new;
end;
$$ language plpgsql;

drop trigger if exists touch_chat_session_after_message_insert on public.chat_messages;
create trigger touch_chat_session_after_message_insert
after insert on public.chat_messages
for each row
execute function public.touch_chat_session_updated_at();
