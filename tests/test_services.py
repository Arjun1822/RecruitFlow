import pytest
from backend.database.connection import SessionLocal
from backend.database.models import Application
from backend.data_generator.generator import generate_dataset
from backend.services.application_service import transition_application

def test_invalid_application_transition(mysql_database_url):
    database_url = mysql_database_url
    generate_dataset("starter", seed=20261022, export=False, database_url=database_url)
    from backend.database.connection import make_session
    session = make_session(database_url); app = session.query(Application).first()
    with pytest.raises(ValueError):
        transition_application(session, app.id, "Hired")
    engine = session.get_bind(); session.close(); engine.dispose()
