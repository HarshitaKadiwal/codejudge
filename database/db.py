import os
import mysql.connector

def get_connection():
    db_host = os.environ.get("DB_HOST", "localhost")

    return mysql.connector.connect(
        host=db_host,
        user="root",
        password="Harshita@3344",
        database="codejudge",
        port=3306
    )