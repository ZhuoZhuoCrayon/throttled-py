from fastapi import FastAPI, Request
from throttled.asyncio.contrib.fastapi import (
    Limiter,
    RateLimitExceededError,
    RateLimitMiddleware,
    get_remote_address,
    rate_limit_exceeded_handler,
)

# 1) Create a limiter that uses the direct client IP as the quota key.
limiter = Limiter("100/m", key_func=get_remote_address)

# 2) Wire FastAPI integration hooks:
#    middleware adds RateLimit-* headers
#    handler renders HTTP 429 responses.
app = FastAPI()
app.add_middleware(RateLimitMiddleware)
app.add_exception_handler(RateLimitExceededError, rate_limit_exceeded_handler)


# 3) Apply the limiter to a route.
@app.get("/items")
@limiter.limit()
async def list_items(request: Request) -> dict[str, list[str]]:
    return {"items": ["apple", "banana"]}
