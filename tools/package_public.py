#!/usr/bin/env python3
"""Build an allowlisted public ZIP, never a recursive archive of the working tree."""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path
from check_public import ROOT, check

def package(output, root=ROOT):
    root, output = Path(root), Path(output)
    result = check(root)
    if result['errors']:
        raise ValueError('Public check failed: ' + '; '.join(result['errors']))
    if output.resolve().is_relative_to(root.resolve()) and output.resolve().parent != (root/'dist').resolve():
        raise ValueError('Inside this checkout, release archives must go directly in ignored dist/')
    if output.exists():
        raise ValueError('Refusing to overwrite an existing archive')
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for name in result['files']:
            path = root/name
            archive.writestr('spend-review/'+name, path.read_bytes())
    with zipfile.ZipFile(output) as archive:
        expected = {'spend-review/'+name for name in result['files']}
        if set(archive.namelist()) != expected or archive.testzip() is not None:
            raise ValueError('Archive integrity/member check failed')
    return {'archive': str(output), 'files': len(result['files']), 'sha256': hashlib.sha256(output.read_bytes()).hexdigest()}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'dist/spend-review-public.zip')
    try:
        print(json.dumps(package(parser.parse_args().output), indent=2));return 0
    except (ValueError, OSError) as error:
        print(str(error));return 1

if __name__=='__main__':
    raise SystemExit(main())
