import os
import redis
from rq import Queue
from flask import Flask

# Configuration de Redis + Queue RQ
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
redis_conn = redis.from_url(redis_url)
queue = Queue(connection=redis_conn)

def create_app():
    app = Flask(__name__)

    from database import initialize_db
    @app.cli.command("init-db")
    def init_db():
        initialize_db()
        print(" Base de données initialisée.")

    # Ajoute ceci pour que les routes soient prises en compte
    from app import register_routes
    register_routes(app)

    return app
