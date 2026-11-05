-- Runs once, when the Postgres volume is first created.
-- Integration tests use their own database so they never touch your local data.
CREATE DATABASE cartlens_test;
