from app.db.repositories import clear_repositories
from scripts.run_scenario import DEFAULT_OUTPUT, REPOSITORY, run_scenario

SCENARIO = REPOSITORY / "sample_docs" / "scenario_3_two_term_demo"


def test_scenario_3_through_upload_and_validation_apis(client, monkeypatch) -> None:
    clear_repositories()
    try:
        exit_code, output = run_scenario(SCENARIO, DEFAULT_OUTPUT, client, monkeypatch)

        assert exit_code == 0, output
        assert "0 failure(s)" in output
    finally:
        clear_repositories()
