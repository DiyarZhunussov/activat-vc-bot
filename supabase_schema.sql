-- ========================================
-- Activat VC Bot - Supabase Schema
-- Optimized for Render.com deployment
-- ========================================
-- Выполните этот скрипт в SQL Editor Supabase

-- Таблица пользователей
CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT UNIQUE NOT NULL,
    username TEXT,
    first_name TEXT,
    join_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_active TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_users_user_id ON users(user_id);
CREATE INDEX idx_users_last_active ON users(last_active);

-- Таблица логов сообщений
CREATE TABLE IF NOT EXISTS group_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    username TEXT,
    text TEXT,
    thread_id INTEGER,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_group_logs_timestamp ON group_logs(timestamp DESC);
CREATE INDEX idx_group_logs_user_id ON group_logs(user_id);
CREATE INDEX idx_group_logs_thread_id ON group_logs(thread_id);

-- Таблица shoutouts
CREATE TABLE IF NOT EXISTS shoutouts (
    id BIGSERIAL PRIMARY KEY,
    from_user_id BIGINT NOT NULL,
    to_username TEXT NOT NULL,
    reason TEXT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_shoutouts_timestamp ON shoutouts(timestamp DESC);

-- Таблица челленджей
CREATE TABLE IF NOT EXISTS challenges (
    id BIGSERIAL PRIMARY KEY,
    text TEXT NOT NULL,
    created_by BIGINT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_challenges_active ON challenges(is_active);
CREATE INDEX idx_challenges_created_at ON challenges(created_at DESC);

-- Таблица ответов на челленджи
CREATE TABLE IF NOT EXISTS challenge_responses (
    id BIGSERIAL PRIMARY KEY,
    challenge_id BIGINT REFERENCES challenges(id),
    user_id BIGINT NOT NULL,
    response_text TEXT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_challenge_responses_challenge ON challenge_responses(challenge_id);

-- Таблица нетворкинг
CREATE TABLE IF NOT EXISTS networks (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    username TEXT,
    text TEXT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_networks_timestamp ON networks(timestamp DESC);

-- Таблица питчей
CREATE TABLE IF NOT EXISTS pitches (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    username TEXT,
    text TEXT NOT NULL,
    likes INTEGER DEFAULT 0,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_pitches_timestamp ON pitches(timestamp DESC);
CREATE INDEX idx_pitches_likes ON pitches(likes DESC);

-- Таблица оценок питчей
CREATE TABLE IF NOT EXISTS pitch_ratings (
    id BIGSERIAL PRIMARY KEY,
    author_id BIGINT NOT NULL,
    average_rating DECIMAL(3,2) NOT NULL,
    total_votes INTEGER NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_pitch_ratings_author ON pitch_ratings(author_id);
CREATE INDEX idx_pitch_ratings_timestamp ON pitch_ratings(timestamp DESC);

-- Таблица бейджей
CREATE TABLE IF NOT EXISTS badges (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    badge_type TEXT NOT NULL,
    earned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_badges_user ON badges(user_id);

-- Таблица FAQ
CREATE TABLE IF NOT EXISTS faq (
    id BIGSERIAL PRIMARY KEY,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    category TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Таблица событий
CREATE TABLE IF NOT EXISTS events (
    id BIGSERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    event_date TIMESTAMP WITH TIME ZONE NOT NULL,
    created_by BIGINT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_events_date ON events(event_date);

-- Таблица анализа настроений
CREATE TABLE IF NOT EXISTS sentiment_logs (
    id BIGSERIAL PRIMARY KEY,
    week_start TIMESTAMP WITH TIME ZONE NOT NULL,
    positive_count INTEGER DEFAULT 0,
    negative_count INTEGER DEFAULT 0,
    neutral_count INTEGER DEFAULT 0,
    sentiment_score DECIMAL(5,2),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_sentiment_logs_week ON sentiment_logs(week_start DESC);

-- Таблица логов бота
CREATE TABLE IF NOT EXISTS bot_logs (
    id BIGSERIAL PRIMARY KEY,
    level TEXT NOT NULL,
    message TEXT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_bot_logs_level ON bot_logs(level);
CREATE INDEX idx_bot_logs_timestamp ON bot_logs(timestamp DESC);

-- Таблица отчетов
CREATE TABLE IF NOT EXISTS reports (
    id BIGSERIAL PRIMARY KEY,
    reporter_id BIGINT NOT NULL,
    reported_user_id BIGINT NOT NULL,
    reason TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    resolved_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_reports_status ON reports(status);
CREATE INDEX idx_reports_created ON reports(created_at DESC);

-- ========================================
-- ВАЖНО: Row Level Security (RLS)
-- ========================================
-- Для production используйте service_role key
-- Для тестирования можно отключить RLS:

-- ALTER TABLE users ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE group_logs ENABLE ROW LEVEL SECURITY;
-- И т.д. для всех таблиц

-- Или создайте политики:
-- CREATE POLICY "Allow bot access" ON users FOR ALL USING (true);

-- ========================================
-- Проверка создания таблиц
-- ========================================
-- Запустите это после выполнения скрипта:

SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;

-- Должны увидеть все созданные таблицы
