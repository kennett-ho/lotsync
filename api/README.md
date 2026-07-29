# Running the API

Phase 3, Sprint 2's read-only API layer. See `API_CONTRACTS.md` for
the DTOs it serves and `PHASE_3_SPRINT_2_REVIEW.md` for what's actually
implemented, what's deliberately deferred, and why.

```
cd lotsync
PYTHONPATH=.. python -m pip install -r requirements.txt
PYTHONPATH=.. uvicorn lotsync.api.app:app --reload
```

(`requirements.txt`, at the repo root, is where `python-multipart` --
new as of Phase 3, Sprint 4, required by `POST /inventory-sync/run`'s
file-upload form fields, this project's first write route -- is
tracked, along with the rest of the backend's dependencies.)

(Adjust `PYTHONPATH` to wherever the `lotsync/` package's parent
directory lives, same convention as `tests/README.md`.)

Once running, interactive API docs are available at `/docs`
(FastAPI's built-in Swagger UI, generated directly from
`api/dtos.py`'s Pydantic models -- not a separately maintained document).

## What's here

| Route | Screen it serves | Source |
|---|---|---|
| `GET /dashboard` | Lot Manager / Controller dashboards | `api/routers/dashboard.py` |
| `GET /vehicles` | Vehicle List | `api/routers/vehicles.py` |
| `GET /vehicles/{vin}` | Vehicle Detail (this sprint's reference implementation) | `api/routers/vehicles.py` |
| `GET /tasks` | Tasks | `api/routers/tasks.py` |
| `GET /recommendations` | Recommendations / "AI Suggestions" | `api/routers/recommendations.py` |
| `GET /activity` | Activity | `api/routers/activity.py` |
| `GET /reports` | Reports (backend-supported subset only) | `api/routers/reports.py` |

## What's NOT here, on purpose

No write routes, no authentication, no session, no permission checks,
no frontend wiring. See `PHASE_3_SPRINT_2_REVIEW.md`'s Risks section
for the reasoning behind each.

## Testing

Uses FastAPI's own `TestClient` (built on `httpx`), the first time this
project has needed a test dependency beyond the standard library --
see `tests/README.md`'s "no external dependencies" note, which predates
this project having any web-framework code to test at all. Query-layer
and DTO-level tests remain plain `unittest`, no new dependency needed,
exactly as before.

```
cd lotsync
PYTHONPATH=.. python -m unittest discover -s tests -p "test_*.py"
```
