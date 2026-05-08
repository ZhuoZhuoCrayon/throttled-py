from fastapi import FastAPI, Request
from throttled.asyncio.contrib.fastapi import (
    Limiter,
    RateLimitExceededError,
    RateLimitMiddleware,
    rate_limit_exceeded_handler,
)


# Custom key_func: rate-limit by API key instead of client IP.
def get_api_key(request: Request) -> str:
    return request.headers.get("X-API-Key", "anonymous")


limiter = Limiter("2/m", key_func=get_api_key)

app = FastAPI()
app.add_middleware(RateLimitMiddleware)
app.add_exception_handler(RateLimitExceededError, rate_limit_exceeded_handler)


@app.get("/items")
@limiter.limit()
async def list_items(request: Request) -> dict[str, list[str]]:
    return {"items": ["apple", "banana"]}
