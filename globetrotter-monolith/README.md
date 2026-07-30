# GlobeTrotter Travel Assistant — Phase 1: Monolith

A single Flask application handling every concern — routing, authentication,
business logic, and data storage — in one process, reading and writing a
single JSON file. This is the deliberate starting point of the semester
project, built to be replaced piece by piece in later phases.

## Architecture

```
Client → API Layer (Flask routes) → Business Logic → Data Access → data.json
```

| Layer | File | Responsibility |
|---|---|---|
| API | `app.py` | HTTP routes, request validation, status codes |
| Business logic | `business_logic.py` | Recommendation scoring, destination search |
| Auth | `auth.py` | Password hashing, JWT issuing/verification |
| Data access | `data_access.py` | The *only* file that touches `data/data.json` |

## Setup

```bash
python3 -m venv venv
source venv/bin/activate        # venv\Scripts\activate on Windows
pip install -r requirements.txt
python3 app.py
```

Server runs at `http://localhost:5000`.

## Running tests

```bash
pytest tests/ -v
```

11 tests cover registration, login, destination search/filtering, protected
recommendation and itinerary endpoints, and rejection of invalid input.

## Endpoints

| Method | Path | Auth required | Description |
|---|---|---|---|
| POST | `/register` | No | Create a user account |
| POST | `/login` | No | Get a JWT token |
| GET | `/destinations` | No | Search/filter destinations (`?q=`, `?tag=`, `?region=`) |
| GET | `/recommendations` | Yes | Personalized destination suggestions |
| POST | `/itineraries` | Yes | Create an itinerary |
| GET | `/itineraries` | Yes | List the current user's itineraries |
| GET | `/health` | No | Liveness check |

Authenticated requests need `Authorization: Bearer <token>`.

### Example

```bash
curl -X POST http://localhost:5000/register \
  -H "Content-Type: application/json" \
  -d '{"username":"lea","email":"lea@example.com","password":"secret123","preferences":["beach"]}'

curl -X POST http://localhost:5000/login \
  -H "Content-Type: application/json" \
  -d '{"email":"lea@example.com","password":"secret123"}'
# → { "token": "..." }

curl http://localhost:5000/recommendations \
  -H "Authorization: Bearer <token>"
```

## Why a monolith, and why JSON?

This phase is meant to be *outgrown*. Everything here works, but every
design choice has a built-in ceiling:

- **JSON file storage** has no transactions, no indexing, and no safe
  concurrent writes — two simultaneous requests can race on the same file.
- **One process** means one bug anywhere (even in an unrelated module)
  can crash the entire API, including features that had nothing to do
  with the failure.
- **One deployable unit** means shipping a fix to the sharing feature
  requires redeploying auth, search, and recommendations too.
- **Vertical-only scaling**: the only way to handle more load is a bigger
  server. You cannot scale the recommendation engine independently of
  the login endpoint, even if it's the one getting hammered.
- **One shared codebase** makes merge conflicts more likely as the team
  grows, since everyone edits the same files for unrelated features.

These aren't bugs — they're the point of Phase 1. Later phases introduce
a real database, split this into independent services, add message
queues, and address exactly these limitations one at a time.

## Tech stack

- **Backend:** Python 3, Flask
- **Data:** JSON file (`data/data.json`)
- **Auth:** PyJWT + Werkzeug password hashing
- **Testing:** pytest
