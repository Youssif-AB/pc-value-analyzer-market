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
