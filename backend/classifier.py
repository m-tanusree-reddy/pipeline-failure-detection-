"""
Error Classification Module for CI-Debug-Agent

This module receives parsed GitHub Actions log output and applies rule-based
logic to determine the exact failure category, calculate severity, and recommend
the best external tools for investigation.
"""

from typing import Dict, Any, List

def classify_error(parsed_log: Dict[str, Any]) -> str:
    """
    Determines the failure category from a parsed log dictionary.

    Args:
        parsed_log (Dict[str, Any]): The dictionary output from log_parser.py.

    Returns:
        str: A standardized failure category (e.g., 'ImportError', 'DependencyError').
    """
    error_type = parsed_log.get("error_type", "")
    
    # Standardize the error_type from log_parser to our requested classifier categories
    if error_type == "AssertionError":
        return "AssertionFailure"
        
    if error_type in ("ModuleNotFoundError", "ImportError"):
        return "ImportError"
        
    # Map GitHub Actions specific generic errors to WorkflowExecutionError
    if error_type == "GitHubActionsError":
        return "WorkflowExecutionError"
        
    valid_categories = {
        "DependencyError", "SyntaxError", "ConfigurationError",
        "QualityCheckFailure", "WorkflowExecutionError", "PermissionError",
        "TimeoutError", "MemoryError", "TestFailure"
    }
    
    if error_type in valid_categories:
        return error_type
        
    return "UnknownError"


def calculate_severity(category: str) -> str:
    """
    Calculates the severity of a failure category.

    Args:
        category (str): The classified error category.

    Returns:
        str: The severity level ('Critical', 'High', 'Medium', 'Low').
    """
    severity_mapping = {
        "MemoryError": "Critical",
        "SyntaxError": "High",
        "ImportError": "High",
        "DependencyError": "High",
        "PermissionError": "High",
        "ConfigurationError": "High",
        "TimeoutError": "Medium",
        "AssertionFailure": "Medium",
        "TestFailure": "Medium",
        "QualityCheckFailure": "Medium",
        "WorkflowExecutionError": "Medium",
        "UnknownError": "Low"
    }
    return severity_mapping.get(category, "Low")


def recommend_tools(category: str) -> List[str]:
    """
    Recommends investigation tools based on the failure category.

    Args:
        category (str): The classified error category.

    Returns:
        List[str]: A list of recommended tools (e.g., ['StackOverflow', 'GitHub Issues']).
    """
    tools_mapping = {
        "ImportError": ["GitHub Issues", "StackOverflow"],
        "DependencyError": ["PyPI", "StackOverflow", "GitHub Issues", "NPM Registry"],
        "SyntaxError": ["Python Documentation", "StackOverflow", "Linters"],
        "AssertionFailure": ["Source Code", "Git History", "Pytest Docs"],
        "TestFailure": ["Source Code", "Git History"],
        "ConfigurationError": ["GitHub Actions Docs", "StackOverflow", "Infrastructure as Code configs"],
        "QualityCheckFailure": ["Git History", "GitHub Issues", "Source Code", "SonarQube/Linters"],
        "WorkflowExecutionError": ["GitHub Actions Docs", "GitHub Issues", "Runner Environment Specs"],
        "PermissionError": ["OS Documentation", "GitHub Actions Docs", "StackOverflow"],
        "TimeoutError": ["GitHub Actions Docs", "Infrastructure Dashboards", "StackOverflow"],
        "MemoryError": ["StackOverflow", "GitHub Issues", "Memory Profilers"],
        "UnknownError": ["StackOverflow", "GitHub Issues", "Web Search"]
    }
    return tools_mapping.get(category, ["StackOverflow", "Web Search"])


def generate_classification(parsed_log: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main pipeline function that ingests a parsed log and returns a complete classification report.

    Args:
        parsed_log (Dict[str, Any]): The dictionary output from log_parser.py.

    Returns:
        Dict[str, Any]: A complete classification report including category, severity, tools, and reason.
    """
    category = classify_error(parsed_log)
    severity = calculate_severity(category)
    tools = recommend_tools(category)
    
    # Infer the reason dynamically based on the parsed message and assigned category
    error_message = parsed_log.get("error_message", "No specific error message found")
    confidence = parsed_log.get("classification_confidence", 50)
    
    reason = f"Classified as {category} with {confidence}% confidence due to log signature: '{error_message}'"
    
    return {
        "category": category,
        "severity": severity,
        "confidence": confidence,
        "recommended_tools": tools,
        "reason": reason,
        "status": "classified"
    }


if __name__ == "__main__":
    # Test suite for verification
    sample_logs = [
        {
            "error_type": "ModuleNotFoundError",
            "error_message": "No module named requests",
            "classification_confidence": 95,
            "status": "parsed"
        },
        {
            "error_type": "QualityCheckFailure",
            "error_message": "PR #21607 failed 1 check(s)",
            "classification_confidence": 90,
            "status": "parsed"
        },
        {
            "error_type": "DependencyError",
            "error_message": "npm ERR! code E404",
            "classification_confidence": 85,
            "status": "parsed"
        },
        {
            "error_type": "AssertionError",
            "error_message": "assert 4 == 5",
            "classification_confidence": 95,
            "status": "parsed"
        },
        {
            "error_type": "GitHubActionsError",
            "error_message": "Process completed with exit code 1",
            "classification_confidence": 75,
            "status": "parsed"
        },
        {
            "error_type": "SyntaxError",
            "error_message": "invalid syntax",
            "classification_confidence": 95,
            "status": "parsed"
        },
        {
            "error_type": "SomeWeirdCrash",
            "error_message": "Segfault at 0x000000",
            "classification_confidence": 0,
            "status": "parsed"
        }
    ]

    print("=" * 60)
    print("CLASSIFICATION RESULTS")
    print("=" * 60)
    for idx, log in enumerate(sample_logs, 1):
        classification = generate_classification(log)
        
        print(f"\nTest {idx}: {log['error_type']} -> {classification['category']}")
        print(f"  Severity: {classification['severity']}")
        print(f"  Tools:    {', '.join(classification['recommended_tools'])}")
        print(f"  Reason:   {classification['reason']}")
