import sqlite3
import streamlit as st
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

app.secret_key = 'super_secret_system_key' # Change this to a random string

def get_db_connection():
    conn = sqlite3.connect('students.db')
    conn.row_factory = sqlite3.Row
    return conn

# Database Initialization
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Tables
    cursor.execute('''CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, email TEXT UNIQUE, phone TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS courses (
        id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE, name TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS results (
        id INTEGER PRIMARY KEY AUTOINCREMENT, student_id INTEGER, course_id INTEGER, grade TEXT,
        FOREIGN KEY(student_id) REFERENCES students(id), FOREIGN KEY(course_id) REFERENCES courses(id))''')
    
    # Create default admin (User: admin, Pass: admin123) if none exists
    cursor.execute("SELECT * FROM admins WHERE username='admin'")
    if not cursor.fetchone():
        hashed_pw = generate_password_hash('admin123')
        cursor.execute("INSERT INTO admins (username, password) VALUES (?, ?)", ('admin', hashed_pw))
        
    conn.commit()
    conn.close()

init_db()

# Middleware to protect routes
@app.before_request
def require_login():
    allowed_routes = ['login', 'static']
    if 'admin' not in session and request.endpoint not in allowed_routes:
        return redirect(url_for('login'))

@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        admin = conn.execute('SELECT * FROM admins WHERE username = ?', (username,)).fetchone()
        conn.close()
        
        if admin and check_password_hash(admin['password'], password):
            session['admin'] = admin['username']
            return redirect(url_for('dashboard'))
        flash('Invalid username or password!')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('login'))

# --- STUDENT MANAGEMENT ---
@app.route('/students', methods=['GET', 'POST'])
def students():
    conn = get_db_connection()
    search_query = request.args.get('search', '')
    
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        try:
            conn.execute('INSERT INTO students (name, email, phone) VALUES (?, ?, ?)', (name, email, phone))
            conn.commit()
        except sqlite3.IntegrityError:
            flash('Email already registered!')

    if search_query:
        students_list = conn.execute('SELECT * FROM students WHERE name LIKE ? OR email LIKE ?', 
                                     (f'%{search_query}%', f'%{search_query}%')).fetchall()
    else:
        students_list = conn.execute('SELECT * FROM students').fetchall()
        
    conn.close()
    return render_template('students.html', students=students_list, search=search_query)

# --- COURSE MANAGEMENT ---
@app.route('/courses', methods=['GET', 'POST'])
def courses():
    conn = get_db_connection()
    if request.method == 'POST':
        code = request.form['code']
        name = request.form['name']
        try:
            conn.execute('INSERT INTO courses (code, name) VALUES (?, ?)', (code, name))
            conn.commit()
        except sqlite3.IntegrityError:
            flash('Course Code already exists!')
            
    courses_list = conn.execute('SELECT * FROM courses').fetchall()
    conn.close()
    return render_template('courses.html', courses=courses_list)

# --- RESULTS MANAGEMENT ---
@app.route('/results', methods=['GET', 'POST'])
def results():
    conn = get_db_connection()
    if request.method == 'POST':
        student_id = request.form['student_id']
        course_id = request.form['course_id']
        grade = request.form['grade']
        
        # Check if record exists to update, else insert new
        existing = conn.execute('SELECT id FROM results WHERE student_id = ? AND course_id = ?', (student_id, course_id)).fetchone()
        if existing:
            conn.execute('UPDATE results SET grade = ? WHERE id = ?', (grade, existing['id']))
        else:
            conn.execute('INSERT INTO results (student_id, course_id, grade) VALUES (?, ?, ?)', (student_id, course_id, grade))
        conn.commit()

    results_list = conn.execute('''
        SELECT r.id, s.name as student_name, c.name as course_name, r.grade 
        FROM results r 
        JOIN students s ON r.student_id = s.id 
        JOIN courses c ON r.course_id = c.id
    ''').fetchall()
    
    students_list = conn.execute('SELECT id, name FROM students').fetchall()
    courses_list = conn.execute('SELECT id, name FROM courses').fetchall()
    conn.close()
    
    return render_template('results.html', results=results_list, students=students_list, courses=courses_list)

if __name__ == "__main__":
    app.run(debug=True)
