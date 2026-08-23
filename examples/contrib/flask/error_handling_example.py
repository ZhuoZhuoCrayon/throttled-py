from flask import Flask, Response, jsonify
from throttled.contrib.flask import Limiter, RateLimitExceededError
from throttled.exceptions import StoreUnavailableError

app = Flask(__name__)
limiter = Limiter("2/m", app=app)


# Customize quota exhaustion responses.
@app.errorhandler(RateLimitExceededError)
def handle_rate_limit(
    exc: RateLimitExceededError,
) -> tuple[Response, int | None, dict[str, str]]:
    headers = {
        name: value
        for name, value in exc.get_headers()
        if name.lower() != "content-type"
    }
    return jsonify(detail=exc.description), exc.code, headers


# Customize store outage responses.
@app.errorhandler(StoreUnavailableError)
def handle_store_outage(exc: StoreUnavailableError) -> tuple[dict[str, str], int]:
    return {"detail": "Rate limit service temporarily unavailable"}, 503


# Apply the limiter to a route.
@app.get("/items")
@limiter.limit()
def list_items() -> dict[str, list[str]]:
    return {"items": ["apple", "banana"]}
