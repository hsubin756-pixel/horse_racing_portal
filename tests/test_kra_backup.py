"""Offline archive checks. Fixture SQL is not a real database backup."""
import contextlib
import fcntl
import io
import json
import os
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import kra_backup as kb


class BackupTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.source=self.root/'source';self.source.mkdir()
        self.files={}
        for name,data in [('database/backup.sql.gz',b'fixture only'),
                          ('database/report.json',b'{"isolatedRestorePassed":true}'),
                          ('kra/sync/job.json','{"한글":"보류", "calls":602}'.encode()),
                          ('kra/results-abc/page-1.xml',b'<response/>')]:
            path=self.source/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
            self.files[name]=path
        self.archive=self.root/'bundle.tar.gz'
        kb.pack_bundle(self.archive,self.files,{'originalRoot':'/original/project'})

    def rewrite(self, change):
        target=self.root/'changed.tar.gz'
        with tarfile.open(self.archive,'r:gz') as source, tarfile.open(target,'w:gz') as out:
            for member in source.getmembers():
                data=source.extractfile(member).read()
                member,data=change(member,data)
                member.size=len(data);out.addfile(member,io.BytesIO(data))
        return target

    def test_verify_and_extract_roundtrip_without_overwriting_existing_files(self):
        target=self.root/'restore'
        with contextlib.redirect_stdout(io.StringIO()):kb.extract(self.archive,target)
        for name,path in self.files.items():
            self.assertEqual((target/name).read_bytes(),path.read_bytes())
            self.assertEqual((target/name).stat().st_mode & 0o777,0o600)
        before=(target/'kra/sync/job.json').read_bytes()
        with self.assertRaises(FileExistsError):kb.extract(self.archive,target)
        self.assertEqual((target/'kra/sync/job.json').read_bytes(),before)
        self.assertEqual(self.archive.stat().st_mode & 0o777,0o600)

    def test_tampered_bytes_fail_and_do_not_leave_extracted_files(self):
        target=self.root/'restore'
        changed=self.rewrite(lambda m,data:(m,b'X'*len(data) if m.name.endswith('.xml') else data))
        with self.assertRaises(kb.BackupError):kb.extract(changed,target)
        self.assertFalse(target.exists())

    def test_path_traversal_symlinks_and_duplicate_members_rejected(self):
        for mode in ('traversal','symlink','duplicate'):
            def change(member,data):
                if member.name.endswith('.xml'):
                    if mode=='traversal':member.name='../outside'
                    elif mode=='duplicate':member.name='kra/sync/job.json'
                    else:member.type=tarfile.SYMTYPE;member.linkname='/etc/passwd'
                return member,data
            with self.subTest(mode=mode),self.assertRaises(kb.BackupError):
                kb.inspect_bundle(self.rewrite(change))

    def test_credentials_and_locks_excluded_and_symlinks_refused(self):
        root=self.root/'kra';root.mkdir()
        for name in ('service-key','.env','sync.lock','page.xml'):(root/name).write_text(name)
        self.assertEqual(list(kb.kra_files(root)),['kra/page.xml'])
        (root/'linked.xml').symlink_to(root/'page.xml')
        with self.assertRaises(kb.BackupError):kb.kra_files(root)

    def test_missing_restore_report_and_false_verification_rejected(self):
        files=dict(self.files);files.pop('database/report.json')
        with self.assertRaises(kb.BackupError):kb.pack_bundle(self.root/'missing.tar.gz',files,{'originalRoot':'/x'})
        self.files['database/report.json'].write_text('{"isolatedRestorePassed":false}')
        with self.assertRaises(kb.BackupError):kb.pack_bundle(self.root/'false.tar.gz',self.files,{'originalRoot':'/x'})

    def test_active_sync_lock_prevents_database_backup(self):
        root=self.root/'repo';sync=root/'.runtime/kra/sync';sync.mkdir(parents=True)
        with (sync/'sync.lock').open('w') as lock, patch.object(kb,'ROOT',root),patch.object(kb.subprocess,'run') as run:
            fcntl.flock(lock,fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaises(kb.BackupError):kb.create(root/'.runtime/backups')
            run.assert_not_called()

    def test_output_inside_source_refused(self):
        root=self.root/'repo';(root/'.runtime/kra').mkdir(parents=True)
        with patch.object(kb,'ROOT',root),self.assertRaises(kb.BackupError):kb.create(root/'.runtime/kra/backups')

    def test_source_change_during_backup_cannot_publish_a_completed_archive(self):
        root=self.root/'repo';kra=root/'.runtime/kra';kra.mkdir(parents=True)
        source=kra/'page.xml';source.write_text('before')
        directory=root/'.runtime/backups'
        def run(command,**kwargs):
            if command[0]=='git':return SimpleNamespace(returncode=0,stdout='fixture-revision')
            staging=Path(command[-1]);dump=staging/'db.sql.gz';report=staging/'db.json'
            dump.write_bytes(b'fixture SQL');report.write_text('{"isolatedRestorePassed":true,"tables":{}}')
            source.write_text('changed during DB backup')
            return SimpleNamespace(stdout=json.dumps({'backup':str(dump),'report':str(report)}))
        with patch.object(kb,'ROOT',root),patch.object(kb.subprocess,'run',side_effect=run),contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(kb.BackupError,'KRA 자료가 변경'):
                kb.create(directory)
        self.assertEqual(list(directory.iterdir()),[])


if __name__=='__main__':unittest.main()
