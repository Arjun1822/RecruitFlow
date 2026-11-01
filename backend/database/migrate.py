"""Create or upgrade RMS tables using the configured DATABASE_URL."""
from backend.database.connection import init_db, engine

if __name__ == "__main__":
    init_db(engine)
    with engine.connect() as connection:
        connection.exec_driver_sql("SELECT 1")
    print(f"Database initialized: {engine.url.render_as_string(hide_password=True)}")
