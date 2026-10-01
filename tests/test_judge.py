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
