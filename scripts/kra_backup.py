#!/usr/bin/env python3
"""DB + KRA 원본/진행 기록 백업. 운영 DB 복원/덮어쓰기는 수행하지 않습니다."""
import argparse
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tarfile
import tempfile
from datetime import datetime, timezone
import uuid

ROOT = Path(__file__).resolve().parents[1]
FORMAT = 'keiba-kra-backup-v1'


class BackupError(Exception):
    pass


def digest(source):
    result = hashlib.sha256()
    while chunk := source.read(1024 * 1024):
        result.update(chunk)
    return result.hexdigest()


def file_record(path):
    with path.open('rb') as source:
        value = digest(source)
    return {'size': path.stat().st_size, 'sha256': value}


def kra_files(root):
    files = {}
    for path in sorted(root.rglob('*')):
        if path.name in ('service-key', '.env') or path.name.endswith('.lock'):
            continue
        if path.is_symlink():
            raise BackupError('KRA 폴더에 심볼릭 링크가 있습니다. 원본 파일 위치를 확인하세요.')
        if path.is_dir():
            continue
        if not path.is_file():
            raise BackupError('KRA 폴더에 일반 파일이 아닌 항목이 있습니다.')
        files['kra/' + path.relative_to(root).as_posix()] = path
    return files


def safe_name(name):
    parts = PurePosixPath(name).parts
    return (name == PurePosixPath(name).as_posix() and not name.startswith('/') and
            '\\' not in name and '..' not in parts and len(parts) >= 2 and
            parts[0] in ('kra', 'database') and
            not any(p in ('service-key', '.env') or p.endswith('.lock') for p in parts))


def inspect_bundle(archive, destination=None):
    """Validate every member; extraction writes only regular files into a new directory."""
    with tarfile.open(archive, 'r:gz') as bundle:
        members = bundle.getmembers()
        by_name = {member.name: member for member in members}
        if len(by_name) != len(members) or any(not m.isfile() for m in members):
            raise BackupError('중복 경로 또는 일반 파일이 아닌 백업 항목입니다.')
        meta = by_name.get('manifest.json')
        if meta is None or meta.size > 32 * 1024 * 1024:
            raise BackupError('백업 목록이 없거나 너무 큽니다.')
        manifest = json.load(bundle.extractfile(meta))
        if (not isinstance(manifest, dict) or manifest.get('format') != FORMAT or
                not isinstance(manifest.get('files'), dict) or not isinstance(manifest.get('originalRoot'), str)):
            raise BackupError('지원하지 않는 백업 형식입니다.')
        expected = manifest['files']
        if set(by_name) != set(expected) | {'manifest.json'}:
            raise BackupError('백업 파일 목록이 일치하지 않습니다.')
        if not {'database/backup.sql.gz', 'database/report.json'} <= set(expected):
            raise BackupError('DB 백업 또는 복원 검사 보고서가 없습니다.')
        for name, record in expected.items():
            if (not isinstance(record, dict) or not safe_name(name) or
                    type(record.get('size')) is not int or by_name[name].size != record['size']):
                raise BackupError('백업 경로 또는 크기가 올바르지 않습니다.')
            with bundle.extractfile(by_name[name]) as source:
                if digest(source) != record['sha256']:
                    raise BackupError('백업 파일의 SHA-256이 일치하지 않습니다.')
        report = json.load(bundle.extractfile(by_name['database/report.json']))
        if not isinstance(report, dict) or report.get('isolatedRestorePassed') is not True:
            raise BackupError('별도 스키마 DB 복원 확인 기록이 없습니다.')
        if destination is not None:
            for name in by_name:
                target = destination / name
                target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                with bundle.extractfile(by_name[name]) as source:
                    with os.fdopen(os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'wb') as out:
                        shutil.copyfileobj(source, out, 1024 * 1024)
        return manifest


