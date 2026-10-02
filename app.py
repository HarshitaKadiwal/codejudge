import logging
import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
import bcrypt
from dotenv import load_dotenv
from mysql.connector import Error as MySQLConnectorError, IntegrityError as MySQLIntegrityError
from werkzeug.exceptions import HTTPException

load_dotenv()

from database.db import (
    ConfigurationError,
    DatabaseInitializationError,
    get_connection,
    get_database_config,
    initialize_database,
    seed_database,
)

from judge.judge import evaluate_python_code_multiple


app = Flask(__name__)

app.config.update(
    SECRET_KEY=os.environ.get('FLASK_SECRET_KEY'),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=os.environ.get('SESSION_COOKIE_SECURE', 'false').lower() == 'true',
)

MAX_SUBMISSION_BYTES = 100_000

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)

logger = logging.getLogger(__name__)


def validate_configuration():
    if not app.secret_key:
        raise ConfigurationError(
            "Missing required application configuration: FLASK_SECRET_KEY"
        )

    get_database_config()


@app.errorhandler(ConfigurationError)
def handle_configuration_error(error):
    logger.error(
        "Application configuration is incomplete: %s",
        error
    )
    return "Application configuration is incomplete.", 503


@app.errorhandler(MySQLConnectorError)
def handle_database_error(error):
    logger.exception("A database operation failed.")
    return "Database service is temporarily unavailable.", 503


@app.errorhandler(Exception)
def handle_unexpected_error(error):
    if isinstance(error, HTTPException):
        return error

    logger.exception("An unexpected application error occurred.")
    return "An unexpected error occurred.", 500


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/health')
def health():
    try:
        connection = get_connection()

        try:
            cursor = connection.cursor()

            try:
                cursor.execute("SELECT 1")
                cursor.fetchone()  # Consume the result
            finally:
                cursor.close()

        finally:
            connection.close()

    except (ConfigurationError, MySQLConnectorError) as error:
        logger.exception("Health check failed: %s", error)
        return "CodeJudge database is unavailable.", 503

    return "CodeJudge app is running successfully!"


# ---------------- REGISTER ----------------

@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':

        username = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''

        if (
            not username
            or len(username) > 80
            or len(password) < 8
            or len(password.encode('utf-8')) > 72
        ):
            flash(
                'Use a username up to 80 characters and a password of 8 to 72 bytes.',
                'error'
            )
            return redirect(url_for('register'))

        conn = get_connection()
        cursor = conn.cursor()

        try:
            # Hash password before storing
            hashed = bcrypt.hashpw(
                password.encode('utf-8'),
                bcrypt.gensalt()
            )

            cursor.execute(
                "INSERT INTO users (username, password) VALUES (%s, %s)",
                (username, hashed.decode('utf-8'))
            )

            conn.commit()

            flash(
                'User registered successfully! Please log in.',
                'success'
            )

            return redirect(url_for('login'))

        except MySQLIntegrityError:
            flash(
                'Username already exists!',
                'error'
            )
            return redirect(url_for('register'))

        finally:
            cursor.close()
            conn.close()

    return render_template('register.html')


# ---------------- LOGIN ----------------

@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        username = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''

        if (
            not username
            or len(username) > 80
            or len(password.encode('utf-8')) > 72
        ):
            flash(
                'Invalid credentials!',
                'error'
            )
            return redirect(url_for('login'))

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM users WHERE username=%s",
            (username,)
        )

        user = cursor.fetchone()

        cursor.close()
        conn.close()

        # Verify hashed password
        if (
            user
            and bcrypt.checkpw(
                password.encode('utf-8'),
                user.get('password').encode('utf-8')
            )
        ):

            session.clear()
            session['username'] = username

            logger.info(
                'User %s logged in',
                username
            )

            flash(
                f'Welcome, {username}!',
                'success'
            )

            return redirect(url_for('problems'))

        else:

            logger.warning(
                'Failed login attempt for %s',
                username
            )

            flash(
                'Invalid credentials!',
                'error'
            )

            return redirect(url_for('login'))

    return render_template('login.html')


# ---------------- PROBLEMS LIST ----------------

