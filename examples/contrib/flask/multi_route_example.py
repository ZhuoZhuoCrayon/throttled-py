from flask import Flask
from throttled.contrib.flask import Limiter
from throttled.store import MemoryStore

# A module-level extension object supports the Flask application-factory pattern.
limiter = Limiter("10/m", store=MemoryStore())


def create_app() -> Flask:
    app = Flask(__name__)
    limiter.init_app(app)

    @app.get("/items")
    @limiter.limit()
    def list_items() -> dict[str, list[str]]:
        return {"items": ["apple", "banana"]}

    @app.get("/admin")
    @limiter.limit("1/m")
    def admin_panel() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
