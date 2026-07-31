import ast, os, sys
from pathlib import Path

bad_imports = []
for path in Path('c:/Users/Hemasri/OneDrive/Desktop/pipeline-failure-detection-/backend').rglob('*.py'):
    if 'venv' in str(path) or '__pycache__' in str(path): continue
    try:
        tree = ast.parse(path.read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split('.')[0] in ['models', 'agents', 'services', 'retrieval', 'utils', 'pipeline', 'parser', 'collector', 'tools']:
                        bad_imports.append((str(path), alias.name))
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.level == 0 and node.module.split('.')[0] in ['models', 'agents', 'services', 'retrieval', 'utils', 'pipeline', 'parser', 'collector', 'tools']:
                    bad_imports.append((str(path), node.module))
    except Exception as e:
        pass

for path, mod in bad_imports:
    print(f'{path}: {mod}')

