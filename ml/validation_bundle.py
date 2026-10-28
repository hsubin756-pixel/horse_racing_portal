"""Preserve a reviewed candidate's training data, evaluator and prospective plan.
No API calls or production model writes. Run final only after the reserved period.
"""
import argparse
import csv
from datetime import date
from importlib.metadata import version
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import experiment as exp

CODE_FILES = ('experiment.py', 'evaluate_tracks.py', 'evaluate_extended.py', 'evaluate.py', 'validation_bundle.py')
PACKAGES = ('numpy', 'scikit-learn', 'scipy', 'joblib', 'threadpoolctl')
PAYLOADS = {'training.csv', 'plan.json', 'development-report.json', 'decision.json',
            'environment.json', 'requirements.txt', *(f'code/{p}' for p in CODE_FILES)}
CRITERIA = {
    'primary': 'top3 recall difference versus market on the same eligible races',
    'reviewThreshold': 'positive mean difference AND paired race bootstrap 95% lower bound > 0 for every selected track',
    'secondary': ['rocAuc', 'averagePrecision'],
    'failedThreshold': 'retain existing service model; do not retune on this final period',
    'passingThreshold': 'review_only; timing, population, calibration and full-coverage checks still required',
    'automaticPromotion': False,
}


def environment():
    return {'python': f'{sys.version_info.major}.{sys.version_info.minor}',
            'packages': {p: version(p) for p in PACKAGES}}


def sha(path):
    import hashlib
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify(folder):
    folder = Path(folder)
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError('Bundle must be a real directory')
    if (folder/'manifest.json').is_symlink():
        raise ValueError('Symlink manifest is not allowed')
    manifest = json.loads((folder/'manifest.json').read_text())
    if manifest.get('kind') != 'validation_bundle_v1' or set(manifest.get('files', {})) != PAYLOADS:
        raise ValueError('Invalid bundle manifest or payload list')
    for relative, expected in manifest['files'].items():
        path = folder/relative
        # Both payload and the one possible intermediate code directory must be ordinary paths.
        if path.is_symlink() or (relative.startswith('code/') and (folder/'code').is_symlink()) or not path.is_file():
            raise ValueError('Missing or symlink payload: ' + relative)
        if sha(path) != expected:
            raise ValueError('Bundle payload changed: ' + relative)
    plan = json.loads((folder/'plan.json').read_text())
    if plan.get('planDigest') != exp.digest({k: v for k, v in plan.items() if k != 'planDigest'}):
        raise ValueError('Invalid frozen plan digest')
    code_hash = exp.digest({name: sha(folder/'code'/name) for name in CODE_FILES[:3]})
    if code_hash != plan['codeHash']:
        raise ValueError('Preserved code differs from frozen plan')
    results = folder/'results'
    if results.exists() or results.is_symlink():
        if results.is_symlink() or not results.is_dir() or (results/'manifest.json').is_symlink():
            raise ValueError('Invalid final results directory')
        files = json.loads((results/'manifest.json').read_text())
        if set(files) != {'evaluation.json', 'decision.json'}:
            raise ValueError('Invalid final results manifest')
        for name, expected in files.items():
            if (results/name).is_symlink() or sha(results/name) != expected:
                raise ValueError('Final results changed: ' + name)
    return plan


