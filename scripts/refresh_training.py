#!/usr/bin/env python3
"""학습 자료 갱신 한 줄 명령: API155 수집 → ml/data/*.csv 내보내기 → 실제 데이터 모델 재학습.

  python3 scripts/refresh_training.py --meets 1 2 3 --from 20250104 --to 20251228

경마장마다 collect(이미 받은 날짜는 건너뜀) → export(ml/data/<경마장>-<연도>.csv) 를 실행하고, 마지막에 ml/train_real.py 로
모델·이력·보고서를 다시 만듭니다. 호출 한도로 일부 날짜가 남으면 CSV를 만들지 않고 멈추니 같은 명령을 다시 실행하세요.
ML 서비스에 반영하려면 끝난 뒤 ./scripts/up.sh 로 이미지를 다시 빌드합니다(자동으로 하지 않습니다).
--dry-run 은 호출·파일 쓰기 없이 계획만 출력합니다.
"""
import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kra_ml_dataset as ds  # noqa: E402
from kra import KraError  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'ml' / 'data'
SLUGS = {'1': 'seoul', '2': 'jeju', '3': 'busan'}


def label(start, end):
    return str(start.year) if start.year == end.year else f'{start:%Y%m%d}-{end:%Y%m%d}'


def target(meet, start, end, data=DATA):
    """내보낼 CSV 경로. 같은 경마장의 다른 기간 CSV가 있으면 경주 ID가 겹쳐 학습이 실패하므로 미리 막습니다."""
    path = data / f'{SLUGS[meet]}-{label(start, end)}.csv'
    others = sorted(p.name for p in data.glob(f'{SLUGS[meet]}-*.csv') if p != path)
    if others:
        raise KraError(f'{", ".join(others)} 와 기간이 겹칠 수 있습니다. 한 경마장은 CSV 한 개로 관리하세요: 기존 파일을 지우고(또는 같은 기간으로 맞추고) 다시 실행하세요.')
    return path


def python_for_ml():
    venv = ROOT / '.runtime' / 'ml-venv' / 'bin' / 'python'
    return str(venv) if venv.exists() else sys.executable


def run(args, data=DATA):
    plan = [(meet, target(meet, args.start, args.end, data)) for meet in args.meets]
    print('계획: ' + ' · '.join(f'{ds.MEETS[m]}→{p.name}' for m, p in plan) + (' · 재학습 생략' if args.skip_train else ' · 재학습 포함'))
    if args.dry_run:
        print('--dry-run: 호출·파일 쓰기 없이 종료합니다.')
        return 0
    for meet, path in plan:
        result = ds.collect(meet, args.start, args.end, args.max_calls, False)
        if result and result['remaining']:
            raise KraError(f'{ds.MEETS[meet]}: 남은 날짜 {result["remaining"]}개가 있어 CSV를 만들지 않았습니다. 같은 명령을 다시 실행하세요(한도 초과 시 다음 날).')
        ds.export(meet, str(path))
    if args.skip_train:
        print('재학습을 생략했습니다. 나중에: python3 ml/train_real.py')
        return 0
    done = subprocess.run([python_for_ml(), str(ROOT / 'ml' / 'train_real.py')], cwd=ROOT)
    if done.returncode != 0:
        raise KraError('ml/train_real.py 가 실패했습니다. 위 메시지를 확인하세요(.runtime/ml-venv 가 없으면 ./scripts/build.sh 로 만들 수 있습니다).')
    provenance = (data / 'PROVENANCE.md').read_text(encoding='utf-8') if (data / 'PROVENANCE.md').exists() else ''
    missing = [ds.MEETS[m] for m, _ in plan if ds.MEETS[m] not in provenance]
    if missing:
        print(f'주의: ml/data/PROVENANCE.md 에 {", ".join(missing)} 자료 출처·기간이 없습니다. 파일을 갱신한 뒤 커밋하세요.')
    print('다음: git add ml/data && git commit, 그리고 ./scripts/up.sh 로 ML 이미지를 다시 빌드한 뒤 curl http://127.0.0.1:8000/health 의 realDataModel.cutoffDate 를 확인하세요.')
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--meets', nargs='+', default=['1'], choices=sorted(SLUGS), help='1 서울 / 2 제주 / 3 부산경남 (기본 1)')
    parser.add_argument('--from', dest='start', required=True, type=ds.parse_day)
    parser.add_argument('--to', dest='end', required=True, type=ds.parse_day)
    parser.add_argument('--max-calls', type=int, default=250, help='경마장별 이번 실행의 최대 호출 수 (기본 250)')
    parser.add_argument('--skip-train', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args(argv)
    args.meets = list(dict.fromkeys(args.meets))
    try:
        if not 1 <= args.max_calls <= 1000:
            raise KraError('--max-calls 는 1~1000 입니다.')
        return run(args)
    except KraError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except (OSError, UnicodeError, ValueError):
        print('로컬 파일을 읽거나 저장하지 못했거나 자료 형식이 올바르지 않습니다. 메시지와 폴더 권한을 확인하세요.', file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print('\n취소했습니다. 받은 날짜는 보존되어 있어 다시 실행하면 이어 받습니다.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
