from flask import Flask
from throttled.contrib.flask import Limiter, get_remote_address

# 1) Opt in to a quota bucket for each direct client address.
app = Flask(__name__)
limiter = Limiter("100/m", app=app, key_func=get_remote_address)


# 2) Rate-limit the route by the address exposed by Flask.
@app.get("/items")
@limiter.limit()
def list_items() -> dict[str, list[str]]:
    return {"items": ["apple", "banana"]}
