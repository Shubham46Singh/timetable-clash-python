CREATE TABLE IF NOT EXISTS classes (
    id SERIAL PRIMARY KEY,
    day TEXT NOT NULL CHECK (day IN ('mon','tue','wed','thu','fri','sat')),
    -- minutes past midnight: comparing "9:00" to "10:00" as text does not work
    start_min INT NOT NULL CHECK (start_min >= 0 AND start_min < 1440),
    end_min INT NOT NULL CHECK (end_min > 0 AND end_min <= 1440),
    subject TEXT NOT NULL,
    teacher TEXT NOT NULL,
    room TEXT NOT NULL,
    batch TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (end_min > start_min));

CREATE INDEX IF NOT EXISTS classes_day_time ON classes (day, start_min);
CREATE INDEX IF NOT EXISTS classes_teacher ON classes (teacher, day, start_min);
CREATE INDEX IF NOT EXISTS classes_room ON classes (room, day, start_min);
CREATE INDEX IF NOT EXISTS classes_batch ON classes (batch, day, start_min);
