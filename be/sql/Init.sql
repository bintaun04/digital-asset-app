DROP DATABASE digital_asset;
CREATE DATABASE digital_asset
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE digital_asset;

CREATE TABLE users (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    email               VARCHAR(150) NOT NULL UNIQUE,
    hashed_password     VARCHAR(255) NOT NULL,
    full_name           VARCHAR(150) DEFAULT '',
    is_active           BOOLEAN DEFAULT TRUE,

    -- Voice biometric
    voice_embedding     BLOB DEFAULT NULL,
    voice_key_text      TEXT DEFAULT NULL,
    voice_language      VARCHAR(2) DEFAULT 'vi',
    voice_registered_at TIMESTAMP NULL DEFAULT NULL,

    -- Timestamps
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_email (email),
    INDEX idx_voice_language (voice_language)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;