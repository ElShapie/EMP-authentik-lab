"""Run the actual local test suites and write an optional local result."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]

if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--salida',type=Path);a=p.parse_args()
    suites=[('permisos','Implementacion/app','test_store.py'),('publicacion','scripts','test_public_content.py'),('practica','tests','test_practice.py')]
    results=[]
    for name,folder,pattern in suites:
        r=subprocess.run([sys.executable,'-m','unittest','discover','-s',folder,'-p',pattern,'-v'],cwd=ROOT,capture_output=True,text=True)
        print(r.stdout+r.stderr)
        results.append({'suite':name,'exit_code':r.returncode,'correcto':r.returncode==0})
    summary={'hora_utc':datetime.now(timezone.utc).isoformat(),'suites':results,'integraciones_externas':'no verificadas por este comando'}
    if a.salida:
        a.salida.parent.mkdir(parents=True,exist_ok=True,mode=0o700);a.salida.write_text(json.dumps(summary,indent=2));a.salida.chmod(0o600)
    raise SystemExit(0 if all(r['correcto'] for r in results) else 1)
