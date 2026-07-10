import sqlite3
import os
from datetime import datetime
from flask import Flask, request, jsonify, render_template, redirect, session
from functools import wraps

app = Flask(__name__)
app.secret_key = os.urandom(24).hex()

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'worldcup.db')

# ---------- Database ----------

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                q1 TEXT NOT NULL,
                q2 TEXT NOT NULL,
                q3 TEXT NOT NULL,
                submitted_at TEXT NOT NULL,
                ip_address TEXT
            )
        ''')

init_db()

# ---------- Auth (simple password for admin) ----------

ADMIN_PASSWORD = 'worldcup2026'

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect('/admin/login')
        return f(*args, **kwargs)
    return decorated

# ---------- Routes ----------

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin/login')
def admin_login():
    return render_template('admin_login.html')

@app.route('/admin/do_login', methods=['POST'])
def do_login():
    pwd = request.form.get('password', '')
    if pwd == ADMIN_PASSWORD:
        session['admin_logged_in'] = True
        return redirect('/admin')
    return render_template('admin_login.html', error='密码错误')

@app.route('/admin/logout')
def logout():
    session.pop('admin_logged_in', None)
    return redirect('/admin/login')

@app.route('/admin')
@login_required
def admin():
    return render_template('admin.html')

# ---------- API ----------

@app.route('/api/submit', methods=['POST'])
def submit():
    data = request.get_json()
    q1 = data.get('q1', '').strip()
    q2 = data.get('q2', '').strip()
    q3 = data.get('q3', '').strip()

    if q1 not in ('是', '否') or q2 not in ('是', '否') or q3 not in ('是', '否'):
        return jsonify({'ok': False, 'error': '请完整填写所有题目'}), 400

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    ip = request.remote_addr or ''

    with get_db() as conn:
        conn.execute(
            'INSERT INTO submissions (q1, q2, q3, submitted_at, ip_address) VALUES (?, ?, ?, ?, ?)',
            (q1, q2, q3, now, ip)
        )

    return jsonify({'ok': True})

@app.route('/api/results')
@login_required
def results():
    with get_db() as conn:
        rows = conn.execute('SELECT * FROM submissions ORDER BY id DESC').fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/api/stats')
@login_required
def stats():
    with get_db() as conn:
        total = conn.execute('SELECT COUNT(*) as c FROM submissions').fetchone()['c']
        q1_yes = conn.execute("SELECT COUNT(*) as c FROM submissions WHERE q1='是'").fetchone()['c']
        q2_yes = conn.execute("SELECT COUNT(*) as c FROM submissions WHERE q2='是'").fetchone()['c']
        q3_yes = conn.execute("SELECT COUNT(*) as c FROM submissions WHERE q3='是'").fetchone()['c']
    return jsonify({
        'total': total,
        'q1_yes': q1_yes,
        'q2_yes': q2_yes,
        'q3_yes': q3_yes,
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8800, debug=False, use_reloader=False)
