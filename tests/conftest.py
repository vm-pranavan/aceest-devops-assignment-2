"""
Pytest configuration and fixtures for ACEest Fitness tests.
"""

import os
import pytest

@pytest.fixture(scope="session", autouse=True, name="setup_test_env")
def test_env(tmp_path_factory):
    """Set up the test environment variables before anything is imported."""
    db_path = str(tmp_path_factory.mktemp("db") / "test_aceest.db")
    os.environ["DB_NAME"] = db_path
    os.environ["TESTING"] = "true"
    os.environ["SECRET_KEY"] = "test-secret-key"
    return db_path

@pytest.fixture(name="app")
def flask_app(setup_test_env):
    """Create application for testing with a temp database."""
    # Import inside the fixture so env vars from setup_test_env are applied first.
    import app as flask_app_module  # pylint: disable=import-outside-toplevel

    os.environ["DB_NAME"] = setup_test_env
    flask_app_instance = flask_app_module.app
    flask_app_instance.config["TESTING"] = True

    # Initialize the database
    flask_app_module.init_db()

    yield flask_app_instance

    # Cleanup is handled by tmp_path_factory


@pytest.fixture(name="client")
def test_client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture(name="logged_in_client")
def logged_in_client_fixture(client):
    """A test client that is already logged in as admin."""
    client.post("/login", data={
        "username": "admin",
        "password": "admin"
    }, follow_redirects=True)
    return client
