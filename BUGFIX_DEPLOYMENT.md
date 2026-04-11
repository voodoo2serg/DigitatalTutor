# DigitalTutor Deployment Bugfix Report

**Date:** 2026-04-12  
**Deployed by:** Kimi Claw  
**Server:** 213.171.9.30  
**Repository:** MediaCod22/DigitatalTutor

---

## Summary

During Docker Compose deployment of DigitalTutor to production server, several bugs were identified and fixed across the web, backend, and bot components. All fixes are documented below.

---

## 🐛 Bug List & Fixes

### 1. Web Container — Missing Prisma Client Generation

**File:** `web/Dockerfile`  
**Severity:** 🔴 Critical  
**Error:** `Cannot find module '@prisma/client'`

**Root Cause:**  
Dockerfile copied source files but didn't generate Prisma client before building Next.js app.

**Fix Applied:**
```dockerfile
# Added before build:
RUN bunx prisma generate
```

---

### 2. Web Container — Missing Public Folder

**File:** `web/Dockerfile`  
**Severity:** 🟡 Medium  
**Error:** `COPY failed: file not found: /app/public`

**Root Cause:**  
Dockerfile tried to copy `public/` folder which doesn't exist in the project.

**Fix Applied:**
```dockerfile
# Removed line:
# COPY --from=builder /app/public ./public
```

---

### 3. Next.js Config — Unsupported ESLint Key

**File:** `web/next.config.ts`  
**Severity:** 🟡 Medium  
**Error:** `Invalid next.config.ts options: Unrecognized key(s): 'eslint'`

**Root Cause:**  
`eslint` key is not supported in Next.js 16.x config.

**Fix Applied:**
```typescript
// Removed:
eslint: { ignoreDuringBuilds: true }
```

---

### 4. Backend — Missing DATABASE_URL Environment Variable

**File:** `.env`  
**Severity:** 🔴 Critical  
**Error:** `Could not parse SQLAlchemy URL from string ''`

**Root Cause:**  
Backend expected `DATABASE_URL` but only `POSTGRES_*` variables were defined.

**Fix Applied:**
```bash
# Added to .env:
DATABASE_URL=postgresql+asyncpg://teacher:KpianDU38usOE7w6OaZxV9ZFZnfe5@postgres:5432/teaching
```

---

### 5. Backend — Missing AsyncSessionLocal Export

**File:** `backend/app/core/database.py`  
**Severity:** 🔴 Critical  
**Error:** `ImportError: cannot import name 'AsyncSessionLocal'`

**Root Cause:**  
`web_auth.py` imported `AsyncSessionLocal` which wasn't exported from database module.

**Fix Applied:**
```python
# Added after async_session definition:
AsyncSessionLocal = async_session
```

---

### 6. Backend — Shared Models Import Path

**File:** `backend/app/core/database.py`  
**Severity:** 🔴 Critical  
**Error:** `ModuleNotFoundError: No module named 'bot.models'`

**Root Cause:**  
Backend imports shared models from `bot/` directory which wasn't accessible in container.

**Fix Applied:**
```yaml
# docker-compose.yml - added volume mount:
volumes:
  - ./bot:/app/bot:ro
```

---

### 7. Nginx Config — Directory Instead of File

**File:** `nginx/nginx.conf`  
**Severity:** 🔴 Critical  
**Error:** `mount ... failed: not a directory`

**Root Cause:**  
`nginx.conf` existed as an empty directory instead of a file.

**Fix Applied:**
```nginx
# Created proper nginx.conf:
worker_processes auto;
error_log /var/log/nginx/error.log warn;

upstream backend { server digitatal-backend:8000; }
upstream web { server digitatal-web:3000; }

server {
    listen 80;
    
    location /api/ { proxy_pass http://backend/; }
    location /docs { proxy_pass http://backend/docs; }
    location / { proxy_pass http://web; }
}
```

---

### 8. Port Conflict — NocoDB vs BestSolution

**File:** `docker-compose.yml`  
**Severity:** 🟡 Medium  
**Error:** `Bind for 0.0.0.0:8081 failed: port is already allocated`

**Root Cause:**  
BestSolution already uses port 8081.

**Fix Applied:**
```yaml
# Changed NocoDB port:
ports:
  - "8087:8080"  # was 8081:8080
```

---

### 9. Bot — aiogram 3.x StateFilter Incompatibility

**File:** `bot/handlers/works_review.py`  
**Severity:** 🔴 Critical  
**Error:** `aiogram.exceptions.UnsupportedKeywordArgument: remove {'state'} arguments`

**Root Cause:**  
aiogram 3.x doesn't accept `state` parameter in decorator; must use `StateFilter`.

**Fix Applied:**
```python
# Changed import:
from aiogram.filters.state import StateFilter  # was: aiogram.fsm.state

# Changed decorator:
@review_router.message(F.text, StateFilter("waiting_review_text"))
# was: @review_router.message(F.text, state="waiting_review_text")
```

---

### 10. Bot — Missing THROTTLING_DELAY in Config Class

**File:** `bot/config.py`  
**Severity:** 🔴 Critical  
**Error:** `AttributeError: 'Config' object has no attribute 'THROTTLING_DELAY'`

**Root Cause:**  
`THROTTLING_DELAY` was a module-level variable, not part of `Config` dataclass.

**Fix Applied:**
```python
@dataclass
class Config:
    # ... existing fields ...
    
    # Added:
    THROTTLING_DELAY: int = int(os.getenv("THROTTLING_DELAY", "15"))
```

---

## 📋 Deployment Commands Used

```bash
# Cleanup previous containers
docker rm -f $(docker ps -aq --filter "name=digitatal")

# Build and start all services
cd /opt/DigitatalTutor
docker compose build --no-cache web backend bot
docker compose up -d

# Verify health
docker compose ps
curl http://localhost:8000/docs
curl http://localhost:8098
```

---

## ✅ Verification Results

| Service | Status | Endpoint |
|---------|--------|----------|
| Backend API | ✅ Healthy | http://213.171.9.30:8000/docs |
| Web UI | ✅ Running | http://213.171.9.30:8098 |
| Telegram Bot | ✅ Polling | @nauker_helper_bot |
| PostgreSQL | ✅ Healthy | Port 5432 |
| Redis | ✅ Healthy | Port 6379 |
| NocoDB | ✅ Running | http://213.171.9.30:8087 |
| Ollama | ✅ Running | Port 11434 |

---

## 📝 Recommendations

1. **Add healthcheck to bot container** — currently no healthcheck implemented
2. **Use specific image tags** — replace `latest` with version pins
3. **Add pre-commit hooks** — validate aiogram 3.x syntax
4. **Document shared model dependency** — backend depends on bot models

---

## Files Modified

- `.env` — Added DATABASE_URL
- `web/Dockerfile` — Added prisma generate, removed public copy
- `web/next.config.ts` — Removed eslint key
- `backend/app/core/database.py` — Added AsyncSessionLocal export
- `backend/Dockerfile` — Build context includes shared code
- `docker-compose.yml` — Added bot volume mount, changed NocoDB port
- `nginx/nginx.conf` — Created from scratch
- `bot/config.py` — Added THROTTLING_DELAY to Config class
- `bot/handlers/works_review.py` — Fixed StateFilter import and usage

---

**Deployed by:** Kimi Claw  
**Timestamp:** 2026-04-12 05:50 MSK
