-- À exécuter une fois dans l'éditeur SQL de Supabase (Project > SQL Editor).

create extension if not exists vector;

create table if not exists menu_items (
    id text primary key,
    name text not null,
    category text not null,
    composition text,
    price_text text not null,
    content text not null,
    embedding vector(384),
    updated_at timestamptz not null default now()
);

create table if not exists restaurant_info (
    id text primary key,
    type text not null check (type in ('info', 'horaires')),
    label text,
    content text not null,
    embedding vector(384),
    updated_at timestamptz not null default now()
);

-- État de conversation et file de commandes (voir Feuille A-04 de l'architecture).
create table if not exists conversations (
    phone_number text primary key,
    current_step text not null default 'idle',
    cart jsonb not null default '[]'::jsonb,
    -- dernière commande confirmée (order_id, items, fulfillment) — permet au
    -- client de la corriger juste après confirmation sans que l'agent
    -- "l'oublie" (le panier, lui, est vidé dès la confirmation).
    last_order jsonb,
    last_message_at timestamptz not null default now(),
    human_takeover boolean not null default false
);

create table if not exists messages (
    id bigint generated always as identity primary key,
    phone_number text not null references conversations (phone_number) on delete cascade,
    role text not null check (role in ('user', 'assistant', 'system')),
    content text not null,
    created_at timestamptz not null default now()
);

create table if not exists orders_outbox (
    id uuid primary key default gen_random_uuid(),
    phone_number text not null,
    payload jsonb not null,
    status text not null default 'pending' check (status in ('pending', 'sent', 'failed')),
    attempts int not null default 0,
    idempotency_key uuid not null unique,
    partner_order_id text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- Recherche vectorielle : à cette échelle (quelques dizaines/centaines de lignes),
-- une recherche brute (sans index ivfflat) est largement assez rapide.
-- Décommenter si le catalogue grossit significativement (> quelques milliers de lignes) :
-- create index if not exists menu_items_embedding_idx
--     on menu_items using ivfflat (embedding vector_cosine_ops) with (lists = 100);
-- create index if not exists restaurant_info_embedding_idx
--     on restaurant_info using ivfflat (embedding vector_cosine_ops) with (lists = 100);
