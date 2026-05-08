from fastapi import FastAPI, Request
from throttled.asyncio.contrib.fastapi import (
    Limiter,
    RateLimitExceededError,
    RateLimitMiddleware,
    rate_limit_exceeded_handler,
)
from throttled.asyncio.store import MemoryStore

# Share a single store across routes.
store = MemoryStore()
limiter = Limiter("10/m", store=store)

app = FastAPI()
app.add_middleware(RateLimitMiddleware)
app.add_exception_handler(RateLimitExceededError, rate_limit_exceeded_handler)


@app.get("/items")
@limiter.limit()
async def list_items(request: Request) -> dict[str, list[str]]:
    return {"items": ["apple", "banana"]}


# Per-route quota override: stricter limit for admin.
@app.get("/admin")
@limiter.limit("1/m")
async def admin_panel(request: Request) -> dict[str, str]:
    return {"status": "ok"}
