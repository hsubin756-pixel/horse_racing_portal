"""Temporary synthetic records for the KRA browser flow; never calls the provider."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from backup import mysql
from kra_import import prepare, apply
from test_kra_import import sample_rows, sectional_rows, mixed_result_rows, RETRIEVED
from kra import MEET_CODES

PREFIX = '970000'


def main():
    meet = sys.argv[2] if sys.argv[1] == 'create' and len(sys.argv) > 2 else sys.argv[3] if sys.argv[1] == 'clean' and len(sys.argv) > 3 else '서울'
    key = f'{MEET_CODES[meet]}:20100101:94'
    if sys.argv[1] == 'create':
        if mysql(f"SELECT COUNT(*) FROM race WHERE kra_id='{key}';", 'keiba').strip() != '0':
            raise SystemExit('Browser fixture key already exists; no data changed.')
        if mysql(f"SELECT COUNT(*) FROM horse WHERE kra_id LIKE '{PREFIX}%';", 'keiba').strip() != '0':
            raise SystemExit('Browser fixture horses already exist; no data changed.')
        rows = sample_rows(race_no=94, prefix=PREFIX) if meet == '서울' else sectional_rows(meet, PREFIX)
        if len(sys.argv) > 3 and sys.argv[3] == 'nonfinishers':
            rows = mixed_result_rows(prefix=PREFIX, race_no=94)
        for row in rows:
            row['rcNo'] = '94'
        plan = prepare(rows, RETRIEVED)
        race_id = apply(plan)[0][0]
        print(json.dumps({'raceId': race_id}))
    elif sys.argv[1] == 'clean':
        # Verify ID AND reserved key to avoid touching any other race.
        race_id = int(sys.argv[2])
        if mysql(f"SELECT COUNT(*) FROM race WHERE id={race_id} AND kra_id='{key}';", 'keiba').strip() != '1':
            raise SystemExit('Fixture identity mismatch; no data changed.')
        entries = f'SELECT id FROM entry WHERE race_id={race_id}'
        mysql(f'DELETE FROM sectional_marker WHERE entry_id IN ({entries});'
              f'DELETE FROM sectional WHERE entry_id IN ({entries});'
              f'DELETE FROM entry WHERE race_id={race_id};DELETE FROM kra_race_import WHERE race_id={race_id};'
              f'DELETE FROM race WHERE id={race_id};'
              f"DELETE FROM horse WHERE kra_id LIKE '{PREFIX}%';"
              f"DELETE FROM person WHERE kra_id LIKE '{PREFIX}%';", 'keiba')


if __name__ == '__main__':
    main()
