"""Row-Level Security sweep for the public schema.

Supabase publishes every table in the `public` schema through PostgREST, so a
table without RLS is readable, writable and deletable by anyone holding the
project's anon key — which is shipped to browsers by design. Nothing in this
project talks to PostgREST: the FastAPI backend connects to Postgres directly
as the table owner, and owners bypass RLS unless FORCE ROW LEVEL SECURITY is
set. Enabling RLS with no policies therefore shuts PostgREST out completely
while leaving the backend untouched.

The sweep is dynamic rather than a hard-coded table list. A list drifts every
time a migration adds a table, which is exactly how the credit-note, delivery-
note and procurement tables ended up publicly readable after `rls001`. `env.py`
runs this after every `alembic upgrade`, so a new table is covered by the same
deploy that creates it.

Tables owned by another role are reported instead of failing the deploy: the
ALTER would raise "must be owner of table" and abort the whole migration run.
"""

ENABLE_RLS_ON_PUBLIC_TABLES = """
DO $$
DECLARE
    rec record;
    skipped text[] := '{}';
BEGIN
    FOR rec IN
        SELECT c.relname AS tbl,
               pg_has_role(current_user, c.relowner, 'USAGE') AS owned
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public'
          AND c.relkind IN ('r', 'p')   -- ordinary and partitioned tables
          AND NOT c.relrowsecurity
        ORDER BY c.relname
    LOOP
        IF rec.owned THEN
            EXECUTE 'ALTER TABLE public.' || quote_ident(rec.tbl)
                    || ' ENABLE ROW LEVEL SECURITY';
        ELSE
            skipped := skipped || rec.tbl;
        END IF;
    END LOOP;

    IF array_length(skipped, 1) > 0 THEN
        RAISE WARNING USING MESSAGE =
            'RLS left disabled (not owned by ' || current_user || '): '
            || array_to_string(skipped, ', ');
    END IF;
END
$$;
"""
