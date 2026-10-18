import importlib.util
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from check_public import check
from package_public import package
from pdf_probe import probe

class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)/'public';self.root.mkdir()
        (self.root/'README.md').write_text('Synthetic public fixture.\n')
        self.manifest(['README.md'])

    def tearDown(self):self.temp.cleanup()

    def manifest(self, files):
        (self.root/'PUBLIC_MANIFEST.json').write_text(json.dumps({'files':files}))

    def test_allowlist_passes_and_extra_file_fails(self):
        self.assertEqual(check(self.root)['errors'],[])
        (self.root/'accidental.txt').write_text('Unexpected')
        self.assertTrue(any('Unexpected' in x for x in check(self.root)['errors']))

    def test_private_content_patterns(self):
        # Construct fake patterns without embedding real confidential identifiers.
        for value in ['/'+'Users'+'/'+'fictional-user', '123'+'X'*8+'45', '7'*12,
                      'fictional'+chr(64)+'example.org', 'sk-'+'a'*25]:
            with self.subTest(value=value):
                (self.root/'README.md').write_text(value)
                self.assertTrue(check(self.root)['errors'])

    def test_binary_source_even_if_allowlisted(self):
        (self.root/'statement.pdf').write_bytes(b'fake')
        self.manifest(['README.md','statement.pdf'])
        self.assertTrue(any('file type' in x for x in check(self.root)['errors']))

    def test_archive_cannot_contain_private_ignored_data(self):
        (self.root/'data').mkdir();(self.root/'data'/'confidential.txt').write_text('Private synthetic test marker')
        output=Path(self.temp.name)/'public.zip'
        package(output,self.root)
        with zipfile.ZipFile(output) as archive:
            self.assertEqual(set(archive.namelist()),{'spend-review/README.md','spend-review/PUBLIC_MANIFEST.json'})
            self.assertNotIn(b'Private synthetic test marker',b''.join(archive.read(x) for x in archive.namelist()))
        with self.assertRaises(ValueError):package(output,self.root)

    def test_manifest_cannot_escape(self):
        self.manifest(['../outside.txt'])
        self.assertTrue(any('Unsafe' in x for x in check(self.root)['errors']))

    def test_symlink_rejected(self):
        other=Path(self.temp.name)/'external.txt';other.write_text('Synthetic outside data')
        (self.root/'link.txt').symlink_to(other)
        self.manifest(['README.md','link.txt'])
        self.assertTrue(any('Symlink' in x or 'symlink' in x for x in check(self.root)['errors']))

class PdfPasswordTests(unittest.TestCase):
    def test_empty_password_first_and_any_candidate_count(self):
        calls=[]
        class Reader:
            is_encrypted=True
            def __init__(self,path):pass
            def decrypt(self,value):
                calls.append(value)
                return value=='synthetic-candidate-29'
        result=probe(['synthetic.pdf'],['synthetic-candidate-'+str(i) for i in range(30)],Reader)
        self.assertEqual(calls[0],'')
        self.assertEqual(result[0]['status'],'supplied candidate 30')
        self.assertNotIn('synthetic-candidate',str(result))

    def test_empty_password_is_not_misreported_as_locked(self):
        class Reader:
            is_encrypted=True
            def __init__(self,path):pass
            def decrypt(self,value):return value==''
        self.assertEqual(probe(['synthetic.pdf'],[],Reader)[0]['status'],'empty password')

if __name__=='__main__':unittest.main()
