#!/usr/bin/env python3
"""Check an allowlisted public export; no network calls and no automatic deletion."""
import argparse
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IGNORED_ROOTS = {'data', 'private', 'tmp', 'dist', '.git', '.venv'}
FORBIDDEN_EXTENSIONS = {'.pdf', '.xls', '.xlsx', '.png', '.jpg', '.jpeg', '.heic', '.bak', '.key', '.pem'}
PATTERNS = {
    'absolute home path': re.compile(r'/(?:Users|home)/[A-Za-z0-9_.-]+|[A-Z]:\\Users\\[^\\\s]+'),
    'masked financial identifier': re.compile(r'\d{3,}[Xx*]{3,}\d{2,}'),
    'long financial/identity number': re.compile(r'(?<![A-Za-z0-9])\d{10,19}(?![A-Za-z0-9])'),
    'private key material': re.compile(r'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----'),
    'credential-shaped token': re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{20,})\b'),
    'email address': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'),
}

def check(root=ROOT):
    root = Path(root)
    errors = []
    manifest = root / 'PUBLIC_MANIFEST.json'
    try:
        listed = json.loads(manifest.read_text())['files']
    except (OSError, ValueError, KeyError) as error:
        return {'errors': ['Public manifest missing or invalid: ' + str(error)], 'files': [], 'git_metadata_present': (root/'.git').exists()}
    allowed = set(listed) | {'PUBLIC_MANIFEST.json'}
    if len(listed) != len(set(listed)):
        errors.append('Duplicate allowlist path')
    for name in allowed:
        parts = Path(name).parts
        if Path(name).is_absolute() or '..' in parts or not parts or parts[0] in IGNORED_ROOTS:
            errors.append('Unsafe allowlist path: ' + name)
            continue
        path = root / name
        if not path.is_file():
            errors.append('Allowlisted file missing: ' + name)
            continue
        if any(p.is_symlink() for p in [path, *path.parents] if p == root or root in p.parents):
            errors.append('Symlinks are not allowed in release paths: ' + name)
            continue
        if path.suffix.lower() in FORBIDDEN_EXTENSIONS or path.name=='.DS_Store':
            errors.append('Private/binary file type prohibited: ' + name)
        try:
            text = path.read_text(encoding='utf-8')
        except (UnicodeError, OSError):
            errors.append('Public files must be inspectable UTF-8 text: ' + name)
            continue
        for label, pattern in PATTERNS.items():
            if pattern.search(name + '\n' + text):
                errors.append(label + ': ' + name)
        if path.suffix=='.csv' and not name.startswith('examples/synthetic/'):
            errors.append('Public CSV only permitted in explicitly synthetic example: ' + name)
    # Check all nonignored working files, not just files already selected for release.
    for directory, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = [name for name in dirs if name != '__pycache__' and not (Path(directory)==root and name in IGNORED_ROOTS)]
        for name in dirs + files:
            path = Path(directory) / name
            relative = path.relative_to(root)
            if path.is_symlink():
                errors.append('Unexpected symlink in project: ' + relative.as_posix())
            elif path.is_file() and relative.as_posix() not in allowed:
                errors.append('Unexpected public file; review before allowlisting: ' + relative.as_posix())
    return {'errors': sorted(set(errors)), 'files': sorted(allowed), 'git_metadata_present': (root/'.git').exists(),
            'notice': 'Heuristic content checks cannot certify anonymity. Git history, ignored data and external backups are not scanned or packaged.'}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    result = check(parser.parse_args().root)
    print(json.dumps(result, indent=2))
    return 1 if result['errors'] else 0

if __name__ == '__main__':
    raise SystemExit(main())
