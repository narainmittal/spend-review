#!/usr/bin/env python3
"""Test PDF accessibility with hidden, session-only password candidates."""
import argparse
import getpass
import sys
from pathlib import Path

def probe(paths, candidates, reader_factory):
    results = []
    for path in paths:
        success = None
        try:
            reader = reader_factory(str(path))
            if not reader.is_encrypted:
                success = 'no password required'
            else:
                # Empty password is attempted before any supplied candidate.
                for index, candidate in enumerate([''] + list(candidates)):
                    try:
                        if reader.decrypt(candidate):
                            success = 'empty password' if index == 0 else 'supplied candidate ' + str(index)
                            break
                    except Exception:
                        continue
        except Exception:
            pass
        results.append({'file': Path(path).name, 'status': success or 'not opened; unreadable or no matching candidate'})
    return results

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('files', type=Path, nargs='+')
    args = parser.parse_args()
    try:
        from pypdf import PdfReader
    except ImportError:
        print('Optional dependency missing. Install pypdf in a virtual environment.');return 1
    if not sys.stdin.isatty():
        print('A private interactive terminal is required; do not put passwords in arguments or pipe input.');return 1
    candidates = []
    try:
        while True:
            value = getpass.getpass('Password candidate (blank finishes; never saved): ')
            if not value:
                break
            candidates.append(value)
        result = probe(args.files, candidates, PdfReader)
        for row in result:
            print(row['file'] + ': ' + row['status'])
        return 1 if any(x['status'].startswith('not opened') for x in result) else 0
    finally:
        candidates.clear()  # Python cannot guarantee memory zeroization.

if __name__ == '__main__':
    raise SystemExit(main())
