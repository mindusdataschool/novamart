-- Initialize schemas for NovaMart
CREATE SCHEMA IF NOT EXISTS app;
CREATE SCHEMA IF NOT EXISTS marts;

-- Grant permissions
GRANT ALL ON SCHEMA app TO novamart_user;
GRANT ALL ON SCHEMA marts TO novamart_user;
