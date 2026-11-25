-- Least-privilege role for postgres-exporter (idempotent).
-- Run as the database owner/superuser with psql variable :pw set, e.g.:
--   psql -U glitchtip -d glitchtip -v pw="<password>" -f postgres-monitoring-user.sql
-- The password lives in monitoring-app/secrets/pg-monitor-password (git-ignored).

DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'monitoring') THEN
    CREATE ROLE monitoring LOGIN;
  END IF;
END
$$;

ALTER ROLE monitoring WITH LOGIN PASSWORD :'pw'
  NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION CONNECTION LIMIT 3;
-- Built-in role: read access to statistics views only (no table data).
GRANT pg_monitor TO monitoring;
ALTER ROLE monitoring SET default_transaction_read_only = on;
GRANT CONNECT ON DATABASE glitchtip TO monitoring;