def pack_bundle(archive, files, metadata):
    records = {name: file_record(path) for name, path in files.items()}
    manifest = {**metadata, 'format': FORMAT, 'files': records}
    with os.fdopen(os.open(archive, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'wb') as raw:
        with tarfile.open(fileobj=raw, mode='w:gz') as bundle:
            for name, path in files.items():
                if not safe_name(name):
                    raise BackupError('허용되지 않은 백업 경로입니다.')
                info = tarfile.TarInfo(name)
                info.size = records[name]['size']; info.mode = 0o600
                with path.open('rb') as source:
                    bundle.addfile(info, source)
            data = json.dumps(manifest, ensure_ascii=False, indent=2).encode()
            info = tarfile.TarInfo('manifest.json'); info.size = len(data); info.mode = 0o600
            bundle.addfile(info, io.BytesIO(data))
    inspect_bundle(archive)
    return manifest


def create(directory):
    kra = ROOT / '.runtime/kra'
    if not kra.is_dir() or kra.is_symlink():
        raise BackupError('로컬 .runtime/kra 원본 폴더를 확인하세요.')
    directory = directory.resolve()
    if directory == kra.resolve() or kra.resolve() in directory.parents:
        raise BackupError('백업 위치는 .runtime/kra 폴더 밖이어야 합니다.')
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    (kra / 'sync').mkdir(exist_ok=True, mode=0o700)
    with (kra / 'sync/sync.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise BackupError('수집 작업이 실행 중입니다. 작업 종료 후 백업하세요.') from None
        files = kra_files(kra)
        if not files:
            raise BackupError('백업할 KRA 자료가 없습니다.')
        before = {name: file_record(path) for name, path in files.items()}
        name = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8]
        archive = directory / (name + '.tar.gz')
        partial = directory / (name + '.partial')
        try:
            with tempfile.TemporaryDirectory(prefix='.kra-backup-', dir=directory) as tmp:
                print('DB 백업 및 별도 스키마 복원 검사 중…', flush=True)
                result = subprocess.run([sys.executable, str(ROOT/'scripts/backup.py'), '--directory', tmp],
                                        cwd=ROOT, capture_output=True, text=True, check=True)
                database = json.loads(result.stdout)
                report = json.loads(Path(database['report']).read_text())
                report['backup'] = 'database/backup.sql.gz'
                Path(database['report']).write_text(json.dumps(report, ensure_ascii=False, indent=2))
                files.update({'database/backup.sql.gz': Path(database['backup']),
                              'database/report.json': Path(database['report'])})
                revision = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True)
                print('KRA 원본·진행 기록 압축 및 파일 검사 중…', flush=True)
                manifest = pack_bundle(partial, files, {
                    'createdAt': datetime.now(timezone.utc).isoformat(), 'originalRoot': str(ROOT),
                    'revision': revision.stdout.strip() if revision.returncode == 0 else None,
                    'excluded': ['.env', '.runtime/kra/service-key', '*.lock'],
                    'scope': 'Same-server isolated database restore checked at creation; no live restore or off-host test.'})
                after = {key: file_record(path) for key, path in kra_files(kra).items()}
                if before != after:
                    raise BackupError('백업 도중 KRA 자료가 변경됐습니다. 쓰기 작업을 멈춘 뒤 재시도하세요.')
                from backup import inventory
                if inventory('keiba') != report['tables']:
                    raise BackupError('백업 도중 DB가 변경됐습니다. 쓰기 작업을 멈춘 뒤 재시도하세요.')
            partial.rename(archive)
        finally:
            partial.unlink(missing_ok=True)
        print('백업 완료:', archive)
        print('포함 파일:', len(manifest['files']), '/ DB 별도 스키마 복원·파일 SHA-256 검사 통과')
        print('인증키와 .env는 제외했습니다. 백업은 암호화되지 않았으며 DB 회원 정보가 포함될 수 있습니다.')
        print('같은 PC의 백업만으로 디스크 손실에 대비할 수 없습니다. 별도 저장장치에 복사하세요.')
        return archive


def extract(archive, target):
    # Never accept an existing directory, even when empty. Never restore the live database.
    target.mkdir(parents=True, exist_ok=False, mode=0o700)
    try:
        manifest = inspect_bundle(archive, target)
    except Exception:
        shutil.rmtree(target)
        raise
    print('검증 및 별도 폴더 풀기 완료:', target)
    print('운영 DB·수집 폴더는 변경하지 않았습니다. 원래 프로젝트 경로:', manifest['originalRoot'])
    print('다른 경로로 옮길 때는 진행 JSON의 절대 경로를 별도로 조정해야 합니다.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    command = commands.add_parser('create'); command.add_argument('--directory', type=Path, default=ROOT/'.runtime/backups/kra')
    command = commands.add_parser('verify'); command.add_argument('archive', type=Path)
    command = commands.add_parser('extract'); command.add_argument('archive', type=Path); command.add_argument('--to', type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == 'create':
            create(args.directory)
        elif args.command == 'verify':
            manifest = inspect_bundle(args.archive)
            print(f"파일 무결성 검사 통과: {len(manifest['files'])}개 (DB 재복원은 수행하지 않았습니다.)")
        else:
            extract(args.archive, args.to)
        return 0
    except (BackupError, OSError, ValueError, KeyError, TypeError, tarfile.TarError, subprocess.CalledProcessError) as exc:
        print(str(exc) if isinstance(exc, BackupError) else '백업 작업 실패: Docker/DB 상태, 경로·권한·파일 형식·여유 공간을 확인하세요. 완료된 백업으로 취급하지 마세요.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
