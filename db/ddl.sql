-- PostgreSQL 15+
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Firms & cases
CREATE TABLE firms(
  firm_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  logo_url TEXT,
  market_share NUMERIC CHECK (market_share BETWEEN 0 AND 100)
);

CREATE TABLE cases(
  case_id TEXT PRIMARY KEY,
  industry TEXT NOT NULL,
  geography TEXT NOT NULL,
  period_start TIMESTAMPTZ NOT NULL,
  period_end   TIMESTAMPTZ NOT NULL,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  meta JSONB DEFAULT '{}'::jsonb
);

-- Observations (CDS spreads etc.)
CREATE TABLE observations(
  case_id TEXT NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
  ts TIMESTAMPTZ NOT NULL,
  firm_id TEXT NOT NULL REFERENCES firms(firm_id),
  price NUMERIC NOT NULL,        -- bps
  volume NUMERIC,
  unit TEXT DEFAULT 'bps',
  src TEXT NOT NULL,             -- client|spglobal|ice|refinitiv|derived
  confidence NUMERIC NOT NULL CHECK (confidence BETWEEN 0 AND 100),
  hash TEXT NOT NULL,            -- SHA-256 of raw row
  PRIMARY KEY(case_id, ts, firm_id, src)
);
CREATE INDEX obs_case_ts_idx ON observations(case_id, ts);
CREATE INDEX obs_case_firm_ts_idx ON observations(case_id, firm_id, ts);

-- Resolved time series (post QC & fusion)
CREATE TABLE series_resolved(
  case_id TEXT NOT NULL,
  ts TIMESTAMPTZ NOT NULL,
  firm_id TEXT NOT NULL,
  price NUMERIC NOT NULL,
  confidence NUMERIC NOT NULL,
  source_preference TEXT NOT NULL, -- which feed won
  PRIMARY KEY(case_id, ts, firm_id)
);
CREATE INDEX sres_case_ts_idx ON series_resolved(case_id, ts);

-- Environments (PELT/manual/event)
CREATE TABLE environments(
  env_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  case_id TEXT NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
  label TEXT NOT NULL,
  start_ts TIMESTAMPTZ NOT NULL,
  end_ts   TIMESTAMPTZ NOT NULL,
  method TEXT NOT NULL,
  meta JSONB DEFAULT '{}'::jsonb
);
CREATE INDEX env_case_bounds_idx ON environments(case_id, start_ts, end_ts);

-- Metrics
CREATE TABLE metrics(
  case_id TEXT NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
  as_of TIMESTAMPTZ NOT NULL,
  key TEXT NOT NULL, -- INV, SYNC, STAB, REG, RISK
  value NUMERIC NOT NULL,
  ci_low NUMERIC,
  ci_high NUMERIC,
  meta JSONB DEFAULT '{}'::jsonb,
  PRIMARY KEY(case_id, as_of, key)
);
CREATE INDEX metrics_case_key_ts_idx ON metrics(case_id, key, as_of);

-- Risk summary (latest)
CREATE TABLE risk_summary(
  case_id TEXT PRIMARY KEY REFERENCES cases(case_id) ON DELETE CASCADE,
  score NUMERIC NOT NULL CHECK (score BETWEEN 0 AND 100),
  verdict TEXT NOT NULL CHECK (verdict IN ('GREEN','AMBER','RED')),
  confidence NUMERIC NOT NULL CHECK (confidence BETWEEN 0 AND 1),
  ci_low NUMERIC,
  ci_high NUMERIC,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  rationale JSONB NOT NULL
);

-- Regime probabilities timeline
CREATE TABLE regime_probabilities(
  case_id TEXT NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
  ts TIMESTAMPTZ NOT NULL,
  p_coordination NUMERIC NOT NULL CHECK (p_coordination BETWEEN 0 AND 1),
  p_competitive NUMERIC NOT NULL CHECK (p_competitive BETWEEN 0 AND 1),
  PRIMARY KEY(case_id, ts)
);

-- Audit log (WORM store pointer kept in evidence bundle)
CREATE TABLE audit_log(
  id BIGSERIAL PRIMARY KEY,
  case_id TEXT NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
  actor TEXT NOT NULL,
  action TEXT NOT NULL,
  ts TIMESTAMPTZ NOT NULL DEFAULT now(),
  payload JSONB NOT NULL,
  hash TEXT NOT NULL
);
CREATE INDEX audit_case_ts_idx ON audit_log(case_id, ts);

-- Minimal seed firms for SA banks example
INSERT INTO firms(firm_id, name) VALUES
('FNB','First National Bank'),
('NED','Nedbank'),
('SBK','Standard Bank'),
('ABSA','Absa')
ON CONFLICT DO NOTHING;
