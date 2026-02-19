-- BMKG Alert v3 — Database Schema
-- Single owner: Python FastAPI backend
-- Engine: SQLite via aiosqlite

-- Application configuration (key-value)
CREATE TABLE IF NOT EXISTS config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Monitored locations
CREATE TABLE IF NOT EXISTS locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    label TEXT,
    province_code TEXT NOT NULL,
    province_name TEXT NOT NULL,
    district_code TEXT NOT NULL,
    district_name TEXT NOT NULL,
    subdistrict_code TEXT NOT NULL,
    subdistrict_name TEXT NOT NULL,
    latitude REAL,
    longitude REAL,
    enabled BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Notification channels
CREATE TABLE IF NOT EXISTS notification_channels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_type TEXT NOT NULL,
    enabled BOOLEAN DEFAULT 0,
    config TEXT NOT NULL,
    last_success_at TIMESTAMP,
    last_error TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Matched alerts
CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bmkg_alert_code TEXT NOT NULL,
    event TEXT,
    severity TEXT,
    urgency TEXT,
    certainty TEXT,
    headline TEXT,
    description TEXT,
    effective TIMESTAMP,
    expires TIMESTAMP,
    infographic_url TEXT,
    polygon_data TEXT,
    matched_location_id INTEGER REFERENCES locations(id),
    match_type TEXT,
    matched_text TEXT,
    status TEXT DEFAULT 'active',
    expired_notified BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(bmkg_alert_code, matched_location_id)
);

-- Delivery log per alert per channel
CREATE TABLE IF NOT EXISTS alert_deliveries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id INTEGER REFERENCES alerts(id),
    channel_id INTEGER REFERENCES notification_channels(id),
    status TEXT NOT NULL,
    error_message TEXT,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Trial subscriptions (demo mode only)
CREATE TABLE IF NOT EXISTS trial_subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_chat_id TEXT NOT NULL,
    subdistrict_code TEXT NOT NULL,
    subdistrict_name TEXT NOT NULL,
    district_name TEXT NOT NULL,
    province_name TEXT NOT NULL,
    severity_threshold TEXT DEFAULT 'all',
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    expired_notified BOOLEAN DEFAULT 0,
    ip_address TEXT
);

-- Activity log
CREATE TABLE IF NOT EXISTS activity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    message TEXT,
    details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status);
CREATE INDEX IF NOT EXISTS idx_alerts_created ON alerts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_code ON alerts(bmkg_alert_code);
CREATE INDEX IF NOT EXISTS idx_trials_expires ON trial_subscriptions(expires_at);
CREATE INDEX IF NOT EXISTS idx_trials_chat ON trial_subscriptions(telegram_chat_id);
CREATE INDEX IF NOT EXISTS idx_activity_created ON activity_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_deliveries_alert ON alert_deliveries(alert_id);

-- Default config values
INSERT OR IGNORE INTO config (key, value) VALUES ('setup_completed', 'false');
INSERT OR IGNORE INTO config (key, value) VALUES ('bmkg_api_url', 'https://bmkg-restapi.vercel.app');
INSERT OR IGNORE INTO config (key, value) VALUES ('poll_interval', '300');
INSERT OR IGNORE INTO config (key, value) VALUES ('severity_threshold', 'all');
INSERT OR IGNORE INTO config (key, value) VALUES ('quiet_hours_enabled', 'false');
INSERT OR IGNORE INTO config (key, value) VALUES ('quiet_hours_start', '22:00');
INSERT OR IGNORE INTO config (key, value) VALUES ('quiet_hours_end', '06:00');
INSERT OR IGNORE INTO config (key, value) VALUES ('quiet_hours_override_severe', 'true');
INSERT OR IGNORE INTO config (key, value) VALUES ('notification_language', 'id');
INSERT OR IGNORE INTO config (key, value) VALUES ('app_version', '1.0.0');
