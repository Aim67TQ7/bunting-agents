-- Enable PostGIS extension
CREATE EXTENSION IF NOT EXISTS postgis;

-- Create database if it doesn't exist (this script runs after DB creation)
-- The database is already created by Docker, so we just enable PostGIS