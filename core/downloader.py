import subprocess
import os
from pathlib import Path
from config.settings import DLUB_BIN, SOURCE_ROOT


def run_dlub_download() -> bool:
    print("==================================================")
    print("\t\tAvvio Fase Download: dlub -get all")
    print("==================================================")

    SOURCE_ROOT.mkdir(parents=True, exist_ok=True)
    cmd = [DLUB_BIN, "-get", "all"]

    try:
        res = subprocess.run(
            cmd,
            cwd=str(SOURCE_ROOT),
            capture_output=True,
            text=True,
            timeout=300
        )
        if res.returncode == 0:
            print("Download dlub completato con successo.")
            if res.stdout.strip():
                print(f"--- Output dlub ---\n{res.stdout.strip()}\n-------------------")
            return True
        else:
            print(f"Avviso o errore dlub (exit {res.returncode}):\n{res.stderr or res.stdout}")
            return False
    except Exception as e:
        print(f"Eccezione durante l'esecuzione di dlub: {e}")
        return False
