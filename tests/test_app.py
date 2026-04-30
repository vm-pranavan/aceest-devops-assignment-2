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
