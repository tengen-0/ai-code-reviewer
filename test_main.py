from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def payload(diff: str):
    return {
        "repo_url": "https://github.com/example/repo",
        "pr_number": 42,
        "author": "octocat",
        "diff": diff,
    }


def test_health_reports_heuristic_provider():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "provider": "heuristic"}


def test_review_detects_hardcoded_secret():
    response = client.post("/review", json=payload("+++ b/config.py\n+API_KEY = 'this-is-a-long-secret-value'\n"))
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["provider"] == "heuristic"
    assert body["findings"][0]["rule_id"] == "secret-api-key"
    assert body["findings"][0]["severity"] == "critical"
    assert body["findings"][0]["line"] == 1


def test_review_detects_unsafe_eval():
    response = client.post("/review", json=payload("+++ b/app.py\n+result = eval(user_input)\n"))
    assert response.status_code == 200
    body = response.json()
    assert body["comments_count"] == 1
    assert body["findings"][0]["rule_id"] == "python-eval"
    assert body["findings"][0]["suggestion"]


def test_review_with_clean_diff_has_no_findings():
    response = client.post("/review", json=payload("+++ b/app.py\n+return sum(values)\n"))
    assert response.status_code == 200
    assert response.json()["findings"] == []
