"""Comprobar conectividad TCP de un destino autorizado del laboratorio."""
import argparse
import socket
import json
from datetime import datetime, timezone

def check(host, port, timeout=3):
    try:
        with socket.create_connection((host, port), timeout=timeout): pass
        ok = True
    except OSError: ok = False
    return {'hora_utc': datetime.now(timezone.utc).isoformat(), 'host': host, 'port': port, 'tcp_disponible': ok}

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--host', required=True); p.add_argument('--puerto', type=int, required=True)
    a = p.parse_args()
    result = check(a.host, a.puerto)
    print(json.dumps(result)); raise SystemExit(0 if result['tcp_disponible'] else 1)
