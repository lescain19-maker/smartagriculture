"""Windows launcher companion. Credentials stay in this process's environment."""
import getpass
import importlib.util
from pathlib import Path
import subprocess
import os
import sys


def ensure_discovery_runtime():
    """Install discovery in a checkout-local virtualenv when needed."""
    if importlib.util.find_spec('zeroconf') is not None:
        return None
    root = Path(__file__).resolve().parent
    environment = root / '.venv'
    python = environment / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    try:
        if not python.exists():
            print('Preparing local Python environment (first start only)...', flush=True)
            subprocess.run([sys.executable, '-m', 'venv', str(environment)], check=True)
        installed = subprocess.run([str(python), '-c', 'import zeroconf'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if installed.returncode:
            print('Installing automatic network discovery (internet needed once)...', flush=True)
            subprocess.run([str(python), '-m', 'pip', 'install', '-r', str(root / 'requirements.txt')], check=True)
        return subprocess.call([str(python), str(root / 'start_local.py')])
    except (OSError, subprocess.CalledProcessError):
        print('Could not prepare automatic discovery. Check Python, internet access and requirements.txt.')
        return 1


def main():
    if sys.version_info < (3, 10):
        print('Python 3.10 or newer is required.')
        return 1
    result = ensure_discovery_runtime()
    if result is not None:
        return result
    print('Smart Agric - Local Dashboard')
    print('Use the same private LOCAL_DEVICE_KEY as in your ESP32 secrets.h.')
    print('The key will not be displayed or saved. Ctrl+C cancels.\n')
    key = os.environ.get('ESP32_DEVICE_KEY', '')
    if key and len(key) < 16:
        print('ESP32_DEVICE_KEY is too short. Enter the correct key below.')
        key = ''
    while len(key) < 16:
        key = getpass.getpass('Local device key (at least 16 characters): ').strip()
        if len(key) < 16:
            print('Please enter a key of at least 16 characters.')
    os.environ['ESP32_DEVICE_KEY'] = key
    print('\nOpening http://localhost:8000 in your browser.')
    print('Your ESP32 will discover this computer automatically on the same LAN.')
    print('Allow Python on your private network if Windows Firewall asks.')
    print('Leave this window running. Press Ctrl+C to stop.\n')
    import server
    sys.argv = [str(server.ROOT / 'server.py'), '--host', '0.0.0.0', '--port', '8000', '--open-browser']
    try:
        server.main()
    except OSError as exc:
        print(f'Unable to start the local server: {exc}')
        print('If port 8000 is already in use, close the existing server and try again.')
        return 1
    finally:
        os.environ.pop('ESP32_DEVICE_KEY', None)
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (KeyboardInterrupt, EOFError):
        print('\nStartup cancelled.')
        raise SystemExit(0)
