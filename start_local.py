"""Windows launcher companion. Credentials stay in this process's environment."""
import getpass
import os
import sys


def main():
    if sys.version_info < (3, 10):
        print('Python 3.10 or newer is required.')
        return 1
    print('Smart Agric - Local Dashboard')
    print('Use the same private device key as DEVICE_KEY in your ESP32 config.h.')
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
    print('For the ESP32, use your computer LAN IPv4 address, not localhost.')
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
