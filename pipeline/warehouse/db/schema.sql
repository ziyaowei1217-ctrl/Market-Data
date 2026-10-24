-- Capital Weekly warehouse schema (Supabase / Postgres).
-- Idempotent: safe to re-run. Writes come only from the pipeline's database
-- role; anon/authenticated roles (classmates, agents, REST API) are read-only.

create table if not exists public.indicators (
  indicator_id    text primary key,
  module          text not null,
  name            text not null,
  definition      text,
  unit            text,
  source_freq     text,
  weekly_rule     text,
  cost            text,
  source_desc     text,
  limits          text,
  source_url      text,
  extra_url       text,
  check_status    text,
  evidence        text,
  catalog_version text,
  method          text not null default 'unmapped',
  phase           text,
  formula         text,
  coverage_note   text,
  updated_at      timestamptz not null default now()
);
comment on table public.indicators is '周报指标目录：来自数据采集清单，加上采集方式(method)、阶段(phase)与派生公式(formula)。';
comment on column public.indicators.method is 'api=官方/免费接口直取或派生; report=机构周报快照; manual=人工维护表; excluded=按需求排除; pending=暂未取得来源';

create table if not exists public.series (
  series_key       text primary key,
  provider         text not null,
  code             text not null,
  params           jsonb not null default '{}'::jsonb,
  title            text,
  frequency        text,
  unit             text,
  source_url       text,
  release_lag_days integer,
  vintages         boolean not null default false,
  first_obs        date,
  last_obs         date,
  last_fetched_at  timestamptz,
  last_status      text,
  last_message     text
);
comment on table public.series is '原始序列登记：每条序列只抓一次，所有窗口回报/快照都从这里派生。';

create table if not exists public.observations (
  series_key     text not null references public.series(series_key) on delete cascade,
  obs_date       date not null,
  realtime_start date not null,
  value          double precision,
  vintage_source text not null,
  fetched_at     timestamptz not null default now(),
  primary key (series_key, obs_date, realtime_start)
);
comment on table public.observations is '原始观测（含修订版本）。realtime_start=该值开始可知的日期；vintage_source: provider=数据源给出的发布版本, first_seen=本库首次采集到, backfill_estimate=初次回填按发布滞后估计, report=报告快照。';

create table if not exists public.weekly_values (
  indicator_id text not null references public.indicators(indicator_id) on delete cascade,
  week_cutoff  date not null,
  value        double precision,
  obs_date     date,
  status       text not null,
  detail       text,
  computed_at  timestamptz not null default now(),
  primary key (indicator_id, week_cutoff)
);
comment on table public.weekly_values is '每周截点（周五）的指标值。obs_date=实际取值的观察期；status=ok/missing_input/insufficient_history/no_vintage/error。缺失为 NULL，不用 0 代替。';

create table if not exists public.fetch_log (
  id          bigint generated always as identity primary key,
  run_id      text not null,
  runner      text not null,
  provider    text not null,
  series_key  text,
  status      text not null,
  rows_written integer,
  message     text,
  logged_at   timestamptz not null default now()
);

-- Private archive of weekly institution reports (copyrighted text: no anon policy).
create table if not exists public.report_pages (
  source      text not null,
  report_date date not null,
  page        integer not null,
  url         text,
  text        text,
  fetched_at  timestamptz not null default now(),
  primary key (source, report_date, page)
);
alter table public.report_pages enable row level security;
revoke all on public.report_pages from anon, authenticated;

create index if not exists observations_series_date on public.observations (series_key, obs_date desc);
create index if not exists weekly_values_cutoff on public.weekly_values (week_cutoff);
create index if not exists fetch_log_run on public.fetch_log (run_id);

-- Latest known version of every observation.
create or replace view public.obs_latest with (security_invoker = true) as
select distinct on (o.series_key, o.obs_date)
       o.series_key, o.obs_date, o.value, o.realtime_start, o.vintage_source
from public.observations o
order by o.series_key, o.obs_date, o.realtime_start desc;

-- Weekly indicator values with names and units: the main table for charts.
create or replace view public.weekly with (security_invoker = true) as
select w.week_cutoff, w.indicator_id, i.module, i.name, i.unit,
       w.value, w.obs_date, w.status, i.method
from public.weekly_values w
join public.indicators i using (indicator_id);

-- Most recent week only.
create or replace view public.latest_week with (security_invoker = true) as
select * from public.weekly
where week_cutoff = (select max(week_cutoff) from public.weekly_values);

-- Catalog with coverage summary, for agents to discover what exists.
create or replace view public.catalog with (security_invoker = true) as
select i.indicator_id, i.module, i.name, i.unit, i.method, i.phase,
       i.formula, i.coverage_note, i.source_url,
       s.first_week, s.last_week, s.ok_weeks
from public.indicators i
left join (
  select indicator_id,
         min(week_cutoff) filter (where status = 'ok') as first_week,
         max(week_cutoff) filter (where status = 'ok') as last_week,
         count(*) filter (where status = 'ok') as ok_weeks
  from public.weekly_values group by indicator_id
) s using (indicator_id);

-- Read-only access for anon/authenticated (REST API, classmates, agents).
alter table public.indicators    enable row level security;
alter table public.series        enable row level security;
alter table public.observations  enable row level security;
alter table public.weekly_values enable row level security;
alter table public.fetch_log     enable row level security;

do $$
declare t text;
begin
  foreach t in array array['indicators','series','observations','weekly_values','fetch_log'] loop
    if not exists (
      select 1 from pg_policies where schemaname = 'public' and tablename = t and policyname = 'read_all'
    ) then
      execute format('create policy read_all on public.%I for select to anon, authenticated using (true)', t);
    end if;
  end loop;
end $$;

grant select on public.indicators, public.series, public.observations,
                public.weekly_values, public.fetch_log,
                public.obs_latest, public.weekly, public.latest_week, public.catalog
  to anon, authenticated;
revoke insert, update, delete, truncate on public.indicators, public.series, public.observations,
                public.weekly_values, public.fetch_log from anon, authenticated;
