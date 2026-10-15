"""Export application audit events from a local SQLite copy; never commits data."""
import argparse
import json
import sqlite3
from pathlib import Path

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base', type=Path, required=True);p.add_argument('--salida', type=Path, required=True)
    a = p.parse_args()
    if not a.base.is_file(): p.error('La base no existe; no se crea una nueva por accidente')
    with sqlite3.connect(a.base.resolve().as_uri() + '?mode=ro', uri=True) as db:
        db.row_factory = sqlite3.Row
        events = [dict(row) for row in db.execute('SELECT * FROM events ORDER BY rowid')]
    a.salida.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    a.salida.write_text(json.dumps(events, indent=2));a.salida.chmod(0o600)
    print('Exportación local guardada. No cargar el archivo a GitHub.')
