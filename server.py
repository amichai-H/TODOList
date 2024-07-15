from flask import Flask, request, jsonify, session, render_template, redirect, url_for
from flask_session import Session
import sqlite3
import hashlib

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

database = "user_management.db"


def create_connection():
    conn = sqlite3.connect(database)
    return conn


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def create_table():
    conn = create_connection()
    create_users_table_sql = """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL
    );
    """
    create_data_table_sql = """
    CREATE TABLE IF NOT EXISTS user_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        data TEXT NOT NULL,
        done INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES users (id)
    );
    """
    with conn:
        cur = conn.cursor()
        cur.execute(create_users_table_sql)
        cur.execute(create_data_table_sql)


create_table()


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        conn = create_connection()
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        sql = ''' INSERT INTO users(username, password)
                  VALUES(?, ?) '''
        try:
            cur = conn.cursor()
            cur.execute(sql, (username, hash_password(password)))
            conn.commit()
            return jsonify({"message": "User registered successfully."}), 201
        except sqlite3.IntegrityError:
            return jsonify({"message": "Error: Username already exists."}), 400
    else:
        return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        conn = create_connection()
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        sql = ''' SELECT id FROM users WHERE username=? AND password=? '''
        cur = conn.cursor()
        cur.execute(sql, (username, hash_password(password)))
        row = cur.fetchone()
        if row:
            session['user_id'] = row[0]
            return jsonify({"message": "Login successful."}), 200
        else:
            return jsonify({"message": "Login failed."}), 401
    else:
        return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('home'))


# @app.route('/list', methods=['GET', 'POST'])
# def user_list():
#     if 'user_id' not in session:
#         return redirect(url_for('login'))
#
#     conn = create_connection()
#     user_id = session['user_id']
#
#     if request.method == 'POST':
#         data = request.get_json()
#         item = data.get('item')
#         sql = ''' INSERT INTO user_data(user_id, data, done) VALUES(?, ?, 0) '''
#         cur = conn.cursor()
#         cur.execute(sql, (user_id, item))
#         conn.commit()
#         return jsonify({"message": "Item added."}), 201
#
#     elif request.method == 'GET':
#         sql = ''' SELECT id, data, done FROM user_data WHERE user_id=? '''
#         cur = conn.cursor()
#         cur.execute(sql, (user_id,))
#         rows = cur.fetchall()
#         if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
#             return jsonify([{"id": row[0], "item": row[1], "done": row[2]} for row in rows])
#         else:
#             return render_template('list.html', items=[{"id": row[0], "item": row[1], "done": row[2]} for row in rows])
@app.route('/list', methods=['GET', 'POST'])
def user_list():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = create_connection()
    user_id = session['user_id']

    if request.method == 'POST':
        data = request.get_json()
        item = data.get('item')
        sql = ''' INSERT INTO user_data(user_id, data) VALUES(?, ?) '''
        cur = conn.cursor()
        cur.execute(sql, (user_id, item))
        conn.commit()
        return jsonify({"message": "Item added."}), 201

    elif request.method == 'GET':
        sql = ''' SELECT id, data, done FROM user_data WHERE user_id=? '''
        cur = conn.cursor()
        cur.execute(sql, (user_id,))
        rows = cur.fetchall()
        items = [{"id": row[0], "item": row[1], "done": row[2]} for row in rows]
        return render_template('list.html', items=items)
    else:
        return render_template('list.html')


@app.route('/list/<int:item_id>', methods=['PUT', 'DELETE'])
def mark_done(item_id):
    if 'user_id' not in session:
        return jsonify({"message": "Unauthorized"}), 401

    conn = create_connection()
    user_id = session['user_id']

    if request.method == 'PUT':
        data = request.get_json()
        done = data.get('done', False)
        sql = ''' UPDATE user_data SET done = ? WHERE id = ? AND user_id = ? '''
        cur = conn.cursor()
        cur.execute(sql, (done, item_id, user_id))
        conn.commit()

        if cur.rowcount == 0:
            return jsonify({"message": "Item not found or not authorized."}), 404

        return jsonify({"message": "Item updated."}), 200

    elif request.method == 'DELETE':
        sql = ''' DELETE FROM user_data WHERE id = ? AND user_id = ? '''
        cur = conn.cursor()
        cur.execute(sql, (item_id, user_id))
        conn.commit()

        if cur.rowcount == 0:
            return jsonify({"message": "Item not found or not authorized."}), 404

        return jsonify({"message": "Item removed successfully."}), 200


if __name__ == '__main__':
    app.run(debug=True)