def prepare(report_path, folder, start, end, cohort, feature_set):
    folder, report_path = Path(folder), Path(report_path)
    if folder.exists() or folder.is_symlink():
        raise ValueError('Destination already exists; never replace a validation bundle')
    report_bytes = report_path.read_bytes()
    report = json.loads(report_bytes)
    if report.get('kind') != 'development_ablation' or report.get('modelParameters') != exp.PARAMS or report.get('audit', {}).get('featureSets') != exp.SETS:
        raise ValueError('Expected an experiment.py development ablation report with matching configuration')
    hashes = report.get('inputHashes', {})
    if not hashes:
        raise ValueError('Report has no input hashes')
    # Paths are those recorded by compare; run from the same repository directory.
    if any(sha(path) != expected for path, expected in hashes.items()):
        raise ValueError('A source CSV changed since development evaluation; keep the old report and review a new comparison first')
    races, actual = exp.read([Path(path) for path in hashes])
    if actual != hashes:
        raise ValueError('Source CSV changed while preparing')
    train_end = report['developmentEndExclusive']
    windows = report.get('windows', [])
    if len(windows) < 2 or windows[-1]['endExclusive'] != train_end:
        raise ValueError('Development windows do not match the training boundary')
    evidence = []
    for window in windows:
        if window['endExclusive'] > train_end or window['start'] >= window['endExclusive']:
            raise ValueError('Invalid development window')
        c = window['cohorts'][cohort]
        if c['status'] != 'evaluated':
            raise ValueError('Selected cohort was not evaluated in every development window')
        tracks = {}
        for track in exp.COHORTS[cohort]:
            t = c['byTrack'][track]
            if not t['market'] or not t['variants'][feature_set]['matchedMarket']:
                raise ValueError('Selected candidate lacks matched market evidence')
            tracks[track] = {'marketRaces': t['marketRaces'], 'market': t['market'],
                             'candidate': t['variants'][feature_set], 'base': t['variants']['base']}
        evidence.append({'start': window['start'], 'endExclusive': window['endExclusive'], 'tracks': tracks})
    plan = exp.freeze(races, train_end, start, end, cohort, feature_set)
    chosen = [r for k, rs in sorted(races.items()) if k.split(':')[0] in exp.COHORTS[cohort]
              and rs[0]['race_date'].isoformat() < train_end for r in rs]
    columns = list(chosen[0])
    if any(set(row) != set(columns) for row in chosen):
        raise ValueError('Training CSV schemas differ')
    folder.mkdir(parents=True, exist_ok=False, mode=0o700)
    try:
        with (folder/'training.csv').open('x', newline='', encoding='utf-8') as sink:
            writer = csv.DictWriter(sink, fieldnames=columns); writer.writeheader(); writer.writerows(chosen)
        stored, _ = exp.read([folder/'training.csv'])
        if exp.training_digest(stored, train_end, cohort) != plan['trainingDigest']:
            raise ValueError('Training snapshot differs after CSV serialization')
        (folder/'development-report.json').write_bytes(report_bytes)
        exp.save(folder/'plan.json', plan)
        exp.save(folder/'decision.json', {'selection': 'Explicit operator-selected research candidate; not a production promotion',
                 'cohort': cohort, 'featureSet': feature_set, 'criteria': CRITERIA, 'developmentEvidence': evidence,
                 'limitations': exp.LIMITS})
        runtime = environment()
        exp.save(folder/'environment.json', runtime)
        (folder/'requirements.txt').write_text(''.join(f'{p}=={v}\n' for p, v in runtime['packages'].items()))
        (folder/'code').mkdir()
        for name in CODE_FILES:
            shutil.copyfile(Path(__file__).with_name(name), folder/'code'/name)
        if report_bytes != report_path.read_bytes():
            raise ValueError('Development report changed during preparation')
        exp.save(folder/'manifest.json', {'kind': 'validation_bundle_v1', 'files': {p: sha(folder/p) for p in sorted(PAYLOADS)}})
        verify(folder)
    except BaseException:
        shutil.rmtree(folder)
        raise
    return plan


def decision(result, criteria):
    tracks = result['window']['cohorts'][result['plan']['cohort']]['byTrack']
    verdicts = {}
    for track, t in tracks.items():
        variant = t['variants'][result['plan']['featureSet']]
        delta = variant['deltaAgainstMarket']
        if delta is None:
            verdicts[track] = 'inconclusive_missing_market'
        elif delta['top3RecallDelta'] > 0 and delta['pairedRaceBootstrap95'][0] > 0:
            verdicts[track] = 'review_only'
        else:
            verdicts[track] = 'threshold_not_met'
    return {'kind': 'final_candidate_review', 'criteria': criteria, 'byTrack': verdicts,
            'decision': 'review_only' if verdicts and all(v == 'review_only' for v in verdicts.values()) else 'do_not_promote',
            'coverageVerified': False, 'preRaceAvailabilityVerified': False, 'promoted': False,
            'note': 'Passing a descriptive bootstrap threshold does not establish pre-race validity or profitability.'}


