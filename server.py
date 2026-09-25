import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import database
import secrets

sessions = {}

class RequestHandler(BaseHTTPRequestHandler):

    def serve_file(self, file_path, content_type):
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.end_headers()

        self.wfile.write(content.encode("utf-8"))

    def serve_binary_file(self, file_path, content_type):
        with open(file_path, "rb") as file:
            content = file.read()

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.end_headers()

        self.wfile.write(content)

    def get_session_email(self):
        cookie_header = self.headers.get("Cookie")
        if not cookie_header:
            return None

        cookies = {}

        for cookie in cookie_header.split(";"):
            name, value = cookie.strip().split("=", 1)
            cookies[name] = value

        session_id = cookies.get("session_id")

        if not session_id:
            return None

        return sessions.get(session_id)

    def do_GET(self):

        if self.path == "/":
            user_email = self.get_session_email()

            with open("pages/index.html", "r", encoding="utf-8") as file:
                html = file.read()

            if user_email:
                nav_links = """
                    <a href="/dashboard">Dashboard</a>
                    <a href="/logout">Logout</a>
                """
            else:
                nav_links = """
                    <a href="/login">Login</a>
                """

            html = html.replace(
                "{{NAV_LINKS}}",
                nav_links
            )

            if user_email:
                html = html.replace(
                    'href="/login" class="button primary-button" id="report-problem-button"',
                    'href="/report" class="button primary-button" id="report-problem-button"'
                )

                html = html.replace(
                    'href="/login" class="button secondary-button" id="report-problem-button"',
                    'href="/dashboard" class="button secondary-button" id="get-started-button"'
                )

            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))

        elif self.path == "/login":
            with open("pages/login.html", "r", encoding="utf-8") as file:
                html = file.read()

            html = html.replace(
                "{{LOGIN_ERROR}}",
                ""
            )

            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()

            self.wfile.write(html.encode("utf-8"))

        elif self.path == "/register":
            self.serve_file("pages/register.html", "text/html")

        elif self.path == "/report":
            self.serve_file("pages/report.html", "text/html")

        elif self.path.startswith("/admin"):
            self.generate_admin_dashboard()

        elif self.path == "/dashboard":
            user_email = self.get_session_email()
            if user_email:
                self.generate_dashboard()
            else:
                self.send_response(302)
                self.send_header("Location", "/login")
                self.end_headers()

        elif self.path == "/logout":
            self.logout_user()

        elif self.path == "/static/css/style.css":
            self.serve_file("static/css/style.css", "text/css")

        elif self.path == "/static/images/hero.jpg":
            self.serve_binary_file("static/images/hero.jpg", "image/jpeg")

        elif self.path.startswith("/edit-report"):
            self.generate_edit_report()

        else:
            self.send_response(404)
            self.send_header("Content-Type", "text/html")
            self.end_headers()

            self.wfile.write(
                b"<h1>404 - Page Not Found</h1>"
            )

    def do_POST(self):
        content_length = int(self.headers["Content-Length"])
        post_data = self.rfile.read(content_length)
        post_data = post_data.decode("utf-8")
        data = parse_qs(post_data)
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        
        if self.path == "/login":
            email = data.get("email", [""])[0]
            password = data.get("password", [""])[0]

            login_success = database.verify_user(
                email,
                password
            )
            if login_success:
                session_id = secrets.token_hex(32)
                sessions[session_id] = email

                self.send_response(302)
                self.send_header("Set-Cookie", f"session_id={session_id}; HttpOnly; Path=/")
                self.send_header("Location", "/dashboard")
                self.end_headers()

            else:
                with open("pages/login.html", "r", encoding="utf-8") as file:
                    html = file.read()

                html = html.replace(
                    "{{LOGIN_ERROR}}",
                     """
                    <div class="login-error" role="alert">
                        Invalid email or password.
                    </div>
                    """
                )

                self.send_response(401)
                self.send_header("Content-Type", "text/html")
                self.end_headers()

                self.wfile.write(html.encode("utf-8"))

        elif path == "/register":
            name = data.get("name", [""])[0]
            email = data.get("email", [""])[0]
            password = data.get("password", [""])[0]

            success = database.register_user(
                name,
                email,
                password
            )

            if success:
                self.send_response(302)
                self.send_header("Location", "/login")
                self.end_headers()

            else:
                self.send_response(400)
                self.send_header("Content-Type", "text/html")
                self.end_headers()

                self.wfile.write(
                    b"<h1>Email already registered.</h1>"
                )

        elif self.path == "/reports":
            user_email = self.get_session_email()
            if not user_email:
                self.send_response(302)
                self.send_header("Location", "/login")
                self.end_headers()
                return

            location = data.get("location", [""])[0]
            problem = data.get("problem", [""])[0]
            description = data.get("description", [""])[0]
            priority = data.get("priority", [""])[0]
            user = database.get_user_by_email(user_email)

            if user is None:
                self.send_response(302)
                self.send_header("Location","/login")
                self.end_headers()
                return

            success = database.create_report(
                user["id"],
                location,
                problem,
                description,
                priority
            )

            if success:
                self.send_response(302)
                self.send_header("Location", "/dashboard")
                self.end_headers()

            else:
                self.send_response(500)
                self.send_header("Content-Type", "text/html")
                self.end_headers()

                self.wfile.write(b"<h1>Something went wrong.</h1>")

        elif path == "/edit-report":
            user_email = self.get_session_email()

            if not user_email:
                self.send_response(302)
                self.send_header("Location", "/login")
                self.end_headers()
                return

            user = database.get_user_by_email(user_email)

            if user is None:
                self.send_response(403)
                self.end_headers()
                return

            report_id = data.get("report_id", [None])[0]
            location = data.get("location", [""])[0]
            problem = data.get("problem", [""])[0]
            description = data.get("description", [""])[0]
            priority = data.get("priority", [""])[0]

            success = database.update_report(
                report_id,
                user["id"],
                location,
                problem,
                description,
                priority
            )

            if success:
                self.send_response(302)
                self.send_header("Location", "/dashboard")
                self.end_headers()

            else:
                self.send_response(404)
                self.send_header("Content-Type", "text/html")
                self.end_headers()

                self.wfile.write(b"<h1>404 - Report not found</h1>")
            return

        elif path == "/delete-report":
            user_email = self.get_session_email()

            if not user_email:
                self.send_response(302)
                self.send_header("Location", "/login")
                self.end_headers()
                return

            user = database.get_user_by_email(user_email)

            if user is None:
                self.send_response(403)
                self.end_headers()
                return

            report_id = data.get("report_id", [None])[0]

            success = database.delete_report(report_id, user["id"])

            if success:
                self.send_response(302)
                self.send_header("Location", "/dashboard")
                self.end_headers()

            else:
                self.send_response(404)
                self.send_header("Content-Type", "text/html")
                self.end_headers()

                self.wfile.write(b"<h1>404 - Report not found</h1>")
            return

        elif path == "/update-status":
            user_email = self.get_session_email()
            if not user_email:
                self.send_response(302)
                self.send_header("Location", "/login")
                self.end_headers()
                return

            user = database.get_user_by_email(user_email)

            if user is None:
                self.send_response(403)
                self.end_headers()
                return

            if user["role"] != "admin":
                self.send_response(403)
                self.send_header("Content-Type", "text/html")
                self.end_headers()

                self.wfile.write(b"<h1>403 - Access Denied</h1>")
                return

            report_id = data.get("report_id", [None])[0]

            status = data.get("status", [None])[0]

            allowed_statuses = ["Pending", "In Progress", "Resolved"]

            if status not in allowed_statuses:
                self.send_response(400)
                self.send_header("Content-Type", "text/html")
                self.end_headers()

                self.wfile.write(b"<h1>400 - Invalid status</h1>")
                return

            success = database.update_report_status(report_id, status)

            if success:
                self.send_response(302)
                self.send_header("Location", "/admin")
                self.end_headers()

            else:
                self.send_response(404)
                self.send_header("Content-Type", "text/html")
                self.end_headers()

                self.wfile.write(b"<h1>404 - Report not found</h1>")
            return

        # UNKNOWN POST REQUEST
        else:
            self.send_response(404)
            self.send_header("Content-Type", "text/html")
            self.end_headers()

            self.wfile.write(b"<h1>404 - Page Not Found</h1>")

    def logout_user(self):
        cookie_header = self.headers.get("Cookie")

        if cookie_header:
            cookies = {}

            for cookie in cookie_header.split(";"):
                name, value = cookie.strip().split("=", 1)
                cookies[name] = value

            session_id = cookies.get("session_id")

            if session_id:
                sessions.pop(session_id, None)

        self.send_response(302)

        self.send_header(
            "Set-Cookie",
            "session_id=; Max-Age=0; HttpOnly; Path=/"
        )
        self.send_header(
            "Location",
            "/login"
        )
        self.end_headers()

    def generate_admin_dashboard(self):
        user_email = self.get_session_email()

        parsed_url = urlparse(self.path)
        query = parse_qs(parsed_url.query)
        location = query.get("location", [""])[0]
        status = query.get("status", [""])[0]
        priority = query.get("priority", [""])[0]

        reports = database.filter_reports(
            location=location,
            status=status,
            priority=priority
        )

        if not user_email:
            self.send_response(302)
            self.send_header("Location", "/login")
            self.end_headers()
            return

        user = database.get_user_by_email(user_email)

        if user is None or user["role"] != "admin":
            self.send_response(403)
            self.send_header("Content-Type", "text/html")
            self.end_headers()

            self.wfile.write(b"<h1>403 - Access Denied</h1>")
            return

        statistics = database.get_report_statistics()

        report_html = ""

        for report in reports:
            report_html += f"""
            <article class="report-card">
                <p class="report-status">{report["status"]}</p>
                <h3>{report["problem"]}</h3>
                <p><strong>Location:</strong> {report["location"]}</p>
                <p><strong>Priority:</strong> {report["priority"]}</p>
                <p>{report["description"]}</p>
                <small>Reported by {report["user_name"]} on {report["created_at"]}</small>

                <div class="status-control">
                    <form action="/update-status" method="POST">

                        <input
                            type="hidden"
                            name="report_id"
                            value="{report['id']}"
                        >

                        <label for="status-{report['id']}">
                            Update Status
                        </label>

                        <select id="status-{report['id']}" name="status">
                            <option
                                value="Pending"
                                {"selected" if report["status"] == "Pending" else ""}
                            >
                                Pending
                            </option>

                            <option
                                value="In Progress"
                                {"selected" if report["status"] == "In Progress" else ""}
                            >
                                In Progress
                            </option>

                            <option
                                value="Resolved"
                                {"selected" if report["status"] == "Resolved" else ""}
                            >
                                Resolved
                            </option>
                        </select>

                        <button type="submit" class="button">Update Status</button>
                    </form>
                </div>
            </article>
            """

        with open("pages/admin.html", "r", encoding="utf-8") as file:
            html = file.read()

        html = html.replace(
            '<div id="reports-container"></div>',
            f'<div id="reports-container">{report_html}</div>'
        )

        html = html.replace(
            "{{LOCATION_SEARCH}}",
            location
        )

        html = html.replace(
            "{{ALL_SELECTED}}",
            "selected" if status == "" else ""
        )
        html = html.replace(
            "{{PENDING_SELECTED}}",
            "selected" if status == "Pending" else ""
        )
        html = html.replace(
            "{{IN_PROGRESS_SELECTED}}",
            "selected"
            if status == "In Progress"
            else ""
        )
        html = html.replace(
            "{{RESOLVED_SELECTED}}",
            "selected"
            if status == "Resolved"
            else ""
        )

        html = html.replace(
            "{{ALL_PRIORITY_SELECTED}}",
            "selected" if priority == "" else ""
        )
        html = html.replace(
            "{{LOW_SELECTED}}",
            "selected" if priority == "Low" else ""
        )
        html = html.replace(
            "{{MEDIUM_SELECTED}}",
            "selected" if priority == "Medium" else ""
        )
        html = html.replace(
            "{{HIGH_SELECTED}}",
            "selected" if priority == "High" else ""
        )

        html = html.replace(
            'id="total-reports">0',
            f'id="total-reports">{statistics["total"]}'
        )
        html = html.replace(
            'id="pending-reports">0',
            f'id="pending-reports">{statistics["pending"]}'
        )
        html = html.replace(
            'id="in-progress-reports">0',
            f'id="in-progress-reports">{statistics["in_progress"]}'
        )
        html = html.replace(
            'id="resolved-reports">0',
            f'id="resolved-reports">{statistics["resolved"]}'
        )

        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()

        self.wfile.write(html.encode("utf-8"))

    def generate_dashboard(self):
        user_email = self.get_session_email()

        if not user_email:
            self.send_response(302)
            self.send_header("Location", "/login")
            self.end_headers()
            return
        
        user = database.get_user_by_email(user_email)

        if user["role"] == "admin":
            nav_links = """
                <a href="/report">New Report</a>
                <a href="/admin">Admin</a>
                <a href="/logout">Logout</a>
            """
        else:
            nav_links = """
                <a href="/report">New Report</a>
                <a href="/logout">Logout</a>
            """
        
        if user is None:
            self.send_response(302)
            self.send_header("Location", "/login")
            self.end_headers()
            return

        reports = database.get_reports_by_user(user["id"])

        total_reports = len(reports)

        pending_reports = sum(
            1 for report in reports
            if report["status"] == "Pending"
        )

        in_progress_reports = sum(
            1 for report in reports
            if report["status"] == "In Progress"
        )

        resolved_reports = sum(
            1 for report in reports
            if report["status"] == "Resolved"
        )

        report_html = ""

        for report in reports:
            report_html += f"""
            <article class="report-card">
                <p class="report-status">{report["status"]}</p>
                <h3>{report["problem"]}</h3>
                <p><strong>Location: </strong>{report["location"]}</p>
                <p><strong>Priority: </strong>{report["priority"]}</p>
                <p>{report["description"]}</p>
                <small>Reported on {report["created_at"]}</small>

                <div class="report-actions">
                    <a href="/edit-report?id={report['id']}" class="button">
                        Edit
                    </a>
                    <form
                        action="/delete-report"
                        method="POST"
                        class="delete-form"
                    >
                        <input
                            type="hidden"
                            name="report_id"
                            value="{report['id']}"
                        >

                        <button type="submit" class="button delete-button">
                            Delete
                        </button>
                    </form>
                </div>
            </article>
            """
        if not reports:
            report_html = """
            <div class="empty-state">
                <h3>No reports yet</h3>
                <p>You haven't submitted any waste reports.</p>
                <a href="/report" class="button">Submit a Report</a>
            </div>
            """

        with open("pages/dashboard.html", "r", encoding="utf-8") as file:
            html = file.read()

        html = html.replace(
            "{{NAV_LINKS}}",
            nav_links
        )

        html = html.replace("Welcome back!", f"Welcome back, {user['name']}!")

        html = html.replace(
            'id="total-reports">0',
            f'id="total-reports">{total_reports}'
        )

        html = html.replace(
            'id="pending-reports">0',
            f'id="pending-reports">{pending_reports}'
        )

        html = html.replace(
            'id="in-progress-reports">0',
            f'id="in-progress-reports">{in_progress_reports}'
        )

        html = html.replace(
            'id="resolved-reports">0',
            f'id="resolved-reports">{resolved_reports}'
        )

        html = html.replace(
            '<div id="reports-container"></div>',
            f'<div id="reports-container">{report_html}</div>'
        )

        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()

        self.wfile.write(html.encode("utf-8"))

    def generate_edit_report(self):
        user_email = self.get_session_email()

        if not user_email:
            self.send_response(302)
            self.send_header("Location", "/login")
            self.end_headers()
            return

        user = database.get_user_by_email(user_email)

        if user is None:
            self.send_response(302)
            self.send_header("Location", "/login")
            self.end_headers()
            return

        parsed_url = urlparse(self.path)
        query = parse_qs(parsed_url.query)

        report_id = query.get("id", [None])[0]

        if report_id is None:
            self.send_response(400)
            self.end_headers()

            self.wfile.write(b"<h1>400 - Report ID is required</h1>")
            return

        report = database.get_report_by_id(report_id, user["id"])

        if report is None:
            self.send_response(404)
            self.end_headers()

            self.wfile.write(b"<h1>404 - Report not found</h1>")
            return

        with open("pages/edit_report.html", "r", encoding="utf-8") as file:
            html = file.read()

        html = html.replace(
            "{{REPORT_ID}}",
            str(report["id"])
        )
        html = html.replace(
            "{{LOCATION}}",
            report["location"]
        )
        
        html = html.replace(
            "{{UNCOLLECTED_WASTE_SELECTED}}",
            "selected" if report["problem"] == "Uncollected waste" else ""
        )
        html = html.replace(
            "{{ILLEGAL_DUMPING_SELECTED}}",
            "selected" if report["problem"] == "Illegal dumping" else ""
        )
        html = html.replace(
            "{{OVERFLOWING_GARBAGE_SELECTED}}",
            "selected" if report["problem"] == "Overflowing garbage" else ""
        )
        html = html.replace(
            "{{BLOCKED_DRAINAGE_SELECTED}}",
            "selected" if report["problem"] == "Blocked drainage" else ""
        )

        html = html.replace(
            "{{DESCRIPTION}}",
            report["description"]
        )

        html = html.replace(
            "{{LOW_SELECTED}}",
            "selected" if report["priority"] == "Low" else ""
        )
        html = html.replace(
            "{{MEDIUM_SELECTED}}",
            "selected" if report["priority"] == "Medium" else ""
        )
        html = html.replace(
            "{{HIGH_SELECTED}}",
            "selected" if report["priority"] == "High" else ""
        )

        html = html.replace(
            'value=""',
            f'value="{report["location"]}"',
            1
        )

        self.send_response(200)

        self.send_header("Content-Type", "text/html")
        self.end_headers()

        self.wfile.write(html.encode("utf-8"))

database.initialize_database()

port = int(os.environ.get("PORT", 8000))

server = HTTPServer(("0.0.0.0", port), RequestHandler)

print(f"Server is running on port {port}")

server.serve_forever()