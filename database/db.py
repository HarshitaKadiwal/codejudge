import os
import mysql.connector
from mysql.connector import Error


def get_connection():
    """Create a MySQL connection using environment variables.

    Environment variables used:
    - DB_HOST
    - DB_USER
    - DB_PASSWORD
    - DB_NAME
    - DB_PORT
    """
    db_host = os.environ.get("DB_HOST", "localhost")
    db_user = os.environ.get("DB_USER", "root")
    db_password = os.environ.get("DB_PASSWORD", "")
    db_name = os.environ.get("DB_NAME", "codejudge")
    db_port = int(os.environ.get("DB_PORT", 3306))

    try:
        conn = mysql.connector.connect(
            host=db_host,
            user=db_user,
            password=db_password,
            database=db_name,
            port=db_port
        )
        return conn
    except Error:
        raise