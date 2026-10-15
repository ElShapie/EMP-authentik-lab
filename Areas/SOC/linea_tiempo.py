"""Join RFID and application events by UTC and explicit laboratory identity."""
import argparse
import csv
import html
import json
from datetime import datetime, timezone
from pathlib import Path

def utc(value):
    stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if stamp.tzinfo is None: raise ValueError('Cada evento requiere zona horaria explícita')
    return stamp.astimezone(timezone.utc)

def collect(rfid, application, employee):
    events = []
    with Path(rfid).open(encoding='utf-8-sig', newline='') as f:
        for row in csv.DictReader(f):
            if employee and row['empleado'] != employee: continue
            events.append({'time': utc(row['hora_utc']), 'identity': row['empleado'], 'source': 'RFID', 'action': row['movimiento'], 'result': row['resultado']})
    for row in json.loads(Path(application).read_text()):
        identity = row.get('employee') or row['user']
        if employee and identity != employee: continue
        events.append({'time': utc(row['time']), 'identity': identity, 'source': 'Aplicación', 'action': row['action'], 'result': row['result']})
    return sorted(events, key=lambda row: row['time'])

def render(events):
    body = '<!doctype html><meta charset="utf-8"><title>Línea de tiempo</title><h1>Línea de tiempo del recorrido</h1><p>Relación por identificador explícito y hora UTC. Revisar el video manualmente; la coincidencia temporal no prueba causalidad.</p><table border="1"><tr><th>UTC</th><th>Identidad</th><th>Fuente</th><th>Acción</th><th>Resultado</th></tr>'
    for row in events:
        body += '<tr>' + ''.join('<td>' + html.escape(str(row[key])) + '</td>' for key in ['time','identity','source','action','result']) + '</tr>'
    return body + '</table>'

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rfid', required=True);p.add_argument('--aplicacion', required=True)
    p.add_argument('--empleado');p.add_argument('--salida', type=Path, required=True)
    a = p.parse_args();events = collect(a.rfid, a.aplicacion, a.empleado)
    a.salida.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    a.salida.write_text(render(events));a.salida.chmod(0o600)
    print(f'Eventos relacionados: {len(events)}. Abrir el HTML localmente.')
