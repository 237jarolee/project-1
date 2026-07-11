import streamlit as st
import sqlite3
import pandas as pd

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('sms_data.db')
    c = conn.cursor()
    # Students table
    c.execute('''CREATE TABLE IF NOT EXISTS students 
                 (id INTEGER PRIMARY KEY, name TEXT, email TEXT, phone TEXT)''')
    # Courses table
    c.execute('''CREATE TABLE IF NOT EXISTS courses 
                 (id INTEGER PRIMARY KEY, course_name TEXT, credits INTEGER)''')
    # Results table
    c.execute('''CREATE TABLE IF NOT EXISTS results 
                 (student_id INTEGER, course_id INTEGER, grade TEXT,
                 FOREIGN KEY(student_id) REFERENCES students(id),
                 FOREIGN KEY(course_id) REFERENCES courses(id))''')
    # Admin table
    c.execute('''CREATE TABLE IF NOT EXISTS admins (username TEXT, password TEXT)''')
    # Default admin
    c.execute("INSERT OR IGNORE INTO admins VALUES ('admin', 'admin123')")
    conn.commit()
    conn.close()

def run_query(query, params=(), fetch=False):
    with sqlite3.connect('sms_data.db') as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        if fetch:
            return cursor.fetchall()
        conn.commit()

# --- APP LAYOUT ---
st.set_page_config(page_title="INVESTOR Student System", layout="wide")
init_db()

# Session state for login
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

# --- LOGIN SYSTEM ---
if not st.session_state['logged_in']:
    st.title("🔐 Admin Login")
    user = st.text_input("Username")
    pw = st.text_input("Password", type="password")
    if st.button("Login"):
        res = run_query("SELECT * FROM admins WHERE username=? AND password=?", (user, pw), True)
        if res:
            st.session_state['logged_in'] = True
            st.rerun()
        else:
            st.error("Invalid credentials")
else:
    # --- MAIN APPLICATION ---
    st.sidebar.title("Navigation")
    menu = ["Register Student", "Manage Courses", "Record Results", "Search Records", "Logout"]
    choice = st.sidebar.selectbox("Go to", menu)

    if choice == "Logout":
        st.session_state['logged_in'] = False
        st.rerun()

    # 1. Register Students
    elif choice == "Register Student":
        st.header("📝 Register New Student")
        with st.form("reg_form"):
            name = st.text_input("Full Name")
            email = st.text_input("Email")
            phone = st.text_input("Phone Number")
            if st.form_submit_button("Add Student"):
                run_query("INSERT INTO students (name, email, phone) VALUES (?,?,?)", (name, email, phone))
                st.success(f"Student {name} registered successfully!")

    # 2. Manage Courses
    elif choice == "Manage Courses":
        st.header("📚 Course Management")
        with st.form("course_form"):
            c_name = st.text_input("Course Name")
            credits = st.number_input("Credits", 1, 5)
            if st.form_submit_button("Add Course"):
                run_query("INSERT INTO courses (course_name, credits) VALUES (?,?)", (c_name, credits))
        
        st.subheader("Existing Courses")
        courses = run_query("SELECT * FROM courses", fetch=True)
        st.table(pd.DataFrame(courses, columns=["ID", "Name", "Credits"]))

    # 3. Record Results
    elif choice == "Record Results":
        st.header("📊 Student Results")
        students = run_query("SELECT id, name FROM students", fetch=True)
        courses = run_query("SELECT id, course_name FROM courses", fetch=True)
        
        if students and courses:
            with st.form("result_form"):
                stu = st.selectbox("Select Student", students, format_func=lambda x: x[1])
                cou = st.selectbox("Select Course", courses, format_func=lambda x: x[1])
                grade = st.selectbox("Grade", ["A", "B", "C", "D", "F"])
                if st.form_submit_button("Save Result"):
                    run_query("INSERT INTO results VALUES (?,?,?)", (stu[0], cou[0], grade))
                    st.success("Result recorded!")
        else:
            st.warning("Please ensure students and courses are registered first.")

    # 4. Search Records
    elif choice == "Search Records":
        st.header("🔍 Search Student Records")
        search_term = st.text_input("Enter Student Name")
        if search_term:
            query = """
            SELECT s.name, c.course_name, r.grade 
            FROM students s
            JOIN results r ON s.id = r.student_id
            JOIN courses c ON r.course_id = c.id
            WHERE s.name LIKE ?
            """
            results = run_query(query, ('%' + search_term + '%',), True)
            if results:
                st.table(pd.DataFrame(results, columns=["Student", "Course", "Grade"]))
            else:
                st.info("No records found.")
