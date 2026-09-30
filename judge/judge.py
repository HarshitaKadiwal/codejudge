import subprocess
import os
import uuid

def run_python_code(code, input_data):
    temp_filename = f"temp_{uuid.uuid4().hex}.py"

    try:
        with open(temp_filename, "w", encoding="utf-8") as f:
            f.write(code)

        result = subprocess.run(
            ["python", temp_filename],
            input=input_data,
            text=True,
            capture_output=True,
            timeout=5
        )

        if result.returncode != 0:
            return False, "Runtime Error", result.stderr.strip()

        return True, "Success", result.stdout.strip()

    except subprocess.TimeoutExpired:
        return False, "Time Limit Exceeded", "Code took too long to execute."

    except Exception as e:
        return False, "Error", str(e)

    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)


def evaluate_python_code_multiple(code, test_cases):
    """
    test_cases = [
        {'input_data': '2 3', 'expected_output': '5'},
        ...
    ]
    """

    results = []

    for index, test_case in enumerate(test_cases, start=1):
        input_data = test_case['input_data']
        expected_output = test_case['expected_output'].strip()

        success, status, actual_output = run_python_code(code, input_data)

        if not success:
            return {
                "verdict": status,
                "passed_count": index - 1,
                "total_count": len(test_cases),
                "failed_case": index,
                "input_data": input_data,
                "expected_output": expected_output,
                "actual_output": actual_output,
                "results": results
            }

        if actual_output.strip() != expected_output:
            return {
                "verdict": "Wrong Answer",
                "passed_count": index - 1,
                "total_count": len(test_cases),
                "failed_case": index,
                "input_data": input_data,
                "expected_output": expected_output,
                "actual_output": actual_output,
                "results": results
            }

        results.append({
            "case_number": index,
            "status": "Passed"
        })

    return {
        "verdict": "Accepted",
        "passed_count": len(test_cases),
        "total_count": len(test_cases),
        "failed_case": None,
        "input_data": None,
        "expected_output": None,
        "actual_output": None,
        "results": results
    }