-- 01_schema.sql
-- Create schema for the game database

-- Create main schema for game-related tables
CREATE SCHEMA IF NOT EXISTS public;

-- Comment on schema
COMMENT ON SCHEMA public IS 'Schema for the Novi-Sad political strategy game that models Yugoslav politics in 1999';

-- Create extensions if not already created
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
