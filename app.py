from flask import Flask, render_template, request, redirect, url_for, session, flash
from database.db import get_connection
from judge.judge import evaluate_python_code_multiple

app = Flask(__name__)
app.secret_key = 'codejudge_secret_key'
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/health')
def health():
    return "CodeJudge app is running successfully!"

# ---------------- REGISTER ----------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "INSERT INTO users (username, password) VALUES (%s, %s)",
                (username, password)
            )
            conn.commit()
            flash('User registered successfully! Please log in.', 'success')
            return redirect(url_for('login'))

        except Exception:
            flash('Username already exists!', 'error')
            return redirect(url_for('register'))

        finally:
            cursor.close()
            conn.close()

    return render_template('register.html')

# ---------------- LOGIN ----------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM users WHERE username=%s AND password=%s",
            (username, password)
        )

        user = cursor.fetchone()

        cursor.close()
        conn.close()

        if user:
            session['username'] = username
            flash(f'Welcome, {username}!', 'success')
            return redirect(url_for('problems'))
        else:
            flash('Invalid credentials!', 'error')
            return redirect(url_for('login'))

    return render_template('login.html')

# ---------------- PROBLEMS LIST ----------------
@app.route('/problems')
def problems():
    if 'username' not in session:
        flash('Please log in first.', 'error')
        return redirect(url_for('login'))

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM problems")
    all_problems = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('problems.html', problems=all_problems, username=session['username'])

# ---------------- SINGLE PROBLEM ----------------
@app.route('/problem/<int:problem_id>')
def problem_detail(problem_id):
    if 'username' not in session:
        flash('Please log in first.', 'error')
        return redirect(url_for('login'))

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM problems WHERE id = %s", (problem_id,))
    problem = cursor.fetchone()

    cursor.close()
    conn.close()

    if problem:
        return render_template('problem_detail.html', problem=problem, username=session['username'])
    else:
        flash('Problem not found!', 'error')
        return redirect(url_for('problems'))

# ---------------- SUBMIT CODE ----------------
@app.route('/submit/<int:problem_id>', methods=['POST'])
def submit_code(problem_id):
    if 'username' not in session:
        flash('Please log in first.', 'error')
        return redirect(url_for('login'))

    username = session['username']
    code = request.form.get('code')

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM problems WHERE id = %s", (problem_id,))
    problem = cursor.fetchone()

    if not problem:
        cursor.close()
        conn.close()
        return "Problem not found!"

    cursor.execute(
        "SELECT input_data, expected_output FROM test_cases WHERE problem_id = %s",
        (problem_id,)
    )
    test_cases = cursor.fetchall()

    if not test_cases:
        cursor.close()
        conn.close()
        return "No test cases found for this problem!"

    evaluation = evaluate_python_code_multiple(code, test_cases)
    verdict = evaluation["verdict"]

    insert_cursor = conn.cursor()
    insert_cursor.execute(
        "INSERT INTO submissions (username, problem_id, code, verdict) VALUES (%s, %s, %s, %s)",
        (username, problem_id, code, verdict)
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
@app.route('/submissions')
def submissions():
    if 'username' not in session:
        flash('Please log in first.', 'error')
        return redirect(url_for('login'))

    username = session['username']

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT s.id, s.username, s.problem_id, p.title AS problem_title, s.verdict, s.submitted_at
        FROM submissions s
        JOIN problems p ON s.problem_id = p.id
        WHERE s.username = %s
        ORDER BY s.submitted_at DESC
    """
    cursor.execute(query, (username,))
    all_submissions = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'submissions.html',
        submissions=all_submissions,
        username=username
    )
@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)