# Timetable and Clash Detection

**Language:** Python (FastAPI) &nbsp;|&nbsp; **Needs:** Postgres + Redis

This is a **starter**. The application already works. Your job is everything
that gets it building, tested and running in CI.

---

## You do not need Python installed

You will build this into a container, and the container brings its own
Python 3.12. You are not being asked to extend the app — you are being asked
to ship it.

---

## 1. What this app needs

| | |
|---|---|
| **Runtime** | Python 3.12 |
| **Install dependencies** | `pip install -r requirements.txt` |
| **Start the app** | `uvicorn app.main:app --host 0.0.0.0 --port 8080` |
| **Listens on** | port 8080, bound to `0.0.0.0` |
| **Environment variables** | `DATABASE_URL`, `REDIS_URL` |
| **Needs running first** | Postgres, Redis, and the migrations applied |

### What it does

Departments enter classes: a subject, a teacher, a room, a batch and a time slot. The system refuses anything that clashes and explains what it collided with, then generates the timetable three ways - per batch, per teacher and per room - from the same set of classes.

### Endpoints

```
GET  /health
GET  /classes                     everything on the timetable
POST /classes                     {"day":"mon","start":"10:00","end":"11:00",
                                   "subject":"DBMS","teacher":"Rao",
                                   "room":"A101","batch":"CSE-3A"}
POST /classes/check               the same check with nothing written - a dry run
DELETE /classes/{id}
GET  /timetable/{kind}/{value}    kind: batch | teacher | room
GET  /free/{day}?minutes=60       gaps long enough to put a class in
```

`/health` reports Postgres and Redis **separately**. If it says
`postgres: false` the app started fine and your compose wiring is wrong —
do not go looking in the application code.

### Migrations

`migrations/` holds `.sql` files applied **in filename order** before the app
starts. They create the tables and insert sample data. A container running
`psql` over them in order is enough; you do not need a migration tool.

---

## 2. What you must write

| File | What it has to do |
|---|---|
| `Dockerfile` | Install dependencies **before** copying source, pin the base image, do not run as root. |
| `docker-compose.yml` | App + Postgres + Redis + a migration step, one `docker compose up`. |
| `.circleci/config.yml` | lint → unit tests → integration tests → secret scan → image build |
| Unit tests | For `app/clashes.py`. No database, no network. |
| Integration tests | Against a real Postgres and Redis as CircleCI service containers. |

Then push your image to **your own Docker Hub account**, tagged `:1.0`.

### When it works

```bash
docker compose up --build
curl localhost:8080/health
```

```json
{"status":"ok","postgres":true,"redis":true}
```

---

## Where the marks are

`app/clashes.py` is **pure logic** — plain functions over plain data, no
database and no HTTP. Start your tests there. Use pytest:
`pytest --cov=app --cov-report=term-missing`. Minimum 70%.

`overlaps` is four lines and deserves about ten tests: partial overlap from the left, partial from the right, full containment either way, identical slots, touching at the boundary, and completely separate. Then `find_clashes` on top of it - room, teacher and batch each clashing on their own, all three at once, and the same slot on a different day clashing with nothing.

## Why Redis is here

The generated timetable views are read constantly - every student, every teacher, every noticeboard - and written perhaps twice a term. That is the shape a cache is for. Grouping every class by day and sorting it is wasted work on the four hundredth identical request.

The important half is invalidation: adding or deleting one class can change a batch view, a teacher view and a room view at once, so every write drops the whole `tt:` prefix rather than trying to be clever about which three keys went stale. A cache that serves a deleted class is worse than no cache.

## The hard part

**Overlap is not equality. 10:00-11:00 and 10:30-11:30 clash, and students usually miss that case.**

Then decide the boundary: does a class ending at 11:00 clash with one starting at 11:00? Say which you chose and why.

Write your answer in your README. It is worth more marks than the feature.

---

## Getting unstuck

| Symptom | Almost always |
|---|---|
| `/health` says `postgres: false` | Wrong hostname. In compose the host is the **service name**, not `localhost`. |
| Page will not load, logs fine | No `ports:` mapping, or bound to `127.0.0.1` not `0.0.0.0`. |
| `relation "..." does not exist` | Migrations did not run, or the app started before they finished. |
| Build takes minutes each time | `COPY . .` is above your dependency install. |
| CI cannot reach the database | In CircleCI service containers the host **is** `localhost` — opposite of compose. |
