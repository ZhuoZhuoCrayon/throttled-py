from flask import Flask
from throttled.contrib.flask import Limiter

# 1) Create the application and eagerly initialize a shared route quota.
app = Flask(__name__)
limiter = Limiter("2/m", app=app)


# 2) Keep the Flask route decorator above the limiter decorator.
@app.get("/items")
@limiter.limit()
def list_items() -> dict[str, list[str]]:
    return {"items": ["apple", "banana"]}
