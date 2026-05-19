from fastapi import FastAPI, Request
from throttled.asyncio.contrib.fastapi import (
    Limiter,
    RateLimitExceededError,
    RateLimitMiddleware,
    rate_limit_exceeded_handler,
)
from throttled.asyncio.store import MemoryStore

# 1) Create a limiter with a shared store for all routes.
store = MemoryStore()
limiter = Limiter("10/m", store=store)

# 2) Wire FastAPI integration hooks:
#    middleware adds RateLimit-* headers
#    handler renders HTTP 429 responses.
app = FastAPI()
app.add_middleware(RateLimitMiddleware)
app.add_exception_handler(RateLimitExceededError, rate_limit_exceeded_handler)


# 3) Apply the default quota to one route.
@app.get("/items")
@limiter.limit()
async def list_items(request: Request) -> dict[str, list[str]]:
    return {"items": ["apple", "banana"]}


# 4) Override the quota for another route.
@app.get("/admin")
@limiter.limit("1/m")
async def admin_panel(request: Request) -> dict[str, str]:
    return {"status": "ok"}
