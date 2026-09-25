import sqlite3
import hashlib
import secrets
from datetime import datetime

DATABASE_NAME = "cleantrack.db"

def hash_password(password):
    salt = secrets.token_hex(16)
    password_hash = hashlib.sha256(
        (salt + password).encode("utf-8")
    ).hexdigest()
    return salt + ":" + password_hash

def get_connection():
    return sqlite3.connect(DATABASE_NAME)

def initialize_database():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'resident'
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            location TEXT NOT NULL,
            problem TEXT NOT NULL,
            description TEXT NOT NULL,
            priority TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pending',
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    connection.commit()
    connection.close()

def register_user(name, email, password):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        password_hash = hash_password(password)

        cursor.execute("""
            INSERT INTO users (name, email, password)
            VALUES (?, ?, ?)
        """, (name, email, password_hash))

        connection.commit()

        return True

    except sqlite3.IntegrityError:
        return False

    finally:
        connection.close()

def create_report(
    user_id,
    location,
    problem,
    description,
    priority
):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        created_at = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        cursor.execute("""
            INSERT INTO reports (
                user_id,
                location,
                problem,
                description,
                priority,
                status,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            location,
            problem,
            description,
            priority,
            "Pending",
            created_at
        ))
        connection.commit()
        return True

    finally:
        connection.close()

def get_all_reports():
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT
                reports.id,
                reports.user_id,
                users.name,
                reports.location,
                reports.problem,
                reports.description,
                reports.priority,
                reports.status,
                reports.created_at
            FROM reports
            JOIN users
            ON reports.user_id = users.id
            ORDER BY reports.created_at DESC
        """)

        results = cursor.fetchall()
        reports = []

        for row in results:
            reports.append({
                "id": row[0],
                "user_id": row[1],
                "user_name": row[2],
                "location": row[3],
                "problem": row[4],
                "description": row[5],
                "priority": row[6],
                "status": row[7],
                "created_at": row[8]
            })
        return reports

    finally:
        connection.close()

def get_reports_by_user(user_id):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT
                id,
                location,
                problem,
                description,
                priority,
                status,
                created_at
            FROM reports
            WHERE user_id = ?
            ORDER BY created_at DESC
        """, (user_id,))

        results = cursor.fetchall()
        reports = []

        for row in results:
            reports.append({
                "id": row[0],
                "location": row[1],
                "problem": row[2],
                "description": row[3],
                "priority": row[4],
                "status": row[5],
                "created_at": row[6]
            })
        return reports
    finally:
        connection.close()

def update_report(
    report_id,
    user_id,
    location,
    problem,
    description,
    priority
):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            UPDATE reports
            SET
                location = ?,
                problem = ?,
                description = ?,
                priority = ?
            WHERE id = ?
            AND user_id = ?
        """, (
            location,
            problem,
            description,
            priority,
            report_id,
            user_id
        ))

        connection.commit()
        return cursor.rowcount > 0
    
    finally:
        connection.close()

def get_report_by_id(report_id, user_id):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT
                id,
                location,
                problem,
                description,
                priority,
                status,
                created_at
            FROM reports
            WHERE id = ?
            AND user_id = ?
        """, (report_id, user_id))

        row = cursor.fetchone()

        if row is None:
            return None

        return {
            "id": row[0],
            "location": row[1],
            "problem": row[2],
            "description": row[3],
            "priority": row[4],
            "status": row[5],
            "created_at": row[6]
        }
    finally:
        connection.close()

def update_report(
    report_id,
    user_id,
    location,
    problem,
    description,
    priority
):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            UPDATE reports
            SET
                location = ?,
                problem = ?,
                description = ?,
                priority = ?
            WHERE id = ?
            AND user_id = ?
        """, (
            location,
            problem,
            description,
            priority,
            report_id,
            user_id
        ))

        connection.commit()

        return cursor.rowcount > 0

    finally:
        connection.close()

def delete_report(report_id, user_id):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            DELETE FROM reports
            WHERE id = ?
            AND user_id = ?
        """, (report_id, user_id))

        connection.commit()
        return cursor.rowcount > 0
    finally:
        connection.close()

def update_report_status(report_id, status):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            UPDATE reports
            SET status = ?
            WHERE id = ?
        """, (
            status,
            report_id
        ))
        connection.commit()
        return cursor.rowcount > 0
    finally:
        connection.close()

def filter_reports(location="", status="", priority=""):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        query = """
            SELECT
                reports.id,
                reports.user_id,
                users.name,
                reports.location,
                reports.problem,
                reports.description,
                reports.priority,
                reports.status,
                reports.created_at
            FROM reports
            JOIN users
                ON reports.user_id = users.id
        """

        conditions = []
        parameters = []

        if location:
            conditions.append("reports.location LIKE ?")
            parameters.append("%" + location + "%")

        if status:
            conditions.append("reports.status = ?")
            parameters.append(status)

        if priority:
            conditions.append("reports.priority = ?")
            parameters.append(priority)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += """
            ORDER BY reports.created_at DESC
        """

        cursor.execute(
            query,
            parameters
        )

        rows = cursor.fetchall()
        reports = []

        for row in rows:
            reports.append({
                "id": row[0],
                "user_id": row[1],
                "user_name": row[2],
                "location": row[3],
                "problem": row[4],
                "description": row[5],
                "priority": row[6],
                "status": row[7],
                "created_at": row[8]
            })
        return reports
    finally:
        connection.close()

def get_report_statistics():
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN status = 'Pending' THEN 1 ELSE 0 END) AS pending,
                SUM(CASE WHEN status = 'In Progress' THEN 1 ELSE 0 END) AS in_progress,
                SUM(CASE WHEN status = 'Resolved' THEN 1 ELSE 0 END) AS resolved
            FROM reports
        """)

        result = cursor.fetchone()

        return {
            "total": result[0] or 0,
            "pending": result[1] or 0,
            "in_progress": result[2] or 0,
            "resolved": result[3] or 0
        }

    finally:
        connection.close()

def verify_user(email, password):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT password
            FROM users
            WHERE email = ?
        """, (email,))

        result = cursor.fetchone()

        if result is None:
            return False

        stored_password = result[0]
        salt, stored_hash = stored_password.split(":")

        password_hash = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
        return password_hash == stored_hash
    finally:
        connection.close()

def get_user_by_email(email):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT id, name, email, role
            FROM users
            WHERE email = ?
        """, (email,))

        result = cursor.fetchone()

        if result is None:
            return None

        return {
            "id": result[0],
            "name": result[1],
            "email": result[2],
            "role": result[3]
        }
    finally:
        connection.close()

def add_role_column():
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            ALTER TABLE users
            ADD COLUMN role TEXT NOT NULL DEFAULT 'resident'
        """)

        connection.commit()

    except sqlite3.OperationalError:
        pass
    finally:
        connection.close()

def set_user_role(email, role):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            UPDATE users
            SET role = ?
            WHERE email = ?
        """, (role, email))

        connection.commit()
    finally:
        connection.close()

initialize_database()

register_user(
    "Test User",
    "test@example.com",
    "test123"
)
