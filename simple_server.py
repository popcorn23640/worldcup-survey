#!/usr/bin/env python3
"""Lightweight survey server using only Python stdlib — no Flask/Werkzeug needed."""

import json
import os
import sqlite3
import urllib.parse
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from http import cookies

DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DIR, 'worldcup.db')
TEMPLATES_DIR = os.path.join(DIR, 'templates')
ADMIN_PASSWORD = 'worldcup2026'

# ---------- Database ----------
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                q1 TEXT NOT NULL,
                q2 TEXT NOT NULL,
                q3 TEXT NOT NULL,
                submitted_at TEXT NOT NULL,
                ip_address TEXT,
                notes TEXT DEFAULT ''
            )
        ''')
        # Migrate existing databases that don't have notes column yet
        try:
            conn.execute('ALTER TABLE submissions ADD COLUMN notes TEXT DEFAULT \'\'')
        except sqlite3.OperationalError:
            pass  # Column already exists
init_db()

# ---------- Auth helpers ----------
SESSION_STORE = {}

def make_session_id():
    import hashlib, time
    raw = f'{time.time()}{os.urandom(8).hex()}'
    return hashlib.sha256(raw.encode()).hexdigest()[:32]

# ---------- HTTP Handler ----------
class SurveyHandler(BaseHTTPRequestHandler):

    def _send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html, status=200):
        body = html.encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_static(self, filename):
        path = os.path.join(TEMPLATES_DIR, filename)
        if not os.path.exists(path) or not os.path.isfile(path):
            self.send_error(404)
            return
        with open(path, 'rb') as f:
            content = f.read()
        self.send_response(200)
        if filename.endswith('.html'):
            self.send_header('Content-Type', 'text/html; charset=utf-8')
        elif filename.endswith('.js'):
            self.send_header('Content-Type', 'application/javascript; charset=utf-8')
        elif filename.endswith('.css'):
            self.send_header('Content-Type', 'text/css; charset=utf-8')
        self.send_header('Content-Length', str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _read_body(self):
        length = int(self.headers.get('Content-Length', '0'))
        if length == 0:
            return b''
        return self.rfile.read(length)

    def _parse_cookies(self):
        c = cookies.SimpleCookie()
        raw = self.headers.get('Cookie', '')
        c.load(raw)
        return c

    def _check_auth(self):
        c = self._parse_cookies()
        if 'session_id' not in c:
            return False
        sid = c['session_id'].value
        return sid in SESSION_STORE and SESSION_STORE[sid].get('role') == 'admin'

    def log_message(self, format, *args):
        pass  # quieter logs

    # ---------- Routes ----------
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == '/':
            self._serve_static('index.html')
        elif path == '/admin/login':
            self._serve_static('admin_login.html')
        elif path == '/admin':
            if not self._check_auth():
                self.send_response(302)
                self.send_header('Location', '/admin/login?r=1')
                self.end_headers()
                return
            self._serve_static('admin.html')
        elif path == '/admin/logout':
            c = self._parse_cookies()
            if 'session_id' in c:
                SESSION_STORE.pop(c['session_id'].value, None)
            self.send_response(302)
            self.send_header('Set-Cookie', 'session_id=; Path=/; Max-Age=0')
            self.send_header('Location', '/admin/login')
            self.end_headers()
        elif path == '/api/stats':
            if not self._check_auth():
                self._send_json({'error': 'unauthorized'}, 401)
                return
            with sqlite3.connect(DB_PATH) as conn:
                conn.row_factory = sqlite3.Row
                total = conn.execute('SELECT COUNT(*) as c FROM submissions').fetchone()['c']
                q1_yes = conn.execute("SELECT COUNT(*) as c FROM submissions WHERE q1='是'").fetchone()['c']
                q2_yes = conn.execute("SELECT COUNT(*) as c FROM submissions WHERE q2='是'").fetchone()['c']
                q3_yes = conn.execute("SELECT COUNT(*) as c FROM submissions WHERE q3='是'").fetchone()['c']
            self._send_json({'total': total, 'q1_yes': q1_yes, 'q2_yes': q2_yes, 'q3_yes': q3_yes})
        elif path == '/api/results':
            if not self._check_auth():
                self._send_json({'error': 'unauthorized'}, 401)
                return
            with sqlite3.connect(DB_PATH) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute('SELECT * FROM submissions ORDER BY id DESC').fetchall()
            self._send_json([dict(r) for r in rows])
        else:
            self.send_error(404)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == '/admin/do_login':
            body = self._read_body().decode('utf-8')
            params = urllib.parse.parse_qs(body)
            pwd = params.get('password', [''])[0]
            if pwd == ADMIN_PASSWORD:
                sid = make_session_id()
                SESSION_STORE[sid] = {'role': 'admin'}
                self.send_response(302)
                self.send_header('Set-Cookie', f'session_id={sid}; Path=/; HttpOnly')
                self.send_header('Location', '/admin')
                self.end_headers()
            else:
                self._send_html(
                    '<!DOCTYPE html>'
                    '<html lang=zh-CN>'
                    '<head><meta charset=utf-8>'
                    '<meta name=viewport content="width=device-width,initial-scale=1">'
                    '<title>登录失败</title>'
                    '<style>'
                    'body{background:#0f1a2e;color:#fff;font-family:sans-serif;'
                    'display:flex;align-items:center;justify-content:center;'
                    'min-height:100vh;padding:20px}'
                    '.box{background:#1a2a44;border-radius:16px;padding:36px 28px;'
                    'max-width:360px;width:100%;text-align:center}'
                    '.box h1{font-size:20px;margin-bottom:16px}'
                    '.box .error{color:#ff5252;margin-bottom:16px}'
                    '.box a{color:#00c853}'
                    '</style>'
                    '</head><body>'
                    '<div class=box>'
                    '<h1>🔐 管理后台登录</h1>'
                    '<div class=error>密码错误</div>'
                    '<a href=/admin/login>重新登录</a>'
                    '</div></body></html>'
                )

        elif path == '/api/submit':
            body = self._read_body().decode('utf-8')
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                self._send_json({'ok': False, 'error': '无效的请求数据'}, 400)
                return

            q1 = data.get('q1', '').strip()
            q2 = data.get('q2', '').strip()
            q3 = data.get('q3', '').strip()
            notes = data.get('notes', '').strip()

            if q1 not in ('是', '否') or q2 not in ('是', '否') or q3 not in ('是', '否'):
                self._send_json({'ok': False, 'error': '请完整填写所有题目'}, 400)
                return

            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ip = self.client_address[0]

            with sqlite3.connect(DB_PATH) as conn:
                conn.execute(
                    'INSERT INTO submissions (q1, q2, q3, submitted_at, ip_address, notes) VALUES (?, ?, ?, ?, ?, ?)',
                    (q1, q2, q3, now, ip, notes)
                )

            self._send_json({'ok': True})

        else:
            self.send_error(404)


if __name__ == '__main__':
    port = 8802
    server = HTTPServer(('0.0.0.0', port), SurveyHandler)
    print(f'Server running on http://0.0.0.0:{port}')
    print(f'         http://127.0.0.1:{port}')
    print(f'         http://localhost:{port}')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
