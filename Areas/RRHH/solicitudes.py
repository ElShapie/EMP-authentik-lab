"""Control local de solicitudes: no aprovisiona cuentas ni autentica operadores."""
import argparse
import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

OWNERS = {'aplicacion': 'TI', 'onelogin': 'IAM', 'microsoft365': 'TI', 'rfid': 'Seguridad_Fisica'}

class Requests:
    def __init__(self, path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS requests (id TEXT PRIMARY KEY,payload TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS history (time TEXT,id TEXT,actor TEXT,action TEXT)')
        Path(path).chmod(0o600)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path)
        try:
            with db:
                yield db
        finally:
            db.close()

    def get(self, request_id):
        with self.connect() as db:
            row = db.execute('SELECT payload FROM requests WHERE id=?', (request_id,)).fetchone()
        if not row:
            raise ValueError('Solicitud inexistente')
        return json.loads(row[0])

    def write(self, payload, actor, action):
        with self.connect() as db:
            db.execute('INSERT INTO requests VALUES (?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload', (payload['id'], json.dumps(payload)))
            db.execute('INSERT INTO history VALUES (?,?,?,?)', (datetime.now(timezone.utc).isoformat(), payload['id'], actor, action))
        return payload

    def create(self, actor, employee, kind, resource, role):
        if not actor or not employee or resource not in OWNERS or kind not in ('alta', 'cambio', 'baja'):
            raise ValueError('Revisar actor, identidad, tipo y recurso')
        return self.write({'id': 'SOL-' + uuid.uuid4().hex[:12], 'solicitante': actor, 'empleado': employee, 'tipo': kind, 'recurso': resource, 'rol': role, 'estado': 'pendiente'}, actor, 'crear')

    def approve(self, request_id, actor, area):
        item = self.get(request_id)
        if item['estado'] != 'pendiente' or actor == item['solicitante'] or not actor or area != OWNERS[item['recurso']]:
            raise ValueError('Aprobación inválida: requiere otro operador del área dueña y estado pendiente')
        item.update(estado='aprobada', aprobador=actor, area_aprobadora=area)
        return self.write(item, actor, 'aprobar')

    def close(self, request_id, actor, evidence):
        item = self.get(request_id)
        if item['estado'] != 'aprobada' or not evidence or not actor:
            raise ValueError('Se requiere aprobación y referencia de evidencia local')
        item.update(estado='implementada', implementador=actor, evidencia=evidence)
        return self.write(item, actor, 'cerrar')

    def list(self):
        with self.connect() as db:
            return [json.loads(row[0]) for row in db.execute('SELECT payload FROM requests ORDER BY rowid')]

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--db', type=Path, default=Path.home() / 'lab-runtime/rrhh/control.sqlite')
    subs = p.add_subparsers(dest='action', required=True)
    create = subs.add_parser('crear')
    for field in ['actor', 'empleado', 'tipo', 'recurso', 'rol']: create.add_argument('--' + field, required=True)
    approve = subs.add_parser('aprobar')
    for field in ['id', 'actor', 'area']: approve.add_argument('--' + field, required=True)
    close = subs.add_parser('cerrar')
    for field in ['id', 'actor', 'evidencia']: close.add_argument('--' + field, required=True)
    subs.add_parser('listar')
    args = p.parse_args(); store = Requests(args.db)
    try:
        if args.action == 'crear': result = store.create(args.actor, args.empleado, args.tipo, args.recurso, args.rol)
        elif args.action == 'aprobar': result = store.approve(args.id, args.actor, args.area)
        elif args.action == 'cerrar': result = store.close(args.id, args.actor, args.evidencia)
        else: result = store.list()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except ValueError as exc: p.error(str(exc))

if __name__ == '__main__': main()