@app.route('/problems')
def problems():

    if 'username' not in session:
        flash(
            'Please log in first.',
            'error'
        )
        return redirect(url_for('login'))

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM problems"
    )

    all_problems = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'problems.html',
        problems=all_problems,
        username=session['username']
    )


# ---------------- SINGLE PROBLEM ----------------

@app.route('/problem/<int:problem_id>')
def problem_detail(problem_id):

    if 'username' not in session:
        flash(
            'Please log in first.',
            'error'
        )
        return redirect(url_for('login'))

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM problems WHERE id = %s",
        (problem_id,)
    )

    problem = cursor.fetchone()

    cursor.close()
    conn.close()

    if problem:

        return render_template(
            'problem_detail.html',
            problem=problem,
            username=session['username']
        )

    else:

        flash(
            'Problem not found!',
            'error'
        )

        return redirect(url_for('problems'))


# ---------------- SUBMIT CODE ----------------

@app.route('/submit/<int:problem_id>', methods=['POST'])
def submit_code(problem_id):

    if 'username' not in session:
        flash(
            'Please log in first.',
            'error'
        )
        return redirect(url_for('login'))

    username = session['username']
    code = request.form.get('code') or ''

    if (
        not code.strip()
        or len(code.encode('utf-8')) > MAX_SUBMISSION_BYTES
    ):

        flash(
            'Submit non-empty code smaller than 100 KB.',
            'error'
        )

        return redirect(
            url_for(
                'problem_detail',
                problem_id=problem_id
            )
        )

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM problems WHERE id = %s",
        (problem_id,)
    )

    problem = cursor.fetchone()

    if not problem:

        cursor.close()
        conn.close()

        return "Problem not found!"

    cursor.execute(
        """
        SELECT input_data, expected_output
        FROM test_cases
        WHERE problem_id = %s
        """,
        (problem_id,)
    )

    test_cases = cursor.fetchall()

    if not test_cases:

        cursor.close()
        conn.close()

        return "No test cases found for this problem!"

    evaluation = evaluate_python_code_multiple(
        code,
        test_cases
    )

    verdict = evaluation["verdict"]

    logger.info(
        "Submission evaluated user=%s problem_id=%d verdict=%s passed=%d/%d",
        username,
        problem_id,
        verdict,
        evaluation["passed_count"],
        evaluation["total_count"],
    )

    insert_cursor = conn.cursor()

    insert_cursor.execute(
        """
        INSERT INTO submissions
        (username, problem_id, code, verdict)
        VALUES (%s, %s, %s, %s)
        """,
        (
            username,
            problem_id,
            code,
            verdict
        )
    )

    conn.commit()

    insert_cursor.close()
    cursor.close()
    conn.close()

    return render_template(
        'result.html',
        verdict=evaluation["verdict"],
        passed_count=evaluation["passed_count"],
        total_count=evaluation["total_count"],
        failed_case=evaluation["failed_case"],
        actual_output=evaluation["actual_output"],
        expected_output=evaluation["expected_output"],
        input_data=evaluation["input_data"],
        username=username,
        problem=problem
    )


# ---------------- SUBMISSIONS ----------------

@app.route('/submissions')
def submissions():

    if 'username' not in session:
        flash(
            'Please log in first.',
            'error'
        )
        return redirect(url_for('login'))

    username = session['username']

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT
            s.id,
            s.username,
            s.problem_id,
            p.title AS problem_title,
            s.verdict,
            s.submitted_at
        FROM submissions s
        JOIN problems p ON s.problem_id = p.id
        WHERE s.username = %s
        ORDER BY s.submitted_at DESC
    """

    cursor.execute(
        query,
        (username,)
    )

    all_submissions = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'submissions.html',
        submissions=all_submissions,
        username=username
    )


# ---------------- LOGOUT ----------------

@app.route('/logout')
def logout():

    session.clear()

    flash(
        'You have been logged out successfully.',
        'success'
    )

    return redirect(url_for('home'))


if __name__ == '__main__':

    try:
        validate_configuration()
        initialize_database()
        seed_database()

    except (
        ConfigurationError,
        DatabaseInitializationError
    ) as exc:

        logger.error(
            "Application configuration error: %s",
            exc
        )

        raise SystemExit(1) from None

    logger.info(
        "Starting CodeJudge on port 5000."
    )

    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False
    )