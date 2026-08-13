create table if not exists news_items (
  id integer primary key autoincrement,
  source_channel text not null,
  telegram_message_id integer not null,
  published_at text not null,
  news_date text not null,
  raw_text text not null,
  url text,
  title text,
  article_text text,
  summary_ko text,
  analysis_ko text,
  impact_score real,
  sentiment text,
  risk_level text,
  category text,
  content_type text,
  analysis_status text not null default 'pending',
  analysis_priority real not null default 0,
  analysis_reason text,
  analysis_scope text,
  duplicate_key text,
  user_hidden integer not null default 0,
  user_note text,
  created_at text not null default current_timestamp,
  updated_at text not null default current_timestamp,
  unique(source_channel, telegram_message_id)
);

create table if not exists daily_briefings (
  briefing_date text primary key,
  title text not null,
  summary_ko text not null,
  key_points text not null default '[]',
  top_regions text not null default '[]',
  top_assets text not null default '[]',
  avg_impact_score real,
  max_risk_level text,
  created_at text not null default current_timestamp,
  updated_at text not null default current_timestamp
);

create table if not exists issues (
  id integer primary key autoincrement,
  slug text not null unique,
  title text not null,
  summary_ko text not null,
  status text not null,
  first_seen_date text not null,
  last_seen_date text not null,
  impact_score real,
  created_at text not null default current_timestamp,
  updated_at text not null default current_timestamp
);

create table if not exists issue_events (
  id integer primary key autoincrement,
  issue_id integer not null references issues(id) on delete cascade,
  news_item_id integer references news_items(id) on delete set null,
  event_date text not null,
  event_summary_ko text not null,
  impact_delta text,
  created_at text not null default current_timestamp
);

create table if not exists news_issue_links (
  news_item_id integer not null references news_items(id) on delete cascade,
  issue_id integer not null references issues(id) on delete cascade,
  confidence real not null default 0,
  link_reason_ko text,
  primary key (news_item_id, issue_id)
);

create table if not exists asset_impacts (
  id integer primary key autoincrement,
  asset_name text not null,
  asset_type text not null,
  stance text not null,
  summary_ko text not null,
  impact_score real,
  watch_points text not null default '[]',
  news_date text not null,
  created_at text not null default current_timestamp
);

create table if not exists region_risks (
  id integer primary key autoincrement,
  region_name text not null,
  risk_level text not null,
  pressure_score real not null,
  summary_ko text not null,
  news_date text not null,
  created_at text not null default current_timestamp
);

create table if not exists news_events (
  id integer primary key autoincrement,
  news_item_id integer not null references news_items(id) on delete cascade,
  event_date text not null,
  region_name text,
  event_title text not null,
  event_summary_ko text not null,
  risk_level text,
  impact_score real,
  keywords text not null default '[]',
  created_at text not null default current_timestamp
);

create table if not exists news_deep_analyses (
  news_item_id integer primary key references news_items(id) on delete cascade,
  investor_summary text not null,
  cause_effect_chain text not null default '{}',
  affected_assets text not null default '[]',
  beneficiaries text not null default '[]',
  hurt_parties text not null default '[]',
  time_horizon text not null default '{}',
  priced_in_assessment text not null default '',
  numeric_indicators text not null default '[]',
  counter_scenarios text not null default '[]',
  confirmation_level text not null default '',
  checklist text not null default '[]',
  raw_result text not null default '{}',
  provider text,
  model text,
  created_at text not null default current_timestamp,
  updated_at text not null default current_timestamp
);

create table if not exists news_translations (
  news_item_id integer primary key references news_items(id) on delete cascade,
  lang text not null default 'en',
  title text not null,
  summary text not null,
  analysis text not null,
  raw_text text not null,
  tags text not null default '[]',
  raw_result text not null default '{}',
  provider text,
  model text,
  created_at text not null default current_timestamp,
  updated_at text not null default current_timestamp
);

create table if not exists ai_context_batches (
  id integer primary key autoincrement,
  period_start text not null,
  period_end text not null,
  item_count integer not null,
  context_text text not null,
  status text not null default 'ready',
  created_at text not null default current_timestamp,
  updated_at text not null default current_timestamp,
  unique(period_start, period_end)
);

create table if not exists ai_situation_state (
  id integer primary key check (id = 1),
  state_text text not null,
  source_count integer not null default 0,
  last_news_item_id integer,
  updated_at text not null default current_timestamp
);

create table if not exists telegram_gap_audit (
  source_channel text not null,
  telegram_message_id integer not null,
  status text not null,
  checked_at text not null default current_timestamp,
  primary key (source_channel, telegram_message_id)
);

create table if not exists automation_status (
  service_name text primary key,
  status text not null,
  detail text,
  last_event_at text,
  last_news_item_id integer,
  processed_count integer not null default 0,
  error_count integer not null default 0,
  updated_at text not null default current_timestamp
);

create table if not exists alert_notifications (
  id integer primary key autoincrement,
  news_item_id integer not null references news_items(id) on delete cascade,
  channel text not null,
  alert_key text not null,
  status text not null,
  reason text,
  sent_at text,
  error_message text,
  created_at text not null default current_timestamp,
  updated_at text not null default current_timestamp,
  unique(news_item_id, channel, alert_key)
);

create table if not exists daily_report_deliveries (
  report_date text not null,
  channel text not null,
  status text not null,
  sent_at text,
  error_message text,
  created_at text not null default current_timestamp,
  updated_at text not null default current_timestamp,
  primary key (report_date, channel)
);

create table if not exists push_subscriptions (
  id integer primary key autoincrement,
  endpoint text not null unique,
  p256dh text not null,
  auth text not null,
  user_label text,
  active integer not null default 1,
  created_at text not null default current_timestamp,
  updated_at text not null default current_timestamp
);

create table if not exists economic_knowledge_sources (
  id integer primary key autoincrement,
  source_key text not null unique,
  institution text not null,
  title text not null,
  url text not null,
  source_type text not null,
  trust_tier integer not null check (trust_tier between 1 and 4),
  region text,
  active integer not null default 1,
  verified_at text,
  created_at text not null default current_timestamp,
  updated_at text not null default current_timestamp
);

create table if not exists economic_knowledge (
  id integer primary key autoincrement,
  knowledge_key text not null unique,
  title text not null,
  domain text not null,
  content text not null,
  mechanisms text not null default '[]',
  assumptions text not null default '[]',
  counter_conditions text not null default '[]',
  keywords text not null default '[]',
  source_id integer references economic_knowledge_sources(id),
  confidence real not null default 0.7 check (confidence between 0 and 1),
  status text not null default 'reviewed',
  version integer not null default 1,
  created_at text not null default current_timestamp,
  updated_at text not null default current_timestamp
);

create table if not exists macro_series (
  series_id text primary key,
  title text not null,
  provider text not null,
  frequency text not null,
  unit text not null,
  source_url text not null,
  active integer not null default 1,
  last_synced_at text,
  created_at text not null default current_timestamp,
  updated_at text not null default current_timestamp
);

create table if not exists macro_observations (
  series_id text not null references macro_series(series_id) on delete cascade,
  observed_at text not null,
  value real not null,
  created_at text not null default current_timestamp,
  primary key (series_id, observed_at)
);

create table if not exists economic_analyses (
  id integer primary key autoincrement,
  question text not null,
  answer text not null,
  assumptions text not null default '[]',
  key_variables text not null default '[]',
  variable_interactions text not null default '[]',
  mechanisms text not null default '[]',
  counterarguments text not null default '[]',
  scenario_analysis text not null default '[]',
  turning_conditions text not null default '[]',
  uncertainty text,
  knowledge_used text not null default '[]',
  news_sources text not null default '[]',
  calculations text not null default '{}',
  macro_snapshot text not null default '[]',
  scenarios text not null default '{}',
  provider text,
  model text,
  created_at text not null default current_timestamp
);

