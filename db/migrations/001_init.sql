CREATE TABLE IF NOT EXISTS listings (
    id BIGSERIAL PRIMARY KEY,
    raw_text TEXT NOT NULL,
    asking_price DOUBLE PRECISION,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS normalized_specs (
    id BIGSERIAL PRIMARY KEY,
    listing_id BIGINT NOT NULL UNIQUE REFERENCES listings(id) ON DELETE CASCADE,
    payload JSONB NOT NULL
);
CREATE TABLE IF NOT EXISTS user_corrections (
    id BIGSERIAL PRIMARY KEY,
    listing_id BIGINT REFERENCES listings(id) ON DELETE SET NULL,
    original_payload JSONB NOT NULL,
    corrected_payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS prediction_results (
    id BIGSERIAL PRIMARY KEY,
    listing_id BIGINT REFERENCES listings(id) ON DELETE SET NULL,
    fair_price DOUBLE PRECISION NOT NULL,
    asking_price DOUBLE PRECISION NOT NULL,
    rating VARCHAR(32) NOT NULL,
    model_version VARCHAR(128) NOT NULL,
    latency_ms DOUBLE PRECISION,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS model_metadata (
    id BIGSERIAL PRIMARY KEY,
    model_name VARCHAR(128) NOT NULL,
    version VARCHAR(128) NOT NULL UNIQUE,
    metrics JSONB NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'candidate',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS market_observations (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(128) NOT NULL,
    source_id VARCHAR(256) NOT NULL UNIQUE,
    payload JSONB NOT NULL,
    observed_price DOUBLE PRECISION NOT NULL CHECK (observed_price > 0),
    observed_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS ix_prediction_results_created_at ON prediction_results(created_at DESC);
CREATE INDEX IF NOT EXISTS ix_market_observations_observed_at ON market_observations(observed_at DESC);

CREATE TABLE IF NOT EXISTS live_market_listings (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(64) NOT NULL,
    source_listing_id VARCHAR(256) NOT NULL,
    listing_type VARCHAR(32) NOT NULL DEFAULT 'active',
    title TEXT NOT NULL,
    summary TEXT,
    url TEXT,
    image_url TEXT,
    price DOUBLE PRECISION NOT NULL CHECK (price > 0),
    currency VARCHAR(3) NOT NULL,
    price_cad DOUBLE PRECISION NOT NULL CHECK (price_cad > 0),
    condition VARCHAR(32) NOT NULL DEFAULT 'good',
    specs_payload JSONB NOT NULL,
    extraction_quality DOUBLE PRECISION NOT NULL DEFAULT 0,
    fingerprint VARCHAR(64) NOT NULL,
    listed_at TIMESTAMPTZ,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT uq_live_market_source_listing UNIQUE (source, source_listing_id)
);
CREATE INDEX IF NOT EXISTS ix_live_market_source ON live_market_listings(source);
CREATE INDEX IF NOT EXISTS ix_live_market_price_cad ON live_market_listings(price_cad);
CREATE INDEX IF NOT EXISTS ix_live_market_fingerprint ON live_market_listings(fingerprint);
CREATE INDEX IF NOT EXISTS ix_live_market_last_seen ON live_market_listings(last_seen_at DESC);
CREATE INDEX IF NOT EXISTS ix_live_market_expires ON live_market_listings(expires_at);
CREATE INDEX IF NOT EXISTS ix_live_market_active ON live_market_listings(active);

CREATE TABLE IF NOT EXISTS market_refresh_runs (
    id BIGSERIAL PRIMARY KEY,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    status VARCHAR(32) NOT NULL DEFAULT 'running',
    source_stats JSONB NOT NULL DEFAULT '{}'::jsonb,
    quality_stats JSONB NOT NULL DEFAULT '{}'::jsonb,
    error_message TEXT
);
