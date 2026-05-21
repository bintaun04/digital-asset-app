DROP DATABASE IF EXISTS digital_asset;
CREATE DATABASE digital_asset
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE digital_asset;

-- ── 1. Users ──────────────────────────────────────────────────
CREATE TABLE users (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    email               VARCHAR(150) NOT NULL UNIQUE,
    hashed_password     VARCHAR(255) NOT NULL,
    full_name           VARCHAR(150) DEFAULT '',
    is_active           BOOLEAN DEFAULT TRUE,

    voice_embedding     BLOB       DEFAULT NULL,
    voice_key_text      TEXT       DEFAULT NULL,
    voice_language      VARCHAR(2) DEFAULT 'vi',
    voice_registered_at TIMESTAMP  NULL DEFAULT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ── 2. Voice Insights ─────────────────────────────────────────
CREATE TABLE voice_insights (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    user_id          INT NOT NULL,
    action_type      ENUM('enroll','verify','challenge') NOT NULL,

    -- Embedding comparison
    is_match         BOOLEAN    DEFAULT FALSE,
    cosine_score     FLOAT      DEFAULT 0.0,
    mfcc_score       FLOAT      DEFAULT NULL,
    ge2e_score       FLOAT      DEFAULT NULL,
    text_similarity  FLOAT      DEFAULT NULL,
    threshold        FLOAT      DEFAULT 0.75,
    gap_to_threshold FLOAT      DEFAULT NULL,
    embedding_dim    SMALLINT   DEFAULT 380,
    mode             VARCHAR(20) DEFAULT 'MFCC+GE2E',
    confidence       VARCHAR(10) DEFAULT NULL,

    -- Acoustic features (giọng gốc vs giọng vừa nói)
    duration_sec     FLOAT      DEFAULT NULL,   -- độ dài audio (giây)
    pitch_mean       FLOAT      DEFAULT NULL,   -- tần số cơ bản trung bình (Hz)
    pitch_std        FLOAT      DEFAULT NULL,   -- độ lệch chuẩn pitch
    speaking_rate    FLOAT      DEFAULT NULL,   -- tốc độ nói (syllables/giây)
    energy_mean      FLOAT      DEFAULT NULL,   -- năng lượng trung bình (RMS)
    energy_std       FLOAT      DEFAULT NULL,   -- độ lệch chuẩn năng lượng
    snr_db           FLOAT      DEFAULT NULL,   -- Signal-to-Noise Ratio (dB)
    silence_ratio    FLOAT      DEFAULT NULL,   -- tỉ lệ khoảng lặng [0-1]
    voice_quality    VARCHAR(10) DEFAULT NULL,  -- 'good'/'fair'/'poor'

    -- Meta
    language         VARCHAR(2) DEFAULT 'vi',
    transcribed_text TEXT       DEFAULT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_insights (user_id, action_type),
    INDEX idx_user_recent   (user_id, created_at DESC),
    INDEX idx_action_match  (action_type, is_match)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ── 3. Voice Challenges ───────────────────────────────────────
CREATE TABLE voice_challenges (
    id             VARCHAR(20) PRIMARY KEY,
    user_id        INT         NOT NULL,
    challenge_text TEXT        NOT NULL,
    expires_at     TIMESTAMP   NOT NULL,
    created_at     TIMESTAMP   DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_challenge (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;