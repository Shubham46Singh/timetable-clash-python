## Design decision: the boundary

**Overlap is not equality.** Two classes clash when each one starts before the
other ends:

    a_start < b_end  and  b_start < a_end

That one line catches partial overlap from either side (10:00-11:00 vs
10:30-11:30), full containment either way, and identical slots.

**Boundary choice: a class ending at 11:00 does NOT clash with one starting at
11:00.** Intervals are half-open, `[start, end)`. The end minute belongs to the
next period, so the class occupies 10:00 up to but excluding 11:00.

Why:
1. It matches reality - one lot of students leaves as the next arrives, and a
   teacher or room can be used back to back. Treating that as a clash would
   make a 09:00-10:00, 10:00-11:00, 11:00-12:00 day impossible to enter.
2. It is consistent: with closed intervals, "10:00-11:00" would secretly occupy
   61 minutes. Half-open intervals give length = end - start exactly.
3. It is the only rule under which the tidy day (seed data, lunch 13:00-14:00)
   works: a class ending at 13:00 is allowed, one running to 13:01 is not.
4. Comparison is done on integer minutes past midnight, never strings, so
   "9:00" vs "10:00" cannot sort wrongly.

Tests: `tests/unit/test_clashes.py::TestOverlaps` covers left/right partial,
both containments, identical, touching both ways, and separate slots.

## Running

    docker compose up --build
    curl localhost:8080/health

    pip install -r requirements-dev.txt
    ruff check .
    pytest tests/unit --cov=app.clashes --cov-report=term-missing
    # integration needs Postgres+Redis with migrations applied
    pytest tests/integration --cov=app
