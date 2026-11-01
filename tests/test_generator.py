from backend.data_generator.generator import generate_dataset
from backend.database.connection import make_session
from backend.database.models import Anomaly

def test_starter_generation(mysql_database_url):
    result = generate_dataset("starter", seed=20261022, export=False, database_url=mysql_database_url)
    assert result["requisitions"] == 10
    assert result["candidates"] == 100
    assert result["applications"] > 0
    session = make_session(mysql_database_url)
    anomalies = session.query(Anomaly).order_by(Anomaly.issue_id).all()
    assert [row.issue_id for row in anomalies] == [f"ANOM-{index:05d}" for index in range(1, 6)]
    assert all(row.ground_truth == "positive" for row in anomalies)
    engine = session.get_bind(); session.close(); engine.dispose()
