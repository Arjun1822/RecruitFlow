from backend.data_generator.generator import generate_dataset
from backend.database.connection import SessionLocal
from backend.database.models import Application
from backend.services.screening_service import screen_application

def test_screening_explains_score(mysql_database_url):
    database_url = mysql_database_url
    generate_dataset("starter", seed=20261022, export=False, database_url=database_url)
    from backend.database.connection import make_session
    session = make_session(database_url); result = screen_application(session, session.query(Application).first().id)
    assert 0 <= result["score"] <= 100
    assert "matched_skills" in result and "missing_skills" in result
    engine = session.get_bind(); session.close(); engine.dispose()
