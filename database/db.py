import os
import logging
import time
import mysql.connector

logger = logging.getLogger(__name__)

_TRANSIENT_CONNECTION_ERRORS = {2002, 2003, 2006, 2013, 2055}


_TABLE_STATEMENTS = (
    """CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(80) NOT NULL UNIQUE,
        password VARCHAR(255) NOT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",

    """CREATE TABLE IF NOT EXISTS problems (
        id INT AUTO_INCREMENT PRIMARY KEY,
        title VARCHAR(255) NOT NULL,
        description TEXT NOT NULL,
        sample_input TEXT,
        sample_output TEXT
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",

    """CREATE TABLE IF NOT EXISTS test_cases (
        id INT AUTO_INCREMENT PRIMARY KEY,
        problem_id INT NOT NULL,
        input_data TEXT NOT NULL,
        expected_output TEXT NOT NULL,
        INDEX idx_test_cases_problem_id (problem_id),
        CONSTRAINT fk_test_cases_problem
            FOREIGN KEY (problem_id) REFERENCES problems (id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",

    """CREATE TABLE IF NOT EXISTS submissions (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(80) NOT NULL,
        problem_id INT NOT NULL,
        code LONGTEXT NOT NULL,
        verdict VARCHAR(50) NOT NULL,
        submitted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_submissions_username_time (username, submitted_at),
        CONSTRAINT fk_submissions_user
            FOREIGN KEY (username) REFERENCES users (username),
        CONSTRAINT fk_submissions_problem
            FOREIGN KEY (problem_id) REFERENCES problems (id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
)


_SEED_PROBLEMS = (
    (
        1,
        "Add Two Numbers",
        "Write a program to read two integers and print their sum.",
        "2 3",
        "5",
    ),
    (
        2,
        "Multiply Two Numbers",
        "Write a program to read two integers and print their product.",
        "4 5",
        "20",
    ),
    (
        3,
        "Find Maximum",
        "Write a program to read two integers and print the greater number.",
        "7 2",
        "7",
    ),
)


_SEED_TEST_CASES = (
    (1, "2 3", "5"),
    (1, "10 20", "30"),
    (1, "0 0", "0"),
    (1, "-1 5", "4"),

    (2, "4 5", "20"),
    (2, "2 10", "20"),
    (2, "0 7", "0"),
    (2, "-2 3", "-6"),

    (3, "7 2", "7"),
    (3, "10 10", "10"),
    (3, "-1 -5", "-1"),
    (3, "0 8", "8"),
)


class ConfigurationError(ValueError):
    """Raised when required application configuration is missing or invalid."""


class DatabaseInitializationError(RuntimeError):
    """Raised when the configured database cannot be initialized safely."""


def _connect_with_retry(config):
    for attempt in range(3):
        try:
            return mysql.connector.connect(**config)
        except mysql.connector.Error as exc:
            if exc.errno not in _TRANSIENT_CONNECTION_ERRORS or attempt == 2:
                raise

            logger.warning(
                "Temporary MySQL connection failure; retrying (%d/3).",
                attempt + 1,
            )

            time.sleep(1)


def get_database_config():
    required = ("DB_HOST", "DB_USER", "DB_PASSWORD", "DB_NAME")

    missing = [
        name
        for name in required
        if not os.environ.get(name, "").strip()
    ]

    if missing:
        raise ConfigurationError(
            "Missing required database configuration: "
            + ", ".join(missing)
        )

    try:
        db_port = int(os.environ.get("DB_PORT", "3306"))
    except ValueError as exc:
        raise ConfigurationError(
            "DB_PORT must be a valid integer."
        ) from exc

    if not 1 <= db_port <= 65535:
        raise ConfigurationError(
            "DB_PORT must be between 1 and 65535."
        )

    return {
        "host": os.environ["DB_HOST"],
        "user": os.environ["DB_USER"],
        "password": os.environ["DB_PASSWORD"],
        "database": os.environ["DB_NAME"],
        "port": db_port,
    }


def get_connection():
    """Create a MySQL connection using explicitly configured credentials."""
    return _connect_with_retry(get_database_config())


def initialize_database():
    """Check the configured database and create missing tables without altering data."""

    config = get_database_config()

    server_config = {
        key: value
        for key, value in config.items()
        if key != "database"
    }

    try:
        server_connection = _connect_with_retry(server_config)

    except mysql.connector.Error as exc:
        raise DatabaseInitializationError(
            "Could not connect to MySQL while checking the configured database."
        ) from exc

    try:
        server_cursor = server_connection.cursor()

        try:
            server_cursor.execute(
                """
                SELECT SCHEMA_NAME
                FROM INFORMATION_SCHEMA.SCHEMATA
                WHERE SCHEMA_NAME = %s
                """,
                (config["database"],),
            )

            database_exists = (
                server_cursor.fetchone() is not None
            )

        finally:
            server_cursor.close()

    finally:
        server_connection.close()

    if not database_exists:
        raise DatabaseInitializationError(
            "The configured MySQL database does not exist: "
            + config["database"]
        )

    try:
        connection = _connect_with_retry(config)

        try:
            cursor = connection.cursor()

            try:
                for statement in _TABLE_STATEMENTS:
                    cursor.execute(statement)

                connection.commit()

            finally:
                cursor.close()

        finally:
            connection.close()

    except mysql.connector.Error as exc:
        raise DatabaseInitializationError(
            "Could not create or verify the required CodeJudge tables."
        ) from exc


def seed_database():
    """Insert the default CodeJudge problems and test cases if they are missing."""

    connection = get_connection()

    try:
        cursor = connection.cursor()

        try:
            cursor.execute("SELECT COUNT(*) FROM problems")
            problem_count = cursor.fetchone()[0]

            if problem_count == 0:

                cursor.executemany(
                    """
                    INSERT INTO problems
                        (id, title, description, sample_input, sample_output)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    _SEED_PROBLEMS,
                )

                cursor.executemany(
                    """
                    INSERT INTO test_cases
                        (problem_id, input_data, expected_output)
                    VALUES (%s, %s, %s)
                    """,
                    _SEED_TEST_CASES,
                )

                connection.commit()

                logger.info(
                    "Seeded default CodeJudge problems and test cases."
                )

        finally:
            cursor.close()

    finally:
        connection.close()