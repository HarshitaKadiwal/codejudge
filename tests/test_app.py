import pytest
from unittest.mock import MagicMock, patch
from mysql.connector import Error as MySQLConnectorError, OperationalError

from app import app, validate_configuration
from database.db import (
    ConfigurationError,
    DatabaseInitializationError,
    get_database_config,
    get_connection,
    initialize_database,
)


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setitem(app.config, 'SECRET_KEY', 'test-only-secret')
    return app.test_client()


@patch('app.get_connection')
def test_health(mock_get_connection, client):
    connection = MagicMock()
    mock_get_connection.return_value = connection

    response = client.get('/health')

    assert response.status_code == 200
    assert response.data.decode() == "CodeJudge app is running successfully!"
    connection.cursor.return_value.execute.assert_called_once_with('SELECT 1')


@patch('app.get_connection', side_effect=ConfigurationError('DB_PASSWORD missing'))
def test_health_reports_database_unavailable(mock_get_connection, client):
    response = client.get('/health')

    assert response.status_code == 503
    assert response.data.decode() == 'CodeJudge database is unavailable.'
    assert b'DB_PASSWORD' not in response.data
    mock_get_connection.assert_called_once()


@patch('app.get_connection', side_effect=MySQLConnectorError('private database detail'))
def test_database_failure_returns_generic_error(mock_get_connection, client):
    with client.session_transaction() as user_session:
        user_session['username'] = 'alice'

    response = client.get('/problems')

    assert response.status_code == 503
    assert response.data == b'Database service is temporarily unavailable.'
    assert b'private database detail' not in response.data
    mock_get_connection.assert_called_once()


def test_home(client):
    response = client.get('/')
    assert response.status_code == 200


def test_protected_pages_redirect_to_login(client):
    for path in ('/problems', '/problem/1', '/submissions'):
        response = client.get(path)
        assert response.status_code == 302
        assert response.location.endswith('/login')

    response = client.post('/submit/1', data={'code': 'print(1)'})
    assert response.status_code == 302
    assert response.location.endswith('/login')


@patch('app.get_connection')
def test_problem_listing(mock_get_connection, client):
    connection = MagicMock()
    cursor = connection.cursor.return_value
    cursor.fetchall.return_value = [
        {'id': 1, 'title': 'Add numbers', 'description': 'Add two numbers.'}
    ]
    mock_get_connection.return_value = connection
    with client.session_transaction() as user_session:
        user_session['username'] = 'alice'

    response = client.get('/problems')

    assert response.status_code == 200
    assert b'Add numbers' in response.data
    cursor.execute.assert_called_once_with('SELECT * FROM problems')


def test_database_config_requires_credentials(monkeypatch):
    for name in ('DB_HOST', 'DB_USER', 'DB_PASSWORD', 'DB_NAME'):
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(ConfigurationError, match='Missing required database configuration'):
        get_database_config()


def test_application_requires_flask_secret(monkeypatch):
    monkeypatch.setitem(app.config, 'SECRET_KEY', None)

    with pytest.raises(ConfigurationError, match='FLASK_SECRET_KEY'):
        validate_configuration()


def test_database_connection_retries_transient_failure(monkeypatch):
    monkeypatch.setenv('DB_HOST', 'mysql')
    monkeypatch.setenv('DB_USER', 'codejudge')
    monkeypatch.setenv('DB_PASSWORD', 'test-password')
    monkeypatch.setenv('DB_NAME', 'codejudge')
    connection = MagicMock()

    with patch('database.db.mysql.connector.connect') as connect:
        with patch('database.db.time.sleep') as sleep:
            connect.side_effect = [
                OperationalError(errno=2003, msg='temporary connection failure'),
                connection,
            ]

            assert get_connection() is connection

    assert connect.call_count == 2
    sleep.assert_called_once_with(1)


def test_database_connection_does_not_retry_authentication_failure(monkeypatch):
    monkeypatch.setenv('DB_HOST', 'mysql')
    monkeypatch.setenv('DB_USER', 'codejudge')
    monkeypatch.setenv('DB_PASSWORD', 'test-password')
    monkeypatch.setenv('DB_NAME', 'codejudge')

    with patch('database.db.mysql.connector.connect') as connect:
        with patch('database.db.time.sleep') as sleep:
            connect.side_effect = OperationalError(errno=1045, msg='access denied')

            with pytest.raises(OperationalError):
                get_connection()

    connect.assert_called_once()
    sleep.assert_not_called()


def test_initialize_database_creates_missing_tables_only(monkeypatch):
    monkeypatch.setenv('DB_HOST', 'mysql')
    monkeypatch.setenv('DB_USER', 'codejudge')
    monkeypatch.setenv('DB_PASSWORD', 'test-password')
    monkeypatch.setenv('DB_NAME', 'codejudge')

    server_connection = MagicMock()
    server_cursor = server_connection.cursor.return_value
    server_cursor.fetchone.return_value = ('codejudge',)
    database_connection = MagicMock()
    database_cursor = database_connection.cursor.return_value

    with patch(
        'database.db._connect_with_retry',
        side_effect=[server_connection, database_connection],
    ):
        initialize_database()

    statements = [call.args[0] for call in database_cursor.execute.call_args_list]
    assert len(statements) == 4
    assert all(statement.startswith('CREATE TABLE IF NOT EXISTS') for statement in statements)
    assert all('DROP ' not in statement and 'ALTER ' not in statement for statement in statements)
    database_connection.commit.assert_called_once()


def test_initialize_database_reports_missing_database(monkeypatch):
    monkeypatch.setenv('DB_HOST', 'mysql')
    monkeypatch.setenv('DB_USER', 'codejudge')
    monkeypatch.setenv('DB_PASSWORD', 'test-password')
    monkeypatch.setenv('DB_NAME', 'missing_db')

    server_connection = MagicMock()
    server_connection.cursor.return_value.fetchone.return_value = None

    with patch('database.db._connect_with_retry', return_value=server_connection) as connect:
        with pytest.raises(DatabaseInitializationError, match='missing_db'):
            initialize_database()

    connect.assert_called_once()


@pytest.mark.parametrize(
    ('code', 'expected_output', 'verdict'),
    [
        ('print(int(input()) + int(input()))', '5', 'Accepted'),
        ('print(0)', '5', 'Wrong Answer'),
    ],
)
@patch('app.get_connection')
def test_submission_verdict_is_stored(
    mock_get_connection, client, code, expected_output, verdict
):
    connection = MagicMock()
    cursor = connection.cursor.return_value
    cursor.fetchone.return_value = {
        'id': 1,
        'title': 'Add numbers',
        'description': 'Add two numbers.',
        'sample_input': '2 3',
        'sample_output': '5',
    }
    cursor.fetchall.return_value = [
        {'input_data': '2\n3\n', 'expected_output': expected_output}
    ]
    mock_get_connection.return_value = connection
    with client.session_transaction() as user_session:
        user_session['username'] = 'alice'

    response = client.post('/submit/1', data={'code': code})

    assert response.status_code == 200
    assert verdict.encode() in response.data
    insert_query, insert_parameters = cursor.execute.call_args.args
    assert insert_query.strip().startswith('INSERT INTO submissions')
    assert insert_parameters == ('alice', 1, code, verdict)
    connection.commit.assert_called_once()


@patch('app.get_connection')
def test_oversized_submission_is_rejected_before_database_access(mock_get_connection, client):
    with client.session_transaction() as user_session:
        user_session['username'] = 'alice'

    response = client.post('/submit/1', data={'code': 'x' * 100_001})

    assert response.status_code == 302
    assert response.location.endswith('/problem/1')
    mock_get_connection.assert_not_called()


@patch('app.get_connection')
def test_submission_history_is_scoped_to_logged_in_user(mock_get_connection, client):
    connection = MagicMock()
    cursor = connection.cursor.return_value
    cursor.fetchall.return_value = [
        {
            'id': 3,
            'problem_id': 1,
            'problem_title': 'Add numbers',
            'verdict': 'Accepted',
            'submitted_at': '2026-10-02 10:00:00',
        }
    ]
    mock_get_connection.return_value = connection
    with client.session_transaction() as user_session:
        user_session['username'] = 'alice'

    response = client.get('/submissions')

    assert response.status_code == 200
    assert b'Add numbers' in response.data
    assert b'Accepted' in response.data
    query, parameters = cursor.execute.call_args.args
    assert 'WHERE s.username = %s' in query
    assert parameters == ('alice',)
def test_seed_database_inserts_default_data_when_problems_table_is_empty():
    from database.db import seed_database

    mock_connection = MagicMock()
    mock_cursor = mock_connection.cursor.return_value

    mock_cursor.fetchone.return_value = (0,)

    with patch("database.db.get_connection", return_value=mock_connection):
        seed_database()

    assert mock_cursor.execute.call_count == 1
    assert mock_cursor.executemany.call_count == 2
    mock_connection.commit.assert_called_once()