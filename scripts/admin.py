#!/usr/bin/env python3
"""Grant/revoke catalog administration for an existing local account. Does not create a password."""
import argparse,json
from backup import mysql
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('email');p.add_argument('--revoke',action='store_true');a=p.parse_args()
email=a.email.strip().lower()
if '@' not in email or len(email)>254:p.error('Enter the existing account email.')
# Hex literal avoids shell/SQL interpolation of arbitrary email characters.
where="email=CONVERT(0x"+email.encode().hex()+" USING utf8mb4)"
rows=mysql('SELECT id FROM member WHERE '+where+';','keiba').splitlines()
if len(rows)!=1:raise SystemExit('Account not found. Register on the website first.')
mysql('UPDATE member SET is_admin='+('FALSE' if a.revoke else 'TRUE')+' WHERE '+where+';','keiba')
print(json.dumps({'memberId':int(rows[0]),'admin':not a.revoke}))
