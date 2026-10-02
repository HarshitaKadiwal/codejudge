from judge.judge import evaluate_python_code_multiple


def test_evaluate_accept():
    code = 'print(int(input()) + int(input()))'
    test_cases = [
        {'input_data': '2\n3\n', 'expected_output': '5'}
    ]
    result = evaluate_python_code_multiple(code, test_cases)
    assert result['verdict'] == 'Accepted'


def test_evaluate_wrong_answer():
    code = 'print(1)'
    test_cases = [
        {'input_data': '', 'expected_output': '2'}
    ]
    result = evaluate_python_code_multiple(code, test_cases)
    assert result['verdict'] in ('Wrong Answer', 'Runtime Error')


def test_runtime_error_does_not_expose_traceback():
    result = evaluate_python_code_multiple(
        "raise RuntimeError('private detail')",
        [{'input_data': '', 'expected_output': 'unused'}],
    )

    assert result['verdict'] == 'Runtime Error'
    assert result['actual_output'] == 'Program exited with a runtime error.'
    assert 'private detail' not in result['actual_output']


def test_submitted_code_does_not_inherit_application_secrets(monkeypatch):
    monkeypatch.setenv('DB_PASSWORD', 'application-secret')
    result = evaluate_python_code_multiple(
        "import os; print('DB_PASSWORD' in os.environ)",
        [{'input_data': '', 'expected_output': 'False'}],
    )

    assert result['verdict'] == 'Accepted'
