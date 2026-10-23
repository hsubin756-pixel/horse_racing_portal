"""Temporary synthetic records for the KRA browser flow; never calls the provider."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from backup import mysql
from kra_import import prepare, apply
from test_kra_import import sample_rows, RETRIEVED

PREFIX = '970000'
KEY = '1:20100101:94'


def main():
    if sys.argv[1] == 'create':
        if mysql(f"SELECT COUNT(*) FROM race WHERE kra_id='{KEY}';", 'keiba').strip() != '0':
            raise SystemExit('Browser fixture key already exists; no data changed.')
        if mysql(f"SELECT COUNT(*) FROM horse WHERE kra_id LIKE '{PREFIX}%';", 'keiba').strip() != '0':
            raise SystemExit('Browser fixture horses already exist; no data changed.')
        rows = sample_rows(race_no=94, prefix=PREFIX)
        plan = prepare(rows, RETRIEVED)
        race_id = apply(plan)[0][0]
        print(json.dumps({'raceId': race_id}))
    elif sys.argv[1] == 'clean':
        # Verify ID AND reserved key to avoid touching any other race.
        race_id = int(sys.argv[2])
        if mysql(f"SELECT COUNT(*) FROM race WHERE id={race_id} AND kra_id='{KEY}';", 'keiba').strip() != '1':
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
