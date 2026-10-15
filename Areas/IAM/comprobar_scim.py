"""Read-only check: SCIM rejects anonymous access and accepts a valid token."""
import argparse
import json
import os
import urllib.request
import urllib.error
from urllib.parse import urlsplit

def fetch(url, token=None):
    headers = {'Authorization': 'Bearer ' + token} if token else {}
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=15) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc: return exc.code, None

def main():
    p = argparse.ArgumentParser(description=__doc__);p.add_argument('--url', required=True);p.add_argument('--scim-version', choices=('1','2'), default='2');args = p.parse_args()
    url = urlsplit(args.url)
    if url.scheme != 'https' or not url.hostname or url.username or url.password: p.error('Usar URL HTTPS sin credenciales')
    token = os.environ.get('SCIM_TOKEN', '')
    if not token or 'REEMPLAZAR' in token: p.error('Cargar SCIM_TOKEN desde el .env local de la aplicación')
    target = args.url.rstrip('/') + f'/scim/v{args.scim_version}/Users'
    anonymous, _ = fetch(target)
    authorized, body = fetch(target, token)
    valid = anonymous == 401 and authorized == 200 and isinstance(body, dict) and isinstance(body.get('Resources'), list)
    print(json.dumps({'anonimo': anonymous, 'autorizado': authorized, 'correcto': valid}))
    raise SystemExit(0 if valid else 1)

if __name__ == '__main__': main()
