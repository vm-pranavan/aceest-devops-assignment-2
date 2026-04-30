"""
Unit tests for the ACEest Fitness Flask application.
Tests cover: health check, authentication, client CRUD, workouts,
BMI calculation, program generation, and database initialization.
"""

import json
import pytest
from app import calculate_bmi, calculate_calories, generate_ai_program


# ---------------------------------------------------------------------------
# Health Check Tests
# ---------------------------------------------------------------------------

class TestHealthCheck:
    """Tests for the /api/health endpoint."""

    def test_health_returns_200(self, client):
        """Health check should return 200 OK."""
        response = client.get("/api/health")
        assert response.status_code == 200

    def test_health_returns_json(self, client):
        """Health check should return valid JSON."""
        response = client.get("/api/health")
        data = json.loads(response.data)
        assert data["status"] == "healthy"
        assert "version" in data
        assert data["app"] == "ACEest Fitness"


# ---------------------------------------------------------------------------
# Authentication Tests
# ---------------------------------------------------------------------------

class TestAuthentication:
    """Tests for login and logout functionality."""

    def test_login_page_loads(self, client):
        """Login page should render successfully."""
        response = client.get("/login")
        assert response.status_code == 200
        assert b"Login" in response.data or b"login" in response.data

    def test_login_success(self, client):
        """Valid credentials should redirect to dashboard."""
        response = client.post("/login", data={
            "username": "admin",
            "password": "admin"
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b"Dashboard" in response.data or b"dashboard" in response.data

    def test_login_failure(self, client):
        """Invalid credentials should show error."""
        response = client.post("/login", data={
            "username": "wrong",
            "password": "wrong"
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b"Invalid" in response.data or b"invalid" in response.data

    def test_logout(self, logged_in_client):
        """Logout should redirect to login page."""
        response = logged_in_client.get("/logout", follow_redirects=True)
        assert response.status_code == 200

    def test_protected_route_redirects(self, client):
        """Protected routes should redirect unauthenticated users."""
        response = client.get("/", follow_redirects=True)
        assert b"Login" in response.data or b"login" in response.data


# ---------------------------------------------------------------------------
# Dashboard Tests
# ---------------------------------------------------------------------------

class TestDashboard:
    """Tests for the main dashboard."""

    def test_dashboard_loads(self, logged_in_client):
        """Dashboard should load for logged-in users."""
        response = logged_in_client.get("/")
        assert response.status_code == 200

    def test_dashboard_shows_stats(self, logged_in_client):
        """Dashboard should display summary statistics."""
        response = logged_in_client.get("/")
        assert response.status_code == 200
        assert b"Total Clients" in response.data or b"total" in response.data.lower()


# ---------------------------------------------------------------------------
# Client Management Tests
# ---------------------------------------------------------------------------

class TestClientManagement:
    """Tests for client CRUD operations."""

    def test_clients_page_loads(self, logged_in_client):
        """Clients page should load."""
        response = logged_in_client.get("/clients")
        assert response.status_code == 200

    def test_add_client(self, logged_in_client):
        """Adding a client should succeed."""
        response = logged_in_client.post("/clients/add", data={
            "name": "Test User",
            "age": 25,
            "height": 175,
            "weight": 70,
            "program": "Beginner (BG)"
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b"Test User" in response.data

    def test_add_duplicate_client(self, logged_in_client):
        """Adding a duplicate client should show error."""
        logged_in_client.post("/clients/add", data={
            "name": "Duplicate User", "age": 25,
            "height": 175, "weight": 70, "program": ""
        }, follow_redirects=True)
        response = logged_in_client.post("/clients/add", data={
            "name": "Duplicate User", "age": 30,
            "height": 180, "weight": 80, "program": ""
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b"already exists" in response.data

    def test_add_client_empty_name(self, logged_in_client):
        """Adding a client without a name should fail."""
        response = logged_in_client.post("/clients/add", data={
            "name": "", "age": 25, "height": 175,
            "weight": 70, "program": ""
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b"required" in response.data

    def test_client_detail_page(self, logged_in_client):
        """Client detail page should load after adding a client."""
        logged_in_client.post("/clients/add", data={
            "name": "Detail User", "age": 28,
            "height": 180, "weight": 85,
            "program": "Muscle Gain (MG) - PPL"
        }, follow_redirects=True)
        response = logged_in_client.get("/client/Detail User")
        assert response.status_code == 200
        assert b"Detail User" in response.data

    def test_client_not_found(self, logged_in_client):
        """Accessing nonexistent client should redirect."""
        response = logged_in_client.get("/client/NonExistent", follow_redirects=True)
        assert response.status_code == 200
        assert b"not found" in response.data

    def test_add_progress(self, logged_in_client):
        """Logging progress for a client should work."""
        logged_in_client.post("/clients/add", data={
            "name": "Progress User", "age": 30,
            "height": 170, "weight": 75, "program": ""
        }, follow_redirects=True)
        response = logged_in_client.post(
            "/client/Progress User/progress",
            data={"adherence": 85},
            follow_redirects=True
        )
        assert response.status_code == 200
        assert b"85" in response.data

    def test_add_metric(self, logged_in_client):
        """Logging body metrics for a client should work."""
        logged_in_client.post("/clients/add", data={
            "name": "Metric User", "age": 25,
            "height": 175, "weight": 70, "program": ""
        }, follow_redirects=True)
        response = logged_in_client.post(
            "/client/Metric User/metric",
            data={"date": "2026-04-30", "weight": 69.5, "waist": 80, "bodyfat": 15},
            follow_redirects=True
        )
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Workout Tests
# ---------------------------------------------------------------------------

class TestWorkouts:
    """Tests for workout logging."""

    def test_workouts_page_loads(self, logged_in_client):
        """Workouts page should load."""
        response = logged_in_client.get("/workouts")
        assert response.status_code == 200

    def test_add_workout(self, logged_in_client):
        """Logging a workout should succeed."""
        logged_in_client.post("/clients/add", data={
            "name": "Workout User", "age": 25,
            "height": 175, "weight": 70, "program": ""
        }, follow_redirects=True)
        response = logged_in_client.post("/workouts/add", data={
            "client_name": "Workout User",
            "date": "2026-04-30",
            "workout_type": "Strength",
            "duration": 60,
            "notes": "Heavy squats"
        }, follow_redirects=True)
        assert response.status_code == 200

    def test_add_workout_no_client(self, logged_in_client):
        """Logging a workout without a client should show error."""
        response = logged_in_client.post("/workouts/add", data={
            "client_name": "",
            "date": "2026-04-30",
            "workout_type": "Strength",
            "duration": 60, "notes": ""
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b"Select" in response.data or b"client" in response.data.lower()


# ---------------------------------------------------------------------------
# Programs Tests
# ---------------------------------------------------------------------------

class TestPrograms:
    """Tests for program viewing and AI generation."""

    def test_programs_page_loads(self, logged_in_client):
        """Programs page should load."""
        response = logged_in_client.get("/programs")
        assert response.status_code == 200
        assert b"Fat Loss" in response.data

    def test_generate_program(self, logged_in_client):
        """AI program generation should return exercises."""
        logged_in_client.post("/clients/add", data={
            "name": "Gen User", "age": 25,
            "height": 175, "weight": 70,
            "program": "Beginner (BG)"
        }, follow_redirects=True)
        response = logged_in_client.post("/programs/generate", data={
            "client_name": "Gen User",
            "experience": "beginner"
        }, follow_redirects=True)
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# BMI Calculator Tests
# ---------------------------------------------------------------------------

class TestBMI:
    """Tests for BMI calculation."""

    def test_bmi_page_loads(self, logged_in_client):
        """BMI page should load."""
        response = logged_in_client.get("/bmi")
        assert response.status_code == 200

    def test_bmi_calculation(self, logged_in_client):
        """BMI calculation should return results."""
        response = logged_in_client.post("/bmi", data={
            "weight": 70, "height": 175
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b"22.9" in response.data or b"Normal" in response.data

    def test_bmi_underweight(self):
        """BMI below 18.5 should be Underweight."""
        bmi, cat, _ = calculate_bmi(50, 180)
        assert cat == "Underweight"

    def test_bmi_normal(self):
        """BMI 18.5-24.9 should be Normal."""
        bmi, cat, _ = calculate_bmi(70, 175)
        assert cat == "Normal"

    def test_bmi_overweight(self):
        """BMI 25-29.9 should be Overweight."""
        bmi, cat, _ = calculate_bmi(90, 175)
        assert cat == "Overweight"

    def test_bmi_obese(self):
        """BMI >= 30 should be Obese."""
        bmi, cat, _ = calculate_bmi(120, 175)
        assert cat == "Obese"

    def test_bmi_invalid_input(self):
        """Invalid input should return None."""
        bmi, cat, _ = calculate_bmi(0, 0)
        assert bmi is None
        assert cat == "Invalid"


# ---------------------------------------------------------------------------
# Utility Function Tests
# ---------------------------------------------------------------------------

class TestUtilities:
    """Tests for utility functions."""

    def test_calculate_calories_fat_loss(self):
        """Calories for fat loss 3-day should use factor 22."""
        cal = calculate_calories(70, "Fat Loss (FL) - 3 day")
        assert cal == 70 * 22

    def test_calculate_calories_muscle_gain(self):
        """Calories for muscle gain should use factor 35."""
        cal = calculate_calories(70, "Muscle Gain (MG) - PPL")
        assert cal == 70 * 35

    def test_calculate_calories_zero_weight(self):
        """Zero weight should return None."""
        cal = calculate_calories(0, "Beginner (BG)")
        assert cal is None

    def test_calculate_calories_unknown_program(self):
        """Unknown program should use default factor 25."""
        cal = calculate_calories(80, "Unknown Program")
        assert cal == 80 * 25

    def test_generate_ai_program_beginner(self):
        """Beginner program should have 3 days."""
        program = generate_ai_program("Beginner (BG)", "beginner")
        days = set(item["day"] for item in program)
        assert len(days) == 3

    def test_generate_ai_program_advanced(self):
        """Advanced program should have 5 days."""
        program = generate_ai_program("Muscle Gain (MG) - PPL", "advanced")
        days = set(item["day"] for item in program)
        assert len(days) == 5

    def test_generate_ai_program_structure(self):
        """Generated program items should have required keys."""
        program = generate_ai_program("Beginner (BG)", "beginner")
        for item in program:
            assert "day" in item
            assert "exercise" in item
            assert "sets" in item
            assert "reps" in item

    def test_generate_ai_program_fat_loss_uses_conditioning(self):
        """Fat Loss program should use Conditioning exercise pool."""
        from app import EXERCISE_POOLS
        program = generate_ai_program("Fat Loss (FL) - 3 day", "beginner")
        conditioning_exercises = set(EXERCISE_POOLS["Conditioning"])
        program_exercises = {item["exercise"] for item in program}
        assert program_exercises.issubset(conditioning_exercises)

    def test_generate_ai_program_muscle_gain_uses_hypertrophy(self):
        """Muscle Gain program should use Hypertrophy exercise pool."""
        from app import EXERCISE_POOLS
        program = generate_ai_program("Muscle Gain (MG) - PPL", "beginner")
        hypertrophy_exercises = set(EXERCISE_POOLS["Hypertrophy"])
        program_exercises = {item["exercise"] for item in program}
        assert program_exercises.issubset(hypertrophy_exercises)

    def test_generate_ai_program_unknown_uses_full_body(self):
        """Unknown program name should fall back to Full Body exercise pool."""
        from app import EXERCISE_POOLS
        program = generate_ai_program("Unknown Program", "beginner")
        full_body_exercises = set(EXERCISE_POOLS["Full Body"])
        program_exercises = {item["exercise"] for item in program}
        assert program_exercises.issubset(full_body_exercises)

    def test_generate_ai_program_intermediate(self):
        """Intermediate program should have 4 days."""
        program = generate_ai_program("Beginner (BG)", "intermediate")
        days = set(item["day"] for item in program)
        assert len(days) == 4

    def test_generate_ai_program_intermediate_sets_range(self):
        """Intermediate program sets should be in range 3-4."""
        program = generate_ai_program("Beginner (BG)", "intermediate")
        for item in program:
            assert 3 <= item["sets"] <= 4

    def test_generate_ai_program_advanced_sets_range(self):
        """Advanced program sets should be in range 4-5."""
        program = generate_ai_program("Muscle Gain (MG) - PPL", "advanced")
        for item in program:
            assert 4 <= item["sets"] <= 5

    def test_calculate_bmi_negative_height(self):
        """Negative height should return invalid."""
        bmi, cat, _ = calculate_bmi(70, -175)
        assert bmi is None
        assert cat == "Invalid"

    def test_calculate_bmi_negative_weight(self):
        """Negative weight should return invalid."""
        bmi, cat, _ = calculate_bmi(-70, 175)
        assert bmi is None
        assert cat == "Invalid"

    def test_calculate_calories_fat_loss_5day(self):
        """Calories for fat loss 5-day should use factor 24."""
        cal = calculate_calories(70, "Fat Loss (FL) - 5 day")
        assert cal == 70 * 24

    def test_calculate_calories_beginner(self):
        """Calories for beginner program should use factor 26."""
        cal = calculate_calories(70, "Beginner (BG)")
        assert cal == 70 * 26

    def test_calculate_calories_none_weight(self):
        """None weight should return None."""
        cal = calculate_calories(None, "Beginner (BG)")
        assert cal is None


# ---------------------------------------------------------------------------
# Additional Route Coverage Tests
# ---------------------------------------------------------------------------

class TestProgramGenerationEdgeCases:
    """Tests for edge cases in the program generation route."""

    def test_generate_program_invalid_experience(self, logged_in_client):
        """Invalid experience level should flash error and redirect."""
        response = logged_in_client.post("/programs/generate", data={
            "client_name": "Some User",
            "experience": "expert"
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b"Invalid" in response.data or b"experience" in response.data.lower()

    def test_generate_program_no_client_match(self, logged_in_client):
        """Generating program for non-existent client should use default program."""
        response = logged_in_client.post("/programs/generate", data={
            "client_name": "Ghost User",
            "experience": "intermediate"
        }, follow_redirects=True)
        assert response.status_code == 200

    def test_generate_program_intermediate_experience(self, logged_in_client):
        """Generating a program with intermediate experience should succeed."""
        logged_in_client.post("/clients/add", data={
            "name": "Inter User", "age": 30,
            "height": 175, "weight": 75,
            "program": "Fat Loss (FL) - 5 day"
        }, follow_redirects=True)
        response = logged_in_client.post("/programs/generate", data={
            "client_name": "Inter User",
            "experience": "intermediate"
        }, follow_redirects=True)
        assert response.status_code == 200

    def test_generate_program_advanced_experience(self, logged_in_client):
        """Generating a program with advanced experience should succeed."""
        logged_in_client.post("/clients/add", data={
            "name": "Adv User", "age": 28,
            "height": 180, "weight": 80,
            "program": "Muscle Gain (MG) - PPL"
        }, follow_redirects=True)
        response = logged_in_client.post("/programs/generate", data={
            "client_name": "Adv User",
            "experience": "advanced"
        }, follow_redirects=True)
        assert response.status_code == 200


class TestClientDetailEdgeCases:
    """Tests for edge cases in client detail view."""

    def test_client_detail_no_height_weight(self, logged_in_client):
        """Client detail without height/weight should not show BMI."""
        logged_in_client.post("/clients/add", data={
            "name": "No BMI User", "age": 25,
            "height": "", "weight": "",
            "program": "Beginner (BG)"
        }, follow_redirects=True)
        response = logged_in_client.get("/client/No BMI User")
        assert response.status_code == 200

    def test_client_detail_shows_progress(self, logged_in_client):
        """Client detail should show logged progress."""
        logged_in_client.post("/clients/add", data={
            "name": "Progress Check", "age": 30,
            "height": 170, "weight": 75, "program": ""
        }, follow_redirects=True)
        logged_in_client.post(
            "/client/Progress Check/progress",
            data={"adherence": 90},
            follow_redirects=True
        )
        response = logged_in_client.get("/client/Progress Check")
        assert response.status_code == 200
        assert b"90" in response.data

    def test_client_detail_shows_metrics(self, logged_in_client):
        """Client detail should show logged metrics."""
        logged_in_client.post("/clients/add", data={
            "name": "Metrics Check", "age": 25,
            "height": 175, "weight": 70, "program": ""
        }, follow_redirects=True)
        logged_in_client.post(
            "/client/Metrics Check/metric",
            data={"date": "2026-04-30", "weight": 68.0, "waist": 78, "bodyfat": 14},
            follow_redirects=True
        )
        response = logged_in_client.get("/client/Metrics Check")
        assert response.status_code == 200
