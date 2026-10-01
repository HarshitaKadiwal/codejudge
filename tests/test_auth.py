import pytest
from unittest.mock import patch, MagicMock
import bcrypt

from app import app


@patch('app.get_connection')
def test_register_and_login(mock_get_conn):
    # Mock DB connection and cursor
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_get_conn.return_value = mock_conn

    client = app.test_client()

    # Register new user
    response = client.post('/register', data={'username': 'testuser', 'password': 'pass123'}, follow_redirects=True)
    assert response.status_code == 200

    # Simulate fetching user for login with stored hashed password
    stored_hash = bcrypt.hashpw('pass123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    mock_cursor.fetchone.return_value = {'id': 1, 'username': 'testuser', 'password': stored_hash}

    response = client.post('/login', data={'username': 'testuser', 'password': 'pass123'}, follow_redirects=True)
    assert response.status_code in (200, 302)