create table if not exists economic_analysis_feedback (
  analysis_id integer primary key references economic_analyses(id) on delete cascade,
  rating integer not null check (rating in (-1, 1)),
  note text,
  updated_at text not null default current_timestamp
);

create table if not exists economic_analysis_scores (
  analysis_id integer primary key references economic_analyses(id) on delete cascade,
  total_score real not null,
  structure_score real not null,
  evidence_score real not null,
  reasoning_score real not null,
  calibration_score real not null,
  checks text not null default '{}',
  created_at text not null default current_timestamp,
  updated_at text not null default current_timestamp
);

create table if not exists economic_forecasts (
  id integer primary key autoincrement,
  analysis_id integer not null references economic_analyses(id) on delete cascade,
  series_id text not null references macro_series(series_id),
  forecast_date text not null,
  target_date text not null,
  favorable_value real,
  base_value real,
  adverse_value real,
  actual_value real,
  actual_date text,
  outcome_bucket text,
  base_error_pct real,
  status text not null default 'open',
  evaluated_at text,
  unique(analysis_id, series_id)
);

create table if not exists economic_improvement_queue (
  id integer primary key autoincrement,
  queue_key text not null unique,
  analysis_id integer references economic_analyses(id) on delete cascade,
  forecast_id integer references economic_forecasts(id) on delete cascade,
  issue_type text not null,
  severity text not null check (severity in ('low','medium','high')),
  detail text not null,
  status text not null default 'open',
  created_at text not null default current_timestamp,
  updated_at text not null default current_timestamp
);

create table if not exists economic_calendar_events (
  event_id text primary key,
  title text not null,
  country text not null check (country in ('US','KR','GLOBAL')),
  category text not null,
  importance text not null check (importance in ('high','medium','low')),
  scheduled_at text not null,
  timezone text not null default 'Asia/Seoul',
  status text not null default 'scheduled',
  reference_period text,
  previous_value text,
  forecast_value text,
  actual_value text,
  unit text,
  source_name text not null,
  source_url text not null,
  is_confirmed integer not null default 1,
  notes text,
  created_at text not null default current_timestamp,
  updated_at text not null default current_timestamp
);

create index if not exists idx_news_items_news_date on news_items(news_date);
create index if not exists idx_news_items_category on news_items(category);
create index if not exists idx_news_items_analysis_status on news_items(analysis_status);
create index if not exists idx_news_items_analysis_scope on news_items(analysis_scope);
create index if not exists idx_news_items_analysis_priority on news_items(analysis_priority);
create index if not exists idx_issue_events_issue_id on issue_events(issue_id);
create index if not exists idx_asset_impacts_news_date on asset_impacts(news_date);
create index if not exists idx_region_risks_news_date on region_risks(news_date);
create index if not exists idx_news_events_region_date on news_events(region_name, event_date);
create index if not exists idx_news_deep_analyses_updated on news_deep_analyses(updated_at);
create index if not exists idx_news_translations_lang on news_translations(lang, updated_at);
create index if not exists idx_alert_notifications_status on alert_notifications(status);
create index if not exists idx_push_subscriptions_active on push_subscriptions(active);
create index if not exists idx_economic_knowledge_domain on economic_knowledge(domain);
create index if not exists idx_economic_knowledge_status on economic_knowledge(status);
create index if not exists idx_macro_observations_date on macro_observations(observed_at);
create index if not exists idx_economic_analyses_created on economic_analyses(created_at);
create index if not exists idx_economic_forecasts_target on economic_forecasts(status, target_date);
create index if not exists idx_economic_improvement_status on economic_improvement_queue(status, severity);
create index if not exists idx_economic_calendar_scheduled on economic_calendar_events(scheduled_at);
