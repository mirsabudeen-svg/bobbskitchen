# Sprint 8 — Pilot Simulation & Hardening

**Goal:** Verify the system survives a real Saturday before real customers do.
**Stack:** FastAPI · PostgreSQL 15 · asyncpg · SQLAlchemy 2.0 · Pydantic v2 · WebSocket

---

## Directory Structure

```
sprint8/
├── tests/
│   ├── conftest.py              # Shared fixtures, factories, DB setup
│   ├── load/
│   │   ├── test_load.py         # Concurrent sessions, order burst, WS fan-out
│   │   └── locustfile.py        # Sustained load (Locust)
│   ├── simulation/
│   │   └── test_saturday_simulation.py  # Full 40-customer Saturday end-to-end
│   ├── staff/
│   │   └── test_staff_workflow.py       # Queue, transitions, payment, reconciliation
│   └── recovery/
│       └── test_recovery.py     # Backend / Postgres / Redis restart scenarios
├── scripts/
│   └── run_sprint8.sh           # Convenience runner
├── config/
│   └── ci.yml                   # GitHub Actions workflow
└── pytest.ini
```

---

## Setup

```bash
# 1. Install test dependencies
pip install pytest pytest-asyncio httpx anyio asyncpg \
            sqlalchemy[asyncio] alembic faker websockets \
            locust psutil

# 2. Set test DB URL (default: postgresql+asyncpg://bobb:bobb@localhost:5432/bobb_test)
export TEST_DATABASE_URL=postgresql+asyncpg://bobb:bobb@localhost:5432/bobb_test

# 3. Run migrations on the test DB
DATABASE_URL=$TEST_DATABASE_URL alembic upgrade head
```

---

## Running the Tests

### Quick (daily dev loop)
```bash
# All core tests — no Docker, no Locust
./scripts/run_sprint8.sh local
# or directly:
pytest tests/load/test_load.py tests/simulation/ tests/staff/ -v -s
```

### Locust sustained load (interactive)
```bash
./scripts/run_sprint8.sh locust
# Visit http://localhost:8089
# Set: host=http://localhost:8000, users=10, spawn-rate=2, run-time=5m
```

### Locust headless (CI-style)
```bash
./scripts/run_sprint8.sh ci
# Runs 10 users for 120 seconds
# Report saved to reports/locust_report.html
```

### Recovery tests (requires Docker Compose)
```bash
# Start your full stack first:
docker compose -p bobb up -d --wait

# Then run:
./scripts/run_sprint8.sh recovery
```

### Everything
```bash
./scripts/run_sprint8.sh all
```

---

## CI Integration

Copy `config/ci.yml` to `.github/workflows/sprint8.yml` in your repo.

Pipeline jobs:
| Job | Trigger | Requirements |
|-----|---------|-------------|
| `test-core` | Every push / PR | PostgreSQL service container |
| `locust-headless` | After core passes | PostgreSQL + API process |
| `test-recovery` | Push to `main` only | Docker Compose |

---

## Pass / Fail Criteria

### Load Tests
| Metric | Target |
|--------|--------|
| 40 concurrent sessions | All 201, no duplicates |
| p95 session-create latency | < 300ms |
| 60 concurrent orders | All 201, no duplicate IDs |
| p95 order-create latency | < 500ms |
| Short ref uniqueness under race | Zero duplicates |
| Idempotency under 5× concurrent retry | Exactly 1 DB row |
| WS broadcast to 10 staff clients | All receive within 2s |
| DTF throughput model | Median wait ≤ 14 min |

### Saturday Simulation
| Metric | Target |
|--------|--------|
| 40 orders → collected | 100% |
| All orders paid | 100% |
| Reprint orders have reprint_count ≥ 1 | 100% |
| Reconciliation totals match sum of orders | Exact match |
| No duplicate short refs | Zero duplicates |

### Staff Workflow
| Test | Target |
|------|--------|
| All valid transitions | 200 |
| All invalid transitions | 409 with correct error body |
| `collected` without payment | 409 `payment_required_before_collection` |
| `collected` is terminal | All escape attempts → 409 |
| Print spec on order items | `image_url`, `print_placement` non-null |
| Short-ref lookup | Correct order, case-insensitive |
| Payment idempotency | 200 on duplicate, same state |

### Recovery Tests
| Scenario | Target |
|----------|--------|
| Backend restart | Order persists, status update succeeds post-restart |
| Idempotency across restart | No duplicate rows |
| PostgreSQL restart | Orders accessible, new orders creatable |
| Staff queue after restart | Serves DB truth (not stale WS cache) |
| WS reconnect after restart | New connection within 5s |
| WS broadcast after reconnect | Staff client receives order_update |
| Redis restart | Core operations unaffected |
| Redis full outage | Orders created and transitioned successfully |

### Locust (10 users, 5 minutes)
| Metric | Target |
|--------|--------|
| Error rate | < 1% |
| p95 response time | < 500ms |
| Failure rate (Locust exit code) | 0 |

---

## One Thing to Fix Before Running

The recovery tests use a `POST /api/v1/debug/variants` endpoint to seed
design variants without going through the full AI generation flow.
**Add this endpoint to your app before running Sprint 8:**

```python
# backend/app/api/debug.py
# Guard with: if not settings.debug: raise HTTPException(404)

@router.post("/variants", response_model=VariantResponse, status_code=201)
async def create_debug_variant(body: DebugVariantRequest, db: AsyncSession = Depends(get_db)):
    """Seed a variant for load/recovery testing. Disabled in production."""
    if not settings.debug:
        raise HTTPException(status_code=404)
    variant = DesignVariant(
        id=uuid.uuid4(),
        session_id=body.session_id,
        image_url=body.image_url,
        prompt=body.prompt,
        style=body.style,
        is_fallback=False,
        is_selected=False,
    )
    db.add(variant)
    await db.commit()
    await db.refresh(variant)
    return VariantResponse(variant=variant)
```

Set `DEBUG=true` in your local and CI `.env`. Never set it in production.
