import csv
import io
import os
import re
import secrets
import sqlite3
from datetime import date, datetime, timedelta
from functools import wraps
from pathlib import Path
from flask import Flask, Response, abort, g, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

BASE = Path(__file__).resolve().parent
app = Flask(__name__)
app.config.update(SECRET_KEY=os.environ.get('SECRET_KEY', secrets.token_hex(32)), DATABASE=os.environ.get('DATABASE_PATH', str(BASE / 'finance.db')), SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax', SESSION_COOKIE_SECURE=os.environ.get('COOKIE_SECURE', '0') == '1', MAX_CONTENT_LENGTH=1024 * 1024)
CATEGORIES = ('Food', 'Transport', 'Shopping', 'Bills', 'Salary', 'Other')


def db():
    if 'db' not in g:
        path = Path(app.config['DATABASE'])
        path.parent.mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(path, timeout=10)
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA foreign_keys=ON')
    return g.db


@app.teardown_appcontext
def close_db(error):
    conn = g.pop('db', None)
    if conn is not None:
        conn.close()


def init_db():
    conn = db()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, email TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, description TEXT NOT NULL, amount INTEGER NOT NULL, type TEXT NOT NULL, category TEXT NOT NULL, date TEXT NOT NULL DEFAULT CURRENT_DATE, user_id INTEGER REFERENCES users(id));
        CREATE TABLE IF NOT EXISTS budgets (id INTEGER PRIMARY KEY, user_id INTEGER REFERENCES users(id), month TEXT NOT NULL, category TEXT NOT NULL, amount INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS savings_goals (id INTEGER PRIMARY KEY, user_id INTEGER REFERENCES users(id), name TEXT NOT NULL, target INTEGER NOT NULL, saved INTEGER NOT NULL DEFAULT 0);
    ''')
    # Preserve legacy Phase 1-4 data; it stays unassigned until explicitly imported.
    for table, fields in {'transactions': {'date': "TEXT", 'user_id': 'INTEGER'}, 'budgets': {'user_id': 'INTEGER'}, 'savings_goals': {'user_id': 'INTEGER'}}.items():
        existing = {r['name'] for r in conn.execute(f'PRAGMA table_info({table})')}
        for field, kind in fields.items():
            if field not in existing:
                conn.execute(f'ALTER TABLE {table} ADD COLUMN {field} {kind}')
    conn.execute("UPDATE transactions SET date=? WHERE date IS NULL OR date=''", (date.today().isoformat(),))
    conn.execute('CREATE UNIQUE INDEX IF NOT EXISTS unique_user_budget ON budgets(user_id, month, category)')
    conn.commit()


@app.before_request
def prepare():
    init_db()
    if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
        if request.headers.get('X-CSRF-Token') != session.get('csrf'):
            return jsonify(error='Invalid security token; refresh and try again'), 403


def login_required(fn):
    @wraps(fn)
    def inner(*args, **kwargs):
        if not session.get('uid'):
            return jsonify(error='Please log in'), 401
        return fn(*args, **kwargs)
    return inner


def body():
    return request.get_json(silent=True) or {}


def positive_pence(value):
    # Frontend sends integer pence, never floating-point pounds.
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0 or value > 10**12:
        raise ValueError('Amount must be positive integer pence')
    return value


def valid_month(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])', value):
        raise ValueError('Month must be YYYY-MM')
    return value


def valid_date(value):
    if not isinstance(value, str):
        raise ValueError('Invalid date')
    return date.fromisoformat(value).isoformat()


def error_response(exc):
    return jsonify(error=str(exc)), 400


@app.get('/')
def home():
    if 'csrf' not in session:
        session['csrf'] = secrets.token_urlsafe(32)
    return render_template('index.html', csrf=session['csrf'])


@app.get('/api/me')
def me():
    user = db().execute('SELECT id,email FROM users WHERE id=?', (session.get('uid'),)).fetchone() if session.get('uid') else None
    return jsonify(dict(user) if user else None)


@app.post('/api/register')
def register():
    data = body()
    email = str(data.get('email', '')).strip().lower()
    password = data.get('password', '')
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email) or not isinstance(password, str) or len(password) < 12 or len(password) > 128:
        return jsonify(error='Enter a valid email and a password of 12–128 characters'), 400
    try:
        cur = db().execute('INSERT INTO users(email,password_hash) VALUES (?,?)', (email, generate_password_hash(password)))
        db().commit()
    except sqlite3.IntegrityError:
        return jsonify(error='Account already exists'), 409
    session.clear()
    session['uid'] = cur.lastrowid
    session['csrf'] = secrets.token_urlsafe(32)
    return jsonify(email=email, csrf=session['csrf']), 201


@app.post('/api/login')
def login():
    data = body()
    email = str(data.get('email', '')).strip().lower()
    user = db().execute('SELECT * FROM users WHERE email=?', (email,)).fetchone()
    if not user or not check_password_hash(user['password_hash'], str(data.get('password', ''))):
        return jsonify(error='Incorrect email or password'), 401
    session.clear()
    session['uid'] = user['id']
    session['csrf'] = secrets.token_urlsafe(32)
    return jsonify(email=email, csrf=session['csrf'])


@app.post('/api/logout')
def logout():
    session.clear()
    session['csrf'] = secrets.token_urlsafe(32)
    return jsonify(csrf=session['csrf'])


@app.get('/api/transactions')
@login_required
def transactions():
    return jsonify([dict(row) for row in db().execute('SELECT id,description,amount,type,category,date FROM transactions WHERE user_id=? ORDER BY date DESC,id DESC', (session['uid'],))])


@app.post('/api/transactions')
@login_required
def add_transaction():
    data = body()
    try:
        description = str(data.get('description', '')).strip()
        if not 1 <= len(description) <= 150:
            raise ValueError('Description must be 1–150 characters')
        amount = positive_pence(data.get('amount'))
        kind = data.get('type')
        category = data.get('category')
        if kind not in ('income', 'expense') or category not in CATEGORIES:
            raise ValueError('Invalid transaction type or category')
        when = valid_date(data.get('date') or date.today().isoformat())
    except ValueError as exc:
        return error_response(exc)
    cur = db().execute('INSERT INTO transactions(description,amount,type,category,date,user_id) VALUES (?,?,?,?,?,?)', (description, amount, kind, category, when, session['uid']))
    db().commit()
    return jsonify(id=cur.lastrowid), 201


@app.delete('/api/transactions/<int:item_id>')
@login_required
def delete_transaction(item_id):
    cur = db().execute('DELETE FROM transactions WHERE id=? AND user_id=?', (item_id, session['uid']))
    db().commit()
    return (jsonify(ok=True) if cur.rowcount else (jsonify(error='Not found'), 404))


@app.get('/api/budgets')
@login_required
def budgets():
    month = request.args.get('month', date.today().strftime('%Y-%m'))
    try:
        month = valid_month(month)
    except ValueError as exc:
        return error_response(exc)
    rows = db().execute('''SELECT b.id,b.month,b.category,b.amount,COALESCE((SELECT SUM(t.amount) FROM transactions t WHERE t.user_id=b.user_id AND t.type='expense' AND t.category=b.category AND substr(t.date,1,7)=b.month),0) spent FROM budgets b WHERE b.user_id=? AND b.month=? ORDER BY b.category''', (session['uid'], month))
    return jsonify([dict(r) for r in rows])


@app.post('/api/budgets')
@login_required
def add_budget():
    data = body()
    try:
        month = valid_month(data.get('month'))
        category = data.get('category')
        if category not in CATEGORIES:
            raise ValueError('Invalid category')
        amount = positive_pence(data.get('amount'))
    except ValueError as exc:
        return error_response(exc)
    db().execute('INSERT INTO budgets(user_id,month,category,amount) VALUES (?,?,?,?) ON CONFLICT(user_id,month,category) DO UPDATE SET amount=excluded.amount', (session['uid'], month, category, amount))
    db().commit()
    return jsonify(ok=True), 201


@app.delete('/api/budgets/<int:item_id>')
@login_required
def delete_budget(item_id):
    cur = db().execute('DELETE FROM budgets WHERE id=? AND user_id=?', (item_id, session['uid']))
    db().commit()
    return (jsonify(ok=True) if cur.rowcount else (jsonify(error='Not found'), 404))


@app.get('/api/goals')
@login_required
def goals():
    return jsonify([dict(r) for r in db().execute('SELECT id,name,target,saved FROM savings_goals WHERE user_id=? ORDER BY id DESC', (session['uid'],))])


@app.post('/api/goals')
@login_required
def add_goal():
    data = body()
    try:
        name = str(data.get('name', '')).strip()
        if not 1 <= len(name) <= 100:
            raise ValueError('Goal name must be 1–100 characters')
        target = positive_pence(data.get('target'))
    except ValueError as exc:
        return error_response(exc)
    cur = db().execute('INSERT INTO savings_goals(user_id,name,target,saved) VALUES (?,?,?,0)', (session['uid'], name, target))
    db().commit()
    return jsonify(id=cur.lastrowid), 201


@app.post('/api/goals/<int:item_id>/contribute')
@login_required
def contribute(item_id):
    try:
        amount = positive_pence(body().get('amount'))
    except ValueError as exc:
        return error_response(exc)
    cur = db().execute('UPDATE savings_goals SET saved=saved+? WHERE id=? AND user_id=?', (amount, item_id, session['uid']))
    db().commit()
    return (jsonify(ok=True) if cur.rowcount else (jsonify(error='Not found'), 404))


@app.delete('/api/goals/<int:item_id>')
@login_required
def delete_goal(item_id):
    cur = db().execute('DELETE FROM savings_goals WHERE id=? AND user_id=?', (item_id, session['uid']))
    db().commit()
    return (jsonify(ok=True) if cur.rowcount else (jsonify(error='Not found'), 404))


@app.get('/api/insights')
@login_required
def insights():
    month = request.args.get('month', date.today().strftime('%Y-%m'))
    try:
        month = valid_month(month)
    except ValueError as exc:
        return error_response(exc)
    previous = (date.fromisoformat(month + '-01') - timedelta(days=1)).strftime('%Y-%m')
    rows = [dict(r) for r in db().execute('SELECT amount,type,category,date FROM transactions WHERE user_id=?', (session['uid'],))]
    current = [r for r in rows if r['date'] and r['date'].startswith(month)]
    prior = [r for r in rows if r['date'] and r['date'].startswith(previous)]
    income = sum(r['amount'] for r in current if r['type'] == 'income')
    expense = sum(r['amount'] for r in current if r['type'] == 'expense')
    old_expense = sum(r['amount'] for r in prior if r['type'] == 'expense')
    by_category = {}
    for r in current:
        if r['type'] == 'expense':
            by_category[r['category']] = by_category.get(r['category'], 0) + r['amount']
    largest = max(by_category, key=by_category.get) if by_category else None
    budget_rows = [dict(r) for r in db().execute('SELECT category,amount FROM budgets WHERE user_id=? AND month=?', (session['uid'], month))]
    alerts = [{'category': b['category'], 'spent': by_category.get(b['category'], 0), 'limit': b['amount']} for b in budget_rows if by_category.get(b['category'], 0) >= b['amount'] * 0.8]
    goals_data = [dict(r) for r in db().execute('SELECT name,target,saved FROM savings_goals WHERE user_id=?', (session['uid'],))]
    return jsonify(month=month, income=income, expenses=expense, net=income-expense, largest_category=largest, largest_amount=by_category.get(largest, 0) if largest else 0, previous_expenses=old_expense, comparison_percent=round((expense-old_expense)/old_expense*100, 1) if old_expense else None, budget_alerts=alerts, goals=goals_data, has_prior_data=bool(prior))


@app.get('/api/export.csv')
@login_required
def export_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Date', 'Description', 'Type', 'Category', 'Amount GBP'])
    for r in db().execute('SELECT date,description,type,category,amount FROM transactions WHERE user_id=? ORDER BY date DESC,id DESC', (session['uid'],)):
        # Prevent spreadsheet formula injection in user-controlled text fields.
        safe = lambda s: "'" + s if s and s.lstrip().startswith(('=', '+', '-', '@', '\t', '\r')) else s
        writer.writerow([r['date'], safe(r['description']), r['type'], safe(r['category']), f"{r['amount']/100:.2f}"])
    return Response('\ufeff' + output.getvalue(), mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename="fintrack-transactions.csv"'})


@app.get('/api/health')
def health():
    return jsonify(status='ok')


@app.cli.command('claim-legacy')
def claim_legacy():
    """Explicitly assign old, unowned records to a chosen existing account. Run locally only."""
    email = input('Account email to receive old data: ').strip().lower()
    user = db().execute('SELECT id FROM users WHERE email=?', (email,)).fetchone()
    if not user:
        print('No such account. Register first.'); return
    for table in ('transactions', 'budgets', 'savings_goals'):
        count = db().execute(f'SELECT COUNT(*) FROM {table} WHERE user_id IS NULL').fetchone()[0]
        print(f'{table}: {count} unassigned records')
    if input('Type CLAIM to assign all unassigned records to this account: ') != 'CLAIM':
        print('Cancelled'); return
    for table in ('transactions', 'budgets', 'savings_goals'):
        db().execute(f'UPDATE {table} SET user_id=? WHERE user_id IS NULL', (user['id'],))
    db().commit()
    print('Legacy records assigned.')


if __name__ == '__main__':
    app.run(debug=os.environ.get('FLASK_DEBUG') == '1', port=int(os.environ.get('PORT', '5000')))
