CREATE DATABASE IF NOT EXISTS digital_asset
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;
 
USE digital_asset;
 
-- ── 1. Users (Auth) ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    email           VARCHAR(150) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name       VARCHAR(150) DEFAULT '',
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
 
-- ── 2. Voice Embeddings (Biometric) ─────────────────────────
CREATE TABLE IF NOT EXISTS voice_embeddings (
    id                   INT AUTO_INCREMENT PRIMARY KEY,
    user_id              INT NOT NULL,
    chroma_collection    VARCHAR(100),
    chroma_id            VARCHAR(50) UNIQUE,
    mfcc_metadata        JSON,
    similarity_threshold FLOAT DEFAULT 0.7,
    registered_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
 
-- ── 3. Indexes ───────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_users_email
    ON users(email);
 
CREATE INDEX IF NOT EXISTS idx_voice_embeddings_user_id
    ON voice_embeddings(user_id);
 