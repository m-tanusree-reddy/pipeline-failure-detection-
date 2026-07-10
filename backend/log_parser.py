import os
import re
from pathlib import Path
from typing import Dict, Any, Tuple, List

# --- Precompiled Regular Expressions ---

# ANSI Escape sequences
ANSI_ESCAPE_RE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

# Noise Patterns
TIMESTAMP_RE = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?\s*')
SEP_RE = re.compile(r'^[=\-]{5,}$')
PROGBAR1_RE = re.compile(r'\[[=#\-\.]+\]\s*\d+%')
PROGBAR2_RE = re.compile(r'\d+%\s*\|[█]+\|')

# Priority list of errors
ERROR_PATTERNS = [
    # (Category, Exact Regex, Keyword/Heuristic string)
    ("ModuleNotFoundError", re.compile(r"ModuleNotFoundError:\s*(.*)"), "ModuleNotFoundError"),
    ("ModuleNotFoundError", re.compile(r"No module named\s*'(.*?)'"), "No module named"),
    
    ("ImportError", re.compile(r"ImportError:\s*(.*)"), "ImportError"),
    
    ("SyntaxError", re.compile(r"SyntaxError:\s*(.*)"), "SyntaxError"),
    
    ("AssertionError", re.compile(r"AssertionError:\s*(.*)"), "AssertionError"),
    ("AssertionError", re.compile(r"AssertionError$"), "AssertionError"),
    
    ("PermissionError", re.compile(r"PermissionError:\s*(.*)"), "PermissionError"),
    ("PermissionError", re.compile(r"Permission denied"), "Permission denied"),
    
    ("FileNotFoundError", re.compile(r"FileNotFoundError:\s*(.*)"), "FileNotFoundError"),
    ("FileNotFoundError", re.compile(r"No such file or directory"), "No such file or directory"),
    
    ("DependencyError", re.compile(r"DependencyError:\s*(.*)"), "DependencyError"),
    ("DependencyError", re.compile(r"npm ERR!"), "npm ERR!"),
    ("DependencyError", re.compile(r"pip.*error", re.IGNORECASE), "pip install failed"),
    
    ("ConfigurationError", re.compile(r"ConfigurationError:\s*(.*)"), "ConfigurationError"),
    ("ConfigurationError", re.compile(r"command not found"), "command not found"),
    
    ("QualityCheckFailure", re.compile(r"(.*failed \d+ check\(s\).*)"), "failed check"),
    
    ("WorkflowExecutionError", re.compile(r"(Workflow failed)"), "Workflow failed"),
    ("WorkflowExecutionError", re.compile(r"(Job failed)"), "Job failed"),
    ("WorkflowExecutionError", re.compile(r"(Step failed)"), "Step failed"),
    
    ("GitHubActionsError", re.compile(r"(Process completed with exit code \d+)"), "Process completed with exit code"),
    ("GitHubActionsError", re.compile(r"(The process\s*'.*?'\s*failed)"), "The process failed"),
    ("GitHubActionsError", re.compile(r"##\[error\](.*)"), "##[error]"),
    ("GitHubActionsError", re.compile(r"Error:\s*(.*)"), "Error:"),
    ("GitHubActionsError", re.compile(r"FAILED\s*(.*)"), "FAILED"),
    
    ("TimeoutError", re.compile(r"TimeoutError:\s*(.*)"), "TimeoutError"),
    ("TimeoutError", re.compile(r"timed out"), "timed out"),
    
    ("MemoryError", re.compile(r"MemoryError:\s*(.*)"), "MemoryError"),
    ("MemoryError", re.compile(r"out of memory"), "out of memory"),
]

def load_log(file_path: str) -> str:
    """Reads a UTF-8 text log file robustly handling BOM and bad characters."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Log file not found: {file_path}")
    if not path.is_file():
        raise IsADirectoryError(f"Path is a directory, not a file: {file_path}")
        
    try:
        with open(path, "r", encoding="utf-8-sig", errors="replace") as file:
            return file.read()
    except Exception as e:
        raise IOError(f"Error reading log file {file_path}: {e}")

def remove_ansi_escape_sequences(log_text: str) -> str:
    """Removes ANSI color escape sequences."""
    return ANSI_ESCAPE_RE.sub('', log_text)

def is_critical_line(line: str) -> bool:
    """Check if the line contains valuable error information that shouldn't be stripped."""
    line_lower = line.lower()
    markers = [
        "##[error]", "##[warning]", "##[notice]", "error:", "failed", "process completed with exit code",
        "exit code", "traceback", "exception"
    ]
    return any(marker in line_lower for marker in markers)

def remove_noise(log_text: str) -> str:
    """Removes unnecessary noise while strictly preserving critical lines."""
    cleaned_lines = []
    
    for line in log_text.splitlines():
        line = TIMESTAMP_RE.sub('', line).strip()
        
        if not line:
            continue
            
        if is_critical_line(line):
            cleaned_lines.append(line)
            continue
            
        # Noise heuristics
        lower_line = line.lower()
        
        # Git checkout/setup & Repository initialization
        if line.startswith('[command]/usr/bin/git') or 'git config' in lower_line or 'git checkout' in lower_line or 'git version' in lower_line or 'git submodule' in lower_line:
            continue
        if 'adding repository directory' in lower_line or 'temporarily overriding home' in lower_line or 'removing credentials config' in lower_line:
            continue
        if 'switched to a new branch' in lower_line or ('branch' in lower_line and 'set up to track' in lower_line):
            continue
            
        # Runner version & OS information
        if 'runner version:' in lower_line or 'worker id:' in lower_line or 'azure region:' in lower_line or 'hosted compute agent' in lower_line:
            continue
        if line.startswith('Ubuntu') or line.startswith('LTS') or line.startswith('Version:') or line.startswith('Commit:') or line.startswith('Build Date:'):
            continue
        if line.startswith('Image:') or line.startswith('Included Software:') or line.startswith('Image Release:'):
            continue
            
        # Environment variables & Setup
        if line.startswith('env:') or line.startswith('shell:') or line.startswith('pythonLocation:') or line.startswith('PKG_CONFIG_PATH:') or line.startswith('Python_ROOT_DIR:'):
            continue
        if line.startswith('Python2_ROOT_DIR:') or line.startswith('Python3_ROOT_DIR:') or line.startswith('LD_LIBRARY_PATH:') or line.startswith('GITHUB_TOKEN'):
            continue
        if line.startswith('Contents:') or line.startswith('Metadata:') or line.startswith('PullRequests:') or line.startswith('with:') or line.startswith('python-version:'):
            continue
        if line.startswith('check-latest:') or line.startswith('token:') or line.startswith('update-environment:') or line.startswith('allow-prereleases:') or line.startswith('freethreaded:'):
            continue
        if line.startswith('Successfully set up'):
            continue
            
        # PR Description / Checklist
        if line.startswith('PR_') or line.startswith('AUTOCLOSE:') or line.startswith('PYTHONPATH:'):
            continue
        if line.startswith('- [ ]') or line.startswith('- [x]') or line.startswith('#### '):
            continue
            
        # Standard noise
        if line.startswith('##[group]') or line.startswith('##[endgroup]'):
            continue
        if line.startswith('Run ') or line.startswith('Complete job'):
            continue
        if 'download progress' in lower_line:
            continue
        if SEP_RE.match(line):
            continue
        if PROGBAR1_RE.search(line) or PROGBAR2_RE.search(line):
            continue
        if 'cleaning up orphan processes' in lower_line or 'post job cleanup' in lower_line:
            continue
        if 'removing includeif entries' in lower_line or 'removing http extra header' in lower_line or 'removing ssh command' in lower_line:
            continue
            
        cleaned_lines.append(line)
        
    return '\n'.join(cleaned_lines)

def detect_error_type(log_text: str) -> Tuple[str, int]:
    """
    Detects the type of error based on priority rules.
    Returns: (error_category, confidence)
    """
    for category, regex_pat, keyword in ERROR_PATTERNS:
        # Check exact regex first (High confidence)
        if regex_pat.search(log_text):
            return category, 95
            
        # Check keyword (Medium confidence)
        if keyword.lower() in log_text.lower():
            return category, 80
            
    # Fallback to generic keyword scanning if no priorities match
    if 'failed' in log_text.lower() or 'error' in log_text.lower():
        return "UnknownError", 40
        
    return "UnknownError", 0

def extract_error_block(log_text: str) -> str:
    """Dynamically extracts the error block by expanding around the primary failure."""
    lines = log_text.splitlines()
    error_indices = []
    
    for i, line in enumerate(lines):
        if is_critical_line(line):
            error_indices.append(i)
            
    if not error_indices:
        return '\n'.join(lines[-30:])

    primary_idx = error_indices[0]
    
    # Expand upwards (tightly, max 5 lines to keep context small)
    start_idx = primary_idx
    for i in range(primary_idx, max(-1, primary_idx - 5), -1):
        if i < 0:
            break
        line = lines[i]
        if line == '' and primary_idx - i >= 1:
            start_idx = i + 1
            break
        start_idx = i
        
    # Expand downwards (grab the whole stacktrace, up to ~25 lines, stopping early on logic breaks)
    end_idx = primary_idx
    for i in range(primary_idx, min(len(lines), primary_idx + 25)):
        line = lines[i]
        if line == '' and i - primary_idx > 1:
            end_idx = i - 1
            break
        end_idx = i

    return '\n'.join(lines[start_idx:end_idx+1])

def extract_error_message(log_text: str) -> str:
    """Extracts the most informative error messages, combining consecutive ones."""
    error_messages = []
    lines = log_text.splitlines()
    
    for line in lines:
        matched_msg = ""
        # 1. Check exact PR check failure
        if "failed" in line.lower() and "check(s)" in line.lower():
            matched_msg = line
        else:
            for category, regex_pat, keyword in ERROR_PATTERNS:
                match = regex_pat.search(line)
                if match:
                    if match.groups() and match.group(1).strip():
                        matched_msg = match.group(1).strip()
                    else:
                        matched_msg = line.strip()
                    break

        if matched_msg:
            clean_msg = matched_msg.replace('##[error]', '').strip()
            clean_msg = clean_msg.rstrip('.')
            if clean_msg and clean_msg not in error_messages:
                error_messages.append(clean_msg)
        elif "Exception:" in line or line.startswith("Error:"):
            clean_msg = line.replace('##[error]', '').strip().rstrip('.')
            if clean_msg and clean_msg not in error_messages:
                 error_messages.append(clean_msg)
                 
    if error_messages:
        return '. '.join(error_messages) + '.'
        
    # Fallback
    for line in lines:
        if is_critical_line(line):
             return line.replace('##[error]', '').strip()
             
    return ""

def parse_log(file_path: str) -> Dict[str, Any]:
    """Main pipeline to parse a log file and extract debugging information."""
    raw_log = load_log(file_path)
    no_ansi_log = remove_ansi_escape_sequences(raw_log)
    clean_log = remove_noise(no_ansi_log)
    
    error_type, confidence = detect_error_type(clean_log)
    error_block = extract_error_block(clean_log)
    error_message = extract_error_message(error_block)
    
    return {
        "file_name": Path(file_path).name,
        "error_type": error_type,
        "classification_confidence": confidence,
        "error_message": error_message,
        "error_context": error_block,
        "clean_log": clean_log,
        "status": "parsed"
    }

if __name__ == "__main__":
    try:
        log_file_input = input("Enter the path to a GitHub Actions log file: ").strip()
        if not log_file_input:
            print("No file path provided.")
        else:
            result = parse_log(log_file_input)
            print("\n" + "="*40)
            print("PARSED LOG RESULT")
            print("="*40)
            
            for key, value in result.items():
                print(f"\n[{key.upper()}]:")
                if isinstance(value, str) and '\n' in value:
                    print("-" * 20)
                    print(value)
                    print("-" * 20)
                else:
                    print(value)
                    
    except Exception as e:
        print(f"Failed to parse log: {e}")
