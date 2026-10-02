from unittest.mock import MagicMock, patch
import bcrypt
from mysql.connector import Error as MySQLConnectorError, IntegrityError

from app import app


@patch('app.get_connection')
def test_registration_hashes_password_and_login_authenticates(mock_get_conn):
    app.config['SECRET_KEY'] = 'test-only-secret'

    connection = MagicMock()
    cursor = connection.cursor.return_value
    mock_get_conn.return_value = connection

    client = app.test_client()

    response = client.post(
        '/register',
        data={'username': 'testuser', 'password': 'strong-pass123'},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.location.endswith('/login')
    insert_query, insert_parameters = cursor.execute.call_args.args
    assert insert_query.startswith('INSERT INTO users')
    assert insert_parameters[0] == 'testuser'
    assert insert_parameters[1] != 'strong-pass123'
    assert bcrypt.checkpw(b'strong-pass123', insert_parameters[1].encode('utf-8'))
    connection.commit.assert_called_once()

    with client.session_transaction() as user_session:
        user_session['stale_value'] = 'must be cleared'

    cursor.fetchone.return_value = {
        'id': 1,
        'username': 'testuser',
        'password': insert_parameters[1],
    }
    response = client.post(
        '/login',
        data={'username': 'testuser', 'password': 'strong-pass123'},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.location.endswith('/problems')
    with client.session_transaction() as user_session:
        assert user_session['username'] == 'testuser'
        assert 'stale_value' not in user_session

    client.get('/logout')
    with client.session_transaction() as user_session:
        assert 'username' not in user_session
        assert 'stale_value' not in user_session


@patch('app.get_connection')
def test_invalid_login_does_not_authenticate(mock_get_conn):
    app.config['SECRET_KEY'] = 'test-only-secret'
    connection = MagicMock()
    connection.cursor.return_value.fetchone.return_value = None
    mock_get_conn.return_value = connection

    response = app.test_client().post(
        '/login',
        data={'username': 'unknown', 'password': 'wrong'},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b'Invalid credentials!' in response.data


@patch('app.get_connection')
def test_registration_database_failure_is_not_reported_as_duplicate(mock_get_conn):
    app.config['SECRET_KEY'] = 'test-only-secret'
    mock_get_conn.side_effect = MySQLConnectorError('private database detail')

    response = app.test_client().post(
        '/register',
        data={'username': 'testuser', 'password': 'strong-pass123'},
    )

    assert response.status_code == 503
    assert b'Database service is temporarily unavailable.' in response.data
    assert b'Username already exists!' not in response.data
    assert b'private database detail' not in response.data


@patch('app.get_connection')
def test_duplicate_username_reports_integrity_failure(mock_get_conn):
    app.config['SECRET_KEY'] = 'test-only-secret'
    connection = MagicMock()
    connection.cursor.return_value.execute.side_effect = IntegrityError('duplicate')
    mock_get_conn.return_value = connection

    response = app.test_client().post(
        '/register',
        data={'username': 'testuser', 'password': 'strong-pass123'},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b'Username already exists!' in response.data


@patch('app.get_connection')
def test_registration_rejects_short_password_before_database_access(mock_get_conn):
    app.config['SECRET_KEY'] = 'test-only-secret'

    response = app.test_client().post(
        '/register',
        data={'username': 'testuser', 'password': 'short'},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b'password of 8 to 72 bytes' in response.data
    mock_get_conn.assert_not_called()
