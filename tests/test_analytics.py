from backend.analytics.metrics import build_analytics_report, calculate_metrics
from backend.data_generator.generator import generate_dataset
from backend.database.connection import make_session

def test_metrics_are_database_derived(mysql_database_url):
    generate_dataset("starter", 20261022, False, mysql_database_url)
    session = make_session(mysql_database_url)
    metrics = calculate_metrics(session)
    assert metrics["total_requisitions"] == 10
    assert metrics["total_applications"] == 150
    assert "average_time_to_hire_days" in metrics
    assert "feedback_completion_rate" in metrics
    assert "requisition_closure_rate" in metrics
    assert 0 <= metrics["offer_acceptance_rate"] <= 100
    report = build_analytics_report(session)
    assert sum(row["count"] for row in report["applications_by_stage"]) == 150
    assert report["monthly_trends"]
    engine = session.get_bind(); session.close(); engine.dispose()
