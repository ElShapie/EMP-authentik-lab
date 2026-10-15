"""Local task/milestone control; the tracked example contains no assignments."""
import argparse
import json
from pathlib import Path
from datetime import datetime, timezone

SOURCE = Path(__file__).with_name('plan.example.json')

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archivo', type=Path, default=Path.home() / 'lab-runtime/direccion/plan.json')
    sub = p.add_subparsers(dest='action', required=True)
    sub.add_parser('iniciar');sub.add_parser('ver')
    update = sub.add_parser('actualizar')
    update.add_argument('--tarea', required=True)
    update.add_argument('--estado', choices=['pendiente','en_proceso','implementado','validado','bloqueado'], required=True)
    update.add_argument('--responsable', required=True)
    update.add_argument('--evidencia', default='')
    a = p.parse_args()
    if a.action == 'iniciar':
        if a.archivo.exists():p.error('El control ya existe; se conserva sin sobrescribir')
        a.archivo.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        a.archivo.write_text(SOURCE.read_text());a.archivo.chmod(0o600)
    if not a.archivo.exists():p.error('Primero ejecutar iniciar')
    plan = json.loads(a.archivo.read_text())
    if a.action == 'actualizar':
        found = next((t for t in plan['tareas'] if t['id'] == a.tarea), None)
        if found is None:p.error('ID de tarea inexistente')
        if a.estado == 'validado' and not a.evidencia:p.error('La validación necesita referencia de evidencia local')
        found.update(estado=a.estado, responsable=a.responsable, evidencia=a.evidencia, actualizado_utc=datetime.now(timezone.utc).isoformat())
        a.archivo.write_text(json.dumps(plan, indent=2, ensure_ascii=False));a.archivo.chmod(0o600)
    print(json.dumps(plan, indent=2, ensure_ascii=False))
