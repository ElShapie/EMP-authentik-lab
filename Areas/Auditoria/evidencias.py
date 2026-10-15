"""Build a reproducible SHA-256 manifest without embedding evidence contents."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

def manifest(folder, excluded=None):
    folder = Path(folder).resolve()
    return [{'archivo': str(p.relative_to(folder)), 'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(folder.rglob('*')) if p.is_file() and not p.is_symlink() and p.resolve() != excluded]

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__);p.add_argument('--carpeta', type=Path, required=True);p.add_argument('--salida', type=Path, required=True)
    a = p.parse_args()
    if not a.carpeta.is_dir():p.error('La carpeta de evidencias no existe')
    entries = manifest(a.carpeta, a.salida.resolve())
    a.salida.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    a.salida.write_text(json.dumps({'generado_utc':datetime.now(timezone.utc).isoformat(),'archivos':entries},indent=2));a.salida.chmod(0o600)
    print(f'Manifiesto local generado: {len(entries)} archivos. No acredita por sí mismo que una prueba pasó.')
