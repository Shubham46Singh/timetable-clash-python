-- Run once against the timetable database.
CREATE EXTENSION IF NOT EXISTS btree_gist;

CREATE TABLE IF NOT EXISTS classes (
    id        SERIAL PRIMARY KEY,
    day       TEXT    NOT NULL CHECK (day IN ('mon','tue','wed','thu','fri','sat')),
    start_min INTEGER NOT NULL,
    end_min   INTEGER NOT NULL,
    subject   TEXT    NOT NULL,
    teacher   TEXT    NOT NULL,
    room      TEXT    NOT NULL,
    batch     TEXT    NOT NULL,
    CHECK (end_min > start_min),

    -- Database-level backstop to the app's clash check (half-open ranges,
    -- so back-to-back classes are allowed).
    EXCLUDE USING gist (day WITH =, lower(room)    WITH =, int4range(start_min, end_min) WITH &&),
    EXCLUDE USING gist (day WITH =, lower(teacher) WITH =, int4range(start_min, end_min) WITH &&),
    EXCLUDE USING gist (day WITH =, lower(batch)   WITH =, int4range(start_min, end_min) WITH &&)
);
