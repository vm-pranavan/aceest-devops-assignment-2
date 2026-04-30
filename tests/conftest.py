"""
Pytest configuration and fixtures for ACEest Fitness tests.
"""

import os
import pytest

@pytest.fixture(scope="session", autouse=True)
def setup_test_env(tmp_path_factory):
    """Set up the test environment variables before anything is imported."""
    db_path = str(tmp_path_factory.mktemp("db") / "test_aceest.db")
    os.environ["DB_NAME"] = db_path
    os.environ["TESTING"] = "true"
    os.environ["SECRET_KEY"] = "test-secret-key"
    return db_path

@pytest.fixture
def app(setup_test_env):
    """Create application for testing with a temp database."""
    # We import app inside the fixture to ensure environment variables are already set
    import app as flask_app_module
    
    flask_app = flask_app_module.app
    flask_app.config["TESTING"] = True
    
    # Initialize the database
    flask_app_module.init_db()

    yield flask_app

    # Cleanup is handled by tmp_path_factory


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture
def logged_in_client(client):
    """A test client that is already logged in as admin."""
    client.post("/login", data={
        "username": "admin",
        "password": "admin"
    }, follow_redirects=True)
    return client