def run_final(folder, csv_paths):
    folder = Path(folder).resolve()
    plan = verify(folder)
    if exp.today() < date.fromisoformat(plan['endExclusive']):
        raise ValueError('Final period has not ended; no interim evaluation')
    if environment() != json.loads((folder/'environment.json').read_text()):
        raise ValueError('Environment changed; recreate the saved Python major/minor and requirements in a separate venv')
    if (folder/'results').exists() or (folder/'results').is_symlink():
        raise ValueError('Final results already exist; never rerun or replace automatically')
    policy = json.loads((folder/'decision.json').read_text())['criteria']
    if policy != CRITERIA:
        raise ValueError('Decision criteria differ from this runner; use the matching runner version')
    lock = folder/'.final-lock'
    lock.mkdir()  # Exclude two simultaneous final runs.
    stage = None
    try:
        if (folder/'results').exists():
            raise ValueError('Final results already exist')
        stage = Path(tempfile.mkdtemp(prefix='.final-', dir=folder))
        command = [sys.executable, str(folder/'code/experiment.py'), 'final', str(folder/'training.csv'),
                   *(str(Path(p).resolve()) for p in csv_paths), '--plan', str(folder/'plan.json'), '--output', str(stage/'evaluation.json')]
        subprocess.run(command, check=True)
        result = json.loads((stage/'evaluation.json').read_text())
        verify(folder)
        verdict = decision(result, policy)
        exp.save(stage/'decision.json', verdict)
        exp.save(stage/'manifest.json', {p: sha(stage/p) for p in ('evaluation.json', 'decision.json')})
        stage.rename(folder/'results')
        stage = None
        return verdict
    finally:
        if stage is not None:
            shutil.rmtree(stage)
        lock.rmdir()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    create = commands.add_parser('prepare')
    create.add_argument('--report', required=True, type=Path)
    create.add_argument('--output', required=True, type=Path)
    create.add_argument('--cohort', choices=exp.COHORTS, required=True)
    create.add_argument('--feature-set', choices=exp.SETS, required=True)
    create.add_argument('--start', required=True); create.add_argument('--end', required=True)
    check = commands.add_parser('verify'); check.add_argument('bundle', type=Path)
    final = commands.add_parser('final'); final.add_argument('bundle', type=Path); final.add_argument('csv', nargs='+', type=Path)
    args = parser.parse_args()
    try:
        if args.command == 'prepare':
            plan = prepare(args.report, args.output, args.start, args.end, args.cohort, args.feature_set)
            print('검증 묶음 준비 완료:', args.output)
            print('후보:', plan['cohort'], plan['featureSet'], '/ 기간:', plan['start'], '~', plan['endExclusive'], '(끝 제외)')
            snapshot, _ = exp.read([args.output/'training.csv'])
            print('학습 스냅샷:', len({rs[0]['race_date'] for rs in snapshot.values()}), '일 /',
                  len(snapshot), '경주 /', sum(len(rs) for rs in snapshot.values()), '건')
            print('학습 스냅샷·실험 코드·환경·선택 근거·고정 계획 보존 / API 호출·서비스 모델 변경 없음')
        elif args.command == 'verify':
            plan = verify(args.bundle)
            print('검증 묶음 무결성 확인:', plan['cohort'], plan['featureSet'], '/ 성능 평가는 실행하지 않았습니다.')
        else:
            result = run_final(args.bundle, args.csv)
            print('최종 판정:', result['decision'], '/ 자동 서비스 반영 없음')
        return 0
    except (ValueError, KeyError, TypeError, OSError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f'검증 준비/평가 중단: {exc}\n')


if __name__ == '__main__':
    main()
