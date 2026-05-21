-- Team 2 LoL 서렌 예측 Supabase 스키마

create extension if not exists pgcrypto;

create table if not exists public.collection_runs (
  run_id uuid primary key default gen_random_uuid(),
  started_at timestamptz not null default now(),
  ended_at timestamptz,
  status text not null default 'running' check (status in ('running', 'complete', 'failed', 'cancelled')),
  params_json jsonb not null default '{}'::jsonb,
  riot_key_type text default 'development',
  match_count integer not null default 0,
  team_row_count integer not null default 0,
  error_summary text,
  created_at timestamptz not null default now()
);

create table if not exists public.riot_matches (
  match_id text primary key,
  run_id uuid references public.collection_runs(run_id) on delete set null,
  queue_id integer not null,
  game_version text,
  game_duration_sec integer not null,
  game_creation_ms bigint,
  collected_at timestamptz not null default now(),
  has_detail boolean not null default false,
  has_timeline boolean not null default false,
  excluded boolean not null default false,
  exclude_reason text,
  raw_detail_path text,
  raw_timeline_path text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.team_features (
  match_id text not null references public.riot_matches(match_id) on delete cascade,
  team_id integer not null check (team_id in (100, 200)),
  feature_version text not null default 'v1_15min',

  -- 라벨
  team_surrendered boolean not null,

  -- 공통 분석 및 메타데이터
  queue_id integer not null,
  game_version text,
  game_duration_sec integer not null,
  collected_at timestamptz not null default now(),

  -- 15분 시점 팀 간 차이 특성: 양수이면 해당 팀이 앞섬
  gold_diff_15 integer not null,
  kill_diff_15 integer not null,
  tower_diff_15 integer not null,
  dragon_diff_15 integer not null,
  rift_herald_diff_15 integer not null,
  cs_diff_15 integer not null,
  avg_level_diff_15 numeric(6, 3) not null,
  first_blood integer not null check (first_blood in (-1, 0, 1)),
  first_tower integer not null check (first_tower in (-1, 0, 1)),
  ward_placed_diff_15 integer not null,
  ward_kill_diff_15 integer not null,

  -- 선택/필터링 및 메타데이터: PUUID/소환사명 없음
  excluded boolean not null default false,
  exclude_reason text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),

  primary key (match_id, team_id, feature_version)
);

create index if not exists idx_team_features_label on public.team_features(team_surrendered);
create index if not exists idx_team_features_version on public.team_features(feature_version);
create index if not exists idx_riot_matches_run_id on public.riot_matches(run_id);

alter table public.collection_runs enable row level security;
alter table public.riot_matches enable row level security;
alter table public.team_features enable row level security;