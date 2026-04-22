USE digital_asset;
 
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS voice_embedding LONGBLOB NULL
        COMMENT 'MFCC+DFT embedding bytes cho xác thực giọng nói';