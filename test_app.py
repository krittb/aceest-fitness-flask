"""
Pytest suite for the ACEest Fitness & Performance Flask application.

Run with:
    pytest -v
    pytest -v --cov=app --cov-report=term-missing
"""

import pytest
import app as app_module


@pytest.fixture
def client():
    """Provide a Flask test client with a clean in-memory member store
    for every test, so tests never leak state into one another."""
    app_module.app.config.update(TESTING=True)
    app_module.members.clear()
    with app_module.app.test_client() as test_client:
        yield test_client
    app_module.members.clear()


# ---------------------------------------------------------------------------
# Basic health / UI
# ---------------------------------------------------------------------------
def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_index_page_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"ACEest" in response.data


def test_get_programs(client):
    response = client.get("/api/programs")
    assert response.status_code == 200
    data = response.get_json()
    assert "Fat Loss" in data
    assert "Muscle Gain" in data
    assert "Beginner" in data
    assert data["Fat Loss"]["factor"] == 22


# ---------------------------------------------------------------------------
# Member creation
# ---------------------------------------------------------------------------
def test_add_member_success(client):
    payload = {"name": "Ravi", "age": 28, "weight": 70, "program": "Fat Loss"}
    response = client.post("/api/members", json=payload)
    assert response.status_code == 201
    data = response.get_json()
    assert data["name"] == "Ravi"
    assert data["calories"] == 70 * 22  # weight * program factor
    assert data["bmi"] is None  # height not supplied


def test_add_member_with_height_computes_bmi(client):
    payload = {"name": "Anita", "age": 30, "weight": 60, "height": 165, "program": "Beginner"}
    response = client.post("/api/members", json=payload)
    assert response.status_code == 201
    data = response.get_json()
    assert data["bmi"] == round(60 / (1.65 ** 2), 2)
    assert data["bmi_category"] in {"Underweight", "Normal weight", "Overweight", "Obese"}


def test_add_member_missing_required_fields(client):
    response = client.post("/api/members", json={"age": 25, "weight": 60})
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_add_member_invalid_program(client):
    payload = {"name": "Karthik", "age": 25, "weight": 65, "program": "Not A Program"}
    response = client.post("/api/members", json=payload)
    assert response.status_code == 400
    assert "Unknown program" in response.get_json()["error"]


@pytest.mark.parametrize("age,weight", [("abc", 70), (25, "heavy"), (-5, 70), (25, -10)])
def test_add_member_invalid_numeric_fields(client, age, weight):
    payload = {"name": "BadData", "age": age, "weight": weight, "program": "Fat Loss"}
    response = client.post("/api/members", json=payload)
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Member retrieval / listing / deletion
# ---------------------------------------------------------------------------
def test_list_members_empty(client):
    response = client.get("/api/members")
    assert response.status_code == 200
    assert response.get_json() == []


def test_get_member_success(client):
    client.post("/api/members", json={"name": "Divya", "age": 24, "weight": 55, "program": "Beginner"})
    response = client.get("/api/members/Divya")
    assert response.status_code == 200
    assert response.get_json()["name"] == "Divya"


def test_get_member_not_found(client):
    response = client.get("/api/members/Ghost")
    assert response.status_code == 404


def test_delete_member_success(client):
    client.post("/api/members", json={"name": "Suresh", "age": 40, "weight": 80, "program": "Muscle Gain"})
    response = client.delete("/api/members/Suresh")
    assert response.status_code == 200
    assert client.get("/api/members/Suresh").status_code == 404


def test_delete_member_not_found(client):
    response = client.delete("/api/members/Ghost")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Progress / adherence tracking
# ---------------------------------------------------------------------------
def test_log_progress_success(client):
    client.post("/api/members", json={"name": "Meera", "age": 22, "weight": 58, "program": "Fat Loss"})
    response = client.post("/api/members/Meera/progress", json={"adherence": 85})
    assert response.status_code == 200
    assert response.get_json()["adherence_log"] == [85]

    # A second entry should append, not overwrite
    client.post("/api/members/Meera/progress", json={"adherence": 90})
    final = client.get("/api/members/Meera").get_json()
    assert final["adherence_log"] == [85, 90]


def test_log_progress_member_not_found(client):
    response = client.post("/api/members/Ghost/progress", json={"adherence": 50})
    assert response.status_code == 404


@pytest.mark.parametrize("adherence", [-1, 101, "high", None])
def test_log_progress_invalid_value(client, adherence):
    client.post("/api/members", json={"name": "Kiran", "age": 29, "weight": 75, "program": "Muscle Gain"})
    response = client.post("/api/members/Kiran/progress", json={"adherence": adherence})
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Standalone BMI calculator
# ---------------------------------------------------------------------------
def test_bmi_endpoint_success(client):
    response = client.post("/api/bmi", json={"weight": 70, "height": 175})
    assert response.status_code == 200
    data = response.get_json()
    assert data["bmi"] == round(70 / (1.75 ** 2), 2)
    assert data["category"] == "Normal weight"


@pytest.mark.parametrize("weight,height", [(0, 170), (70, 0), ("x", 170), (70, "y")])
def test_bmi_endpoint_invalid_input(client, weight, height):
    response = client.post("/api/bmi", json={"weight": weight, "height": height})
    assert response.status_code == 400
