import unittest
import os
import tempfile
from pathlib import Path
from backend.log_parser import parse_log

class TestLogParser(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for test logs
        self.test_dir = tempfile.TemporaryDirectory()
        self.test_dir_path = Path(self.test_dir.name)

    def tearDown(self):
        self.test_dir.cleanup()

    def create_log_file(self, filename: str, content: str) -> str:
        filepath = self.test_dir_path / filename
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return str(filepath)

    def test_module_not_found_error(self):
        content = """Run pytest
================ test session starts ================
Traceback (most recent call last):
  File "app.py", line 1, in <module>
    import numpy
ModuleNotFoundError: No module named 'numpy'
=====================================================
"""
        filepath = self.create_log_file("module_not_found.log", content)
        result = parse_log(filepath)
        
        self.assertEqual(result["status"], "parsed")
        self.assertEqual(result["error_type"], "ModuleNotFoundError")
        self.assertEqual(result["classification_confidence"], 95)
        self.assertIn("No module named 'numpy'", result["error_message"])

    def test_syntax_error(self):
        content = """Run pytest
================ test session starts ================
Traceback (most recent call last):
  File "app.py", line 10
    if True
          ^
SyntaxError: expected ':'
=====================================================
"""
        filepath = self.create_log_file("syntax_error.log", content)
        result = parse_log(filepath)
        
        self.assertEqual(result["error_type"], "SyntaxError")
        self.assertEqual(result["classification_confidence"], 95)
        self.assertIn("expected ':'", result["error_message"])

    def test_assertion_error(self):
        content = """Run pytest
================ test session starts ================
def test_calc():
>       assert 2 + 2 == 5
E       AssertionError: assert 4 == 5

tests/test_calc.py:2: AssertionError
=====================================================
"""
        filepath = self.create_log_file("assertion_error.log", content)
        result = parse_log(filepath)
        
        self.assertEqual(result["error_type"], "AssertionError")
        self.assertEqual(result["classification_confidence"], 95)
        self.assertIn("assert 4 == 5", result["error_message"])

    def test_quality_check_failure(self):
        content = """Run Quality Checks
##[notice]PR #21607 author has no commits
##[error]PR #21607 failed 1 check(s), adding comment with details.
##[error]Process completed with exit code 1.
Post job cleanup.
"""
        filepath = self.create_log_file("quality_check.log", content)
        result = parse_log(filepath)
        
        self.assertEqual(result["error_type"], "QualityCheckFailure")
        self.assertEqual(result["classification_confidence"], 95)
        # Check if it combines consecutive messages correctly
        self.assertIn("PR #21607 failed 1 check(s), adding comment with details", result["error_message"])
        self.assertIn("Process completed with exit code 1", result["error_message"])

    def test_workflow_execution_error(self):
        content = """##[group]Run action
##[endgroup]
Job failed due to infra issues.
Workflow failed.
"""
        filepath = self.create_log_file("workflow_error.log", content)
        result = parse_log(filepath)
        
        self.assertEqual(result["error_type"], "WorkflowExecutionError")
        self.assertEqual(result["classification_confidence"], 95)

    def test_dependency_failure(self):
        content = """Run npm install
npm ERR! code E404
npm ERR! 404 Not Found - GET https://registry.npmjs.org/non-existent-package
"""
        filepath = self.create_log_file("dependency.log", content)
        result = parse_log(filepath)
        
        self.assertEqual(result["error_type"], "DependencyError")
        self.assertEqual(result["classification_confidence"], 95)
        self.assertIn("code E404", result["error_message"])

    def test_unknown_error(self):
        content = """Starting build
Compiling everything...
Whoops something broke.
Error code -1
"""
        filepath = self.create_log_file("unknown_error.log", content)
        result = parse_log(filepath)
        
        self.assertEqual(result["error_type"], "UnknownError")
        self.assertEqual(result["classification_confidence"], 40) # Fallback to generic "error" presence

if __name__ == '__main__':
    unittest.main()
