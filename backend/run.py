from app import create_app

app = create_app()

from app.extensions import db
from sqlalchemy import event

with app.app_context():

    @event.listens_for(db.engine, "connect")
    def connect(dbapi_connection, connection_record):
        print("NEW DB CONNECTION")

    @event.listens_for(db.engine, "close")
    def close(dbapi_connection, connection_record):
        print("DB CONNECTION CLOSED")

@app.route("/")
def health_check():
    return {"status": "ok", "message": "Balapedia API is running"}, 200

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=8080,
        use_reloader=False,
    )
