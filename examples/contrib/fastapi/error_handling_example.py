from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from throttled.asyncio.contrib.fastapi import (
    Limiter,
    RateLimitExceededError,
    RateLimitMiddleware,
    rate_limit_exceeded_handler,
)
from throttled.exceptions import StoreUnavailableError

app = FastAPI()
app.add_middleware(RateLimitMiddleware)
limiter = Limiter("2/m")


# Customize quota exhaustion responses.
async def handle_rate_limit(request: Request, exc: Exception) -> Response:
    response = await rate_limit_exceeded_handler(request, exc)
    response.headers["X-Support"] = "support@example.com"
    return response


app.add_exception_handler(RateLimitExceededError, handle_rate_limit)


# Customize store outage responses.
async def handle_store_outage(request: Request, exc: Exception) -> Response:
    return JSONResponse(
        status_code=503,
        content={"detail": "Rate limit service temporarily unavailable"},
    )


app.add_exception_handler(StoreUnavailableError, handle_store_outage)


# Apply the limiter to a route.
@app.get("/items")
@limiter.limit()
async def list_items(request: Request) -> dict[str, list[str]]:
    return {"items": ["apple", "banana"]}
