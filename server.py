#!/usr/bin/env python3
"""Smart Agric local telemetry server. Python 3.10+, no dependencies."""
import argparse
import hmac
import json
import math
import os
from pathlib import Path
import sqlite3
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

ROOT = Path(__file__).resolve().parent
LIMITS = ((0, 100), (-40, 125), (-40, 125), (0, 100))
FIELDS = ('soil_moisture', 'soil_temperature', 'air_temperature', 'humidity')


def validate_sample(data):
    values = []
    for field, (low, high) in zip(FIELDS, LIMITS):
        value = data.get(field)
        if field == 'soil_temperature' and value is None:
            values.append(None)
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
            raise ValueError(f'{field} must be a finite number from {low} to {high}')
        values.append(float(value))
    if not isinstance(data.get('pump'), bool) or not isinstance(data.get('pump_available'), bool):
        raise ValueError('pump and pump_available must be booleans')
    uptime = data.get('uptime_ms')
    if isinstance(uptime, bool) or not isinstance(uptime, int) or uptime < 0:
        raise ValueError('uptime_ms must be a nonnegative integer')
    return values


class Store:
    def __init__(self, path):
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.lock = threading.Lock()
        self.desired = False  # Restart always requests pump off.
        self.db.execute('CREATE TABLE IF NOT EXISTS readings (id INTEGER PRIMARY KEY, time INTEGER NOT NULL, payload TEXT NOT NULL)')
        self.db.commit()

    def add(self, data):
        validate_sample(data)
        sample = {k: data.get(k) for k in (*FIELDS, 'pump', 'pump_available', 'uptime_ms')}
        sample['time'] = int(time.time() * 1000)  # Server receive time, not sensor timestamp.
        with self.lock:
            self.db.execute('INSERT INTO readings(time,payload) VALUES (?,?)', (sample['time'], json.dumps(sample)))
            self.db.execute('DELETE FROM readings WHERE time < ?', (sample['time'] - 7 * 86400000,))
            self.db.commit()
        return sample

    def latest(self):
        with self.lock:
            row = self.db.execute('SELECT payload FROM readings ORDER BY id DESC LIMIT 1').fetchone()
        return json.loads(row[0]) if row else None

    def history(self, minutes):
        with self.lock:
            rows = self.db.execute('SELECT payload FROM readings WHERE time >= ? ORDER BY id DESC LIMIT 720', (int(time.time()*1000) - minutes * 60000,)).fetchall()
        return [json.loads(row[0]) for row in reversed(rows)]


def handler_for(store, key):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            # Keep tokens and request data out of logs.
            pass

        def reply(self, code, data):
            body = json.dumps(data, allow_nan=False).encode()
            self.send_response(code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def authorized(self):
            # Browser UI is same-origin. ESP32 does not send Origin.
            origin = self.headers.get('Origin')
            if origin and urlparse(origin).netloc != self.headers.get('Host'):
                self.reply(403, {'error': 'Use the dashboard served by this local server.'})
                return False
            supplied = self.headers.get('X-Device-Key', '')
            if not hmac.compare_digest(supplied.encode(), key.encode()):
                self.reply(401, {'error': 'Incorrect local device key.'})
                return False
            return True

        def do_GET(self):
            url = urlparse(self.path)
            if url.path.startswith('/api/'):
                if not self.authorized():
                    return
                if url.path == '/api/status':
                    sample = store.latest()
                    age = (int(time.time()*1000) - sample['time']) if sample else None
                    return self.reply(200, {'sample': sample, 'online': age is not None and 0 <= age <= 15000, 'age_ms': age, 'desired_pump': store.desired})
                if url.path == '/api/history':
                    try:
                        minutes = int(parse_qs(url.query).get('minutes', ['60'])[0])
                        if not 1 <= minutes <= 10080:
                            raise ValueError()
                    except ValueError:
                        return self.reply(400, {'error': 'minutes must be 1–10080'})
                    return self.reply(200, {'samples': store.history(minutes)})
                if url.path == '/api/command':
                    sample = store.latest()
                    fresh = sample and 0 <= int(time.time()*1000)-sample['time'] <= 15000
                    return self.reply(200, {'pump': bool(store.desired and fresh and sample['pump_available'])})
                return self.reply(404, {'error': 'Unknown endpoint'})
            files = {'/': 'index.html', '/index.html': 'index.html', '/app.js': 'app.js', '/charts.js': 'charts.js', '/history.js': 'history.js'}
            filename = files.get(url.path)
            if not filename:
                return self.reply(404, {'error': 'Not found'})
            body = (ROOT / filename).read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8' if filename.endswith('.html') else 'application/javascript; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            if not self.authorized():
                return
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= 4096:
                    raise ValueError('Request body must be 1–4096 bytes')
                data = json.loads(self.rfile.read(size))
                if not isinstance(data, dict):
                    raise ValueError('Expected a JSON object')
                if self.path == '/api/telemetry':
                    return self.reply(200, {'sample': store.add(data)})
                if self.path == '/api/pump':
                    if not isinstance(data.get('pump'), bool):
                        raise ValueError('pump must be a boolean')
                    latest = store.latest()
                    if data['pump'] and (not latest or not latest['pump_available'] or not 0 <= int(time.time()*1000)-latest['time'] <= 15000):
                        return self.reply(409, {'error': 'Pump unavailable or telemetry is stale.'})
                    store.desired = data['pump']
                    return self.reply(200, {'desired_pump': store.desired})
                return self.reply(404, {'error': 'Unknown endpoint'})
            except (ValueError, TypeError) as exc:
                return self.reply(400, {'error': str(exc)})
    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--open-browser', action='store_true', help='Open the local dashboard after binding the server')
    args = parser.parse_args()
    key = os.environ.get('ESP32_DEVICE_KEY', '')
    if len(key) < 16:
        parser.error('Set ESP32_DEVICE_KEY to a private random key of at least 16 characters.')
    data_dir = ROOT / 'data'
    data_dir.mkdir(exist_ok=True)
    store = Store(data_dir / 'telemetry.sqlite3')
    server = ThreadingHTTPServer((args.host, args.port), handler_for(store, key))
    print(f'Smart Agric listening on http://{args.host}:{args.port}. Ctrl+C to stop.', flush=True)
    print('For ESP32 access use --host 0.0.0.0 and the computer’s LAN IPv4 address.', flush=True)
    from discovery import DiscoveryAnnouncer
    discovery = DiscoveryAnnouncer(server.server_port)
    if args.host in ('0.0.0.0', ''):
        discovery.start()
    else:
        print('LAN discovery is off for loopback-only binding. Use --host 0.0.0.0 for ESP32 access.', flush=True)
    browser_timer = None
    if args.open_browser:
        import webbrowser
        def open_dashboard():
            try:
                webbrowser.open(f'http://localhost:{server.server_port}')
            except Exception:
                print('Open the dashboard URL manually in your browser.', flush=True)
        browser_timer = threading.Timer(0.5, open_dashboard)
        browser_timer.daemon = True
        browser_timer.start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        if browser_timer:
            browser_timer.cancel()
        discovery.stop()
        server.server_close()
        store.db.close()


if __name__ == '__main__':
    main()
