from flask import Flask, request
from throttled.contrib.flask import Limiter


# 1) Read an application principal from the active Flask request.
def get_api_key() -> str:
    return request.headers.get("X-API-Key", "anonymous")


app = Flask(__name__)
limiter = Limiter("2/m", app=app, key_func=get_api_key)


# 2) Each API key receives an independent quota bucket.
@app.get("/items")
@limiter.limit()
def list_items() -> dict[str, list[str]]:
    return {"items": ["apple", "banana"]}
