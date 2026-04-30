"""
Pytest configuration and fixtures for ACEest Fitness tests.
"""

import os
import pytest

from app import app as flask_app, init_db


@pytest.fixture
def app(tmp_path):
    """Create application for testing with a temp database."""
    db_path = str(tmp_path / "test_aceest.db")
    flask_app.config["TESTING"] = True
    flask_app.config["SECRET_KEY"] = "test-secret-key"
    os.environ["DB_NAME"] = db_path

    # Re-import to pick up new DB_NAME
    import app as app_module
    app_module.DB_NAME = db_path
    init_db()

    yield flask_app

    if os.path.exists(db_path):
        os.remove(db_path)


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
