# BOBB AI Platform — Sprint 0 Code Review

**Reviewer**: Staff Engineer  
**Date**: 2026-06-11  
**Branch**: `claude/inspiring-albattani-ladj5g`  
**Scope**: FastAPI structure, SQLAlchemy models, Alembic migrations, WebSocket implementation, Docker configuration, Zustand store, CI workflows, environment configuration

---

## Executive Summary

Sprint 0 is a well-structured, production-aware scaffold. All 10 database tables are correct and match `database_schema.md` exactly. The circular deferred FK (`designs.selected_variant_id`) is implemented correctly with `use_alter=True`. The `variant_number` column has no CHECK constraint — correct. All monetary values use integer paise. The WebSocket handler sends `session_resumed` on connect with `is_reconnect: bool`. The frontend API client never hardcodes `localhost` and builds WebSocket URLs from `VITE_API_BASE_URL`. The CI workflows are correct, cache pip and npm, and run migrations before tests. No Critical or High issues were found.

Three Medium and four Low issues are documented below, all straightforward to fix in Sprint 1.

---

## Critical Issues

None.

---

## High Issues

None.

---

## Medium Issues

### M-01 — Frontend Dockerfile uses `npm run dev` in production container
**File**: `frontend/Dockerfile` (CMD line)

The Docker image runs Vite's dev server (`npm run dev -- --host 0.0.0.0`). Vite's dev server is not suitable for production: it performs no-bundle HMR, is single-threaded, and the Vite docs explicitly warn against using it for serving production traffic. On the Windows PC (single screen, no live-reload needed), this is a performance and reliability risk.

**Fix**: Build the static bundle and serve with a lightweight static server:
```dockerfile
RUN npm run build
CMD ["npx", "serve", "-s", "dist", "-l", "3000"]
```
Or use `nginx:alpine` to serve `dist/`. This also reduces the container image size significantly.

---

### M-02 — Redis service has no healthcheck; backend `depends_on` only waits for Postgres
**File**: `docker-compose.yml` (lines 18–21, 36–38)

Redis has no `healthcheck` block. The `backend` service `depends_on` uses `condition: service_healthy` for Postgres (correct), but has no dependency on Redis at all. If Redis is used in Sprint 2+ (session caching, WebSocket pub/sub), the backend can start before Redis is ready and the first connection attempt will fail.

**Fix**: Add a Redis healthcheck and a conditional dependency:
```yaml
redis:
  image: redis:7
  ports:
    - "6379:6379"
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
    interval: 5s
    timeout: 3s
    retries: 5

backend:
  depends_on:
    postgres:
      condition: service_healthy
    redis:
      condition: service_healthy
```

---

### M-03 — Database engine created at module import time; test isolation requires overriding settings
**File**: `backend/app/db/base.py` (lines 14–22)

`get_engine()` lazily creates the engine the first time it's called and stores it in a module-level global `_engine`. The `TestClient` used in tests imports `app.main` which triggers the engine creation using whatever `DATABASE_URL` is in the environment (or `.env`). If the `.env` file is present during CI with a different URL, tests could connect to the wrong database. More critically, there is no way to inject a test database URL without patching the module global.

**Fix**: Initialise the engine inside the FastAPI lifespan and store it on `app.state`, then have `get_db` read from `request.app.state`. This is the idiomatic FastAPI pattern for dependency-injectable infrastructure:
```python
# In lifespan:
app.state.engine = create_async_engine(settings.database_url, ...)
app.state.session_factory = async_sessionmaker(app.state.engine, ...)
yield
await app.state.engine.dispose()

# In get_db:
async def get_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    async with request.app.state.session_factory() as session:
        yield session
```
Tests can then override `app.state` with a test engine without monkeypatching globals.

---

## Low Issues

### L-01 — `GET /products` returns 501 with `content-type: application/json`; should be consistent with other stubs
**File**: `backend/app/api/products.py`

`GET /products` returns `{"detail": "Not implemented — Sprint 1"}` with status 501. The frontend's `api.getProducts()` call will receive a non-2xx status and throw. This is expected for a stub, but the error format should match FastAPI's standard `HTTPException` shape to make Sprint 1 wiring easier.

**Fix**: Replace the stub body with `raise HTTPException(status_code=501, detail="Not implemented — Sprint 1")` so it matches FastAPI's error envelope.

---

### L-02 — `backend/.env.example` has `VITE_API_BASE_URL` mixed in
**File**: `backend/.env.example` (last line)

The backend `.env.example` ends with `VITE_API_BASE_URL=http://192.168.1.10:8420`. This is a frontend variable (Vite prefix) and does not belong in the backend env file. It will be ignored by `pydantic-settings` due to `extra="ignore"`, but it will confuse anyone reading the file.

**Fix**: Move this line to `frontend/.env.example` only. `backend/.env.example` already has `PORT=8420` which serves the same documentation purpose.

---

### L-03 — `useWebSocket` reconnect resets `sessionId` on every `useEffect` re-render
**File**: `frontend/src/hooks/useWebSocket.ts` (line 28, dependency array)

The `useEffect` dependency array includes `[sessionId, handleMessage]`. `handleMessage` is wrapped in `useCallback([])` (stable), but `sessionId` changing will close and reopen the WebSocket. This is correct for session changes, but if the parent component re-renders frequently (e.g., state updates) and `sessionId` is passed down as a new string reference each time rather than read from the store directly inside the hook, there is a risk of spurious reconnects. Currently the hook reads `sessionId` from `App.tsx` via props, which is stable from Zustand.

**Fix** (minor): Read `sessionId` from the Zustand store directly inside the hook to eliminate the dependency on parent render cycles entirely:
```typescript
const sessionId = useSessionStore((s) => s.sessionId);
// Remove sessionId from the hook's parameter
```

---

### L-04 — `backend/.mypy_cache` is gitignored correctly but `mypy` is not in CI's `--strict` mode
**File**: `.github/workflows/backend.yml` (mypy step)

The CI runs `mypy app tests` without flags. `mypy` without `--strict` will not catch missing type annotations, `Any` propagation, or untyped function parameters — the main value of mypy. Sprint 0 code is clean enough that enabling stricter flags now costs nothing and prevents type debt accumulating over later sprints.

**Fix**: Add to `pyproject.toml` or `mypy.ini`:
```ini
[mypy]
strict = true
plugins = pydantic.mypy
```
Or pass `--strict` in the CI step. If some third-party stubs are missing, use `ignore_missing_imports = true` per-module rather than weakening the whole check.

---

## Verdict

**Sprint 0 is approved for merge.**

No Critical or High issues were found. The three Medium issues (dev server in Docker, missing Redis healthcheck, module-global DB engine) should be fixed in Sprint 1 before the first integration tests against a real database. The four Low issues are polish items.

The scaffold faithfully implements every architecture constraint: deferred circular FK, no `variant_number` CHECK, paise-only monetary values, `ws_path` in session response, `session_resumed` on WebSocket connect, `--workers 1` enforced in both Dockerfile and compose command, and `VITE_API_BASE_URL` used consistently with no hardcoded `localhost`.
