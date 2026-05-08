from fastapi import FastAPI, Request
from throttled.asyncio.contrib.fastapi import (
    Limiter,
    RateLimitExceededError,
    RateLimitMiddleware,
    rate_limit_exceeded_handler,
)

# 1) Create a Limiter with a default quota.
limiter = Limiter("2/m")

# 2) Wire up the middleware and exception handler.
app = FastAPI()
app.add_middleware(RateLimitMiddleware)
app.add_exception_handler(RateLimitExceededError, rate_limit_exceeded_handler)


# 3) Decorate routes with @limiter.limit().
@app.get("/items")
@limiter.limit()
async def list_items(request: Request) -> dict[str, list[str]]:
    return {"items": ["apple", "banana"]}
