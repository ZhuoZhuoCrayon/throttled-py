from flask import Flask
from throttled.contrib.flask import Limiter
from throttled.store import MemoryStore

store = MemoryStore()
app = Flask(__name__)
limiter = Limiter(
    "2/m",
    app=app,
    store=store,
    key_prefix="storefront",
)


@app.get("/items")
@limiter.limit()
def list_items() -> dict[str, list[str]]:
    return {"items": ["apple", "banana"]}
