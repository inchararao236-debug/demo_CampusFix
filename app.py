import sqlite3, threading, urllib.parse, http.server, socketserver, datetime, concurrent.futures, sys, time
import logging
import smtplib
from email.message import EmailMessage

# ---------- Backup ----------
# Original file backed up as app_backup.py

DB_PATH = 'complaints.db'
HOST = '127.0.0.1'
PORT = 8000

# ---------- Logging ----------
logger = logging.getLogger('CampusFix')
logger.setLevel(logging.INFO)
fh = logging.FileHandler('app.log')
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)

# ---------- Database ----------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT,
            description TEXT,
            category TEXT,
            urgency TEXT,
            department TEXT,
            priority TEXT,
            status TEXT,
            created_at TEXT,
            logs TEXT,
            email TEXT,
            location TEXT
        )
    ''')
    conn.commit()
    conn.close()
    # Add columns if they were missing in older DB versions
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('ALTER TABLE tickets ADD COLUMN email TEXT')
        c.execute('ALTER TABLE tickets ADD COLUMN location TEXT')
        conn.commit()
    except sqlite3.OperationalError:
        # Columns already exist – ignore
        pass
    finally:
        conn.close()

# ---------- Simple AI Agents (simulated) ----------
def analyze_problem(description: str):
    """Determine category and urgency from description using smarter rules."""
    # Smart classification mapping
    cat_map = {
        'fan': 'Electrical',
        'light': 'Electrical',
        'tube light': 'Electrical',
        'switch': 'Electrical',
        'electrical wiring': 'Electrical',
        'wifi': 'Network',
        'internet': 'Network',
        'network': 'Network',
        'water leakage': 'Plumbing',
        'leakage': 'Plumbing',
        'taps': 'Plumbing',
        'drainage': 'Plumbing',
        'projector': 'AV Equipment',
        'smart board': 'AV Equipment',
        'computer': 'Lab Computer',
        'keyboard': 'Lab Computer',
        'mouse': 'Lab Computer',
        'boot failure': 'Lab Computer',
        'library login': 'Library Access',
        'library access': 'Library Access',
        'smoke': 'Safety',
        'sparks': 'Safety',
        'fire': 'Safety',
        'electric shock': 'Safety',
    }
    # Default values
    category = 'Other'
    urgency = 'Low'
    lower = description.lower()
    # Determine category by first matching keyword
    for kw, cat in cat_map.items():
        if kw in lower:
            category = cat
            break
    # Urgency rules
    if category == 'Safety':
        urgency = 'High'
    else:
        high_keywords = ['not working', 'down', 'cannot', "can't", 'urgent', 'exam']
        medium_keywords = ['slow', 'intermittent', 'leaking']
        for kw in high_keywords:
            if kw in lower:
                urgency = 'High'
                break
        else:
            for kw in medium_keywords:
                if kw in lower:
                    urgency = 'Medium'
                    break
    log = f"Analyzer: category={category}, urgency={urgency}\n"
    return category, urgency, log

def investigate_solution(category: str, urgency: str):
    """Provide specific suggestions based on category."""
    suggestions = {
        'Electrical': ['Check power supply', 'Inspect wiring', 'Contact electrician'],
        'Network': ['Check router', 'Inspect network connectivity'],
        'Plumbing': ['Shut off water supply', 'Contact plumber'],
        'AV Equipment': ['Check power cable', 'Check input source'],
        'Lab Computer': ['Reboot machine', 'Check OS logs'],
        'Safety': ['Evacuate area', 'Call emergency services'],
        'Library Access': ['Reset password', 'Check network drive'],
    }
    sol = suggestions.get(category, ['Contact support'])
    confidence = 'High' if urgency == 'High' else 'Medium'
    log = f"Investigator: solutions={sol}, confidence={confidence}\n"
    return sol, confidence, log

def assign_department(category: str):
    mapping = {
        'Electrical': 'Electrical Maintenance',
        'Network': 'IT Support',
        'Plumbing': 'Plumbing/Maintenance',
        'AV Equipment': 'AV Support',
        'Lab Computer': 'IT Lab',
        'Safety': 'Campus Safety',
        'Library Access': 'Library Services',
        'Other': 'General Services',
    }
    return mapping.get(category, 'General Services')

def compute_priority(urgency: str, confidence: str):
    if urgency == 'High' or confidence == 'High':
        return 'P1'
    if urgency == 'Medium':
        return 'P2'
    return 'P3'

def check_duplicate(description, location):
    """Return a warning if a similar complaint was filed for the same location recently.
    Looks back 7 days and compares description text using substring and Jaccard similarity.
    """
    import re
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    week_ago = (datetime.datetime.now() - datetime.timedelta(days=7)).isoformat()
    c.execute('SELECT description FROM tickets WHERE location = ? AND created_at >= ?', (location, week_ago))
    past = c.fetchall()
    conn.close()
    desc_lower = description.lower()
    # Helper to make a token set from a string
    def token_set(s):
        return set(re.findall(r"\w+", s.lower()))
    new_set = token_set(desc_lower)
    for (past_desc,) in past:
        past_lower = past_desc.lower()
        # Direct substring match (either way)
        if desc_lower in past_lower or past_lower in desc_lower:
            return "Duplicate warning: a similar complaint was submitted recently at this location."
        # Jaccard similarity of word tokens
        past_set = token_set(past_desc)
        if past_set:
            similarity = len(new_set & past_set) / len(new_set | past_set)
            if similarity >= 0.6:
                return "Duplicate warning: a similar complaint was submitted recently at this location."
    return None
def create_ticket(student_name, description, category, urgency,
                  department, priority, logs, email=None, location=None):
    """
    Insert a new complaint into the SQLite tickets table.
    Returns the ticket id.
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = datetime.datetime.now().isoformat()
    status = 'Open'
    c.execute('''
        INSERT INTO tickets (
            student_name, description, category, urgency,
            department, priority, status, created_at, logs,
            email, location
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
    ''', (student_name, description, category, urgency,
          department, priority, status, now, logs, email, location))
    conn.commit()
    ticket_id = c.lastrowid
    conn.close()
    return ticket_id
    c.execute('''
        INSERT INTO tickets (student_name, description, category, urgency, department, priority, status, created_at, logs, email, location)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
    ''', (student_name, description, category, urgency, department, priority, status, now, logs, email, location))
    conn.commit()
    ticket_id = c.lastrowid
    conn.close()
    return ticket_id

def process_complaint(student_name, description, email=None, location=None):
    # Run Analyzer and Investigator in parallel (Investigator needs category, so we sequence)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future_analyze = executor.submit(analyze_problem, description)
        category, urgency, log_a = future_analyze.result()
        future_invest = executor.submit(investigate_solution, category, urgency)
        solutions, confidence, log_i = future_invest.result()
    department = assign_department(category)
    priority = compute_priority(urgency, confidence)
    logs = log_a + log_i + f"Coordinator: dept={department}, priority={priority}, solutions={solutions}\n"
    # Duplicate detection – add warning to logs if found
    warning = check_duplicate(description, location)
    if warning:
        logs += f"Duplicate Warning: {warning}\n"
    ticket_id = create_ticket(student_name, description, category, urgency, department, priority, logs, email, location)
    return ticket_id, logs

# ---------- CSS ----------
STYLE = '''
body {font-family: Arial, sans-serif; background: #f5f7fa; margin:0; padding:20px;}
h1 {color:#333;}
form {background:#fff; padding:20px; border-radius:8px; box-shadow:0 2px 8px rgba(0,0,0,0.1); max-width:500px; margin:auto;}
input[type=text], input[type=email], textarea {width:100%; padding:10px; margin:8px 0; border:1px solid #ccc; border-radius:4px; box-sizing:border-box;}
input[type=submit] {background:linear-gradient(45deg, #6a5acd, #00bfff); color:#fff; border:none; padding:12px 20px; border-radius:4px; cursor:pointer; transition:background 0.3s;}
input[type=submit]:hover {background:linear-gradient(45deg, #5a4abd, #00a0e0);}
.table-wrapper {overflow-x:auto;}
table {width:100%; border-collapse:collapse; margin-top:20px;}
th, td {padding:12px; text-align:left; border-bottom:1px solid #ddd;}
th {background:#6a5acd; color:#fff;}
tr:hover {background:#f1f1f1;}
.badge {padding:4px 8px; border-radius:12px; color:#fff; font-size:0.9em;}
.badge-open {background:#1e90ff;}
.badge-progress {background:#ff8c00;}
.badge-resolved {background:#32cd32;}
.priority-P1 {color:#ff0000; font-weight:bold;}
.priority-P2 {color:#ff7f00; font-weight:bold;}
.priority-P3 {color:#008000; font-weight:bold;}
.cards {display:flex; flex-wrap:wrap; justify-content:space-around; margin-bottom:20px;}
.card {background:#fff; flex:1 1 200px; margin:10px; padding:20px; border-radius:8px; box-shadow:0 2px 6px rgba(0,0,0,0.1); text-align:center;}
.card h2 {margin:0; font-size:2em;}
@media (max-width:600px) {form {padding:15px;}}
''' 

# ---------- HTTP Server ----------
class RequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(303)
            self.send_header('Content-type', 'text/html')
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            html = f'''<html><head><title>CampusFix Complaint</title><style>{STYLE}</style></head><body>
<h1>Submit a Complaint</h1>
<form method="POST" action="/submit">
Name: <input type="text" name="student_name" required><br>
Email: <input type="email" name="email" required><br>
Location: <input type="text" name="location" required><br>
Description:<br><textarea name="description" rows="4" cols="50" required></textarea><br>
<input type="submit" value="Submit">
</form>
</body></html>'''
            self.wfile.write(html.encode())
        elif self.path == '/admin':
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute('SELECT id, student_name, description, category, urgency, department, priority, status, created_at, logs, email, location FROM tickets ORDER BY id DESC')
            rows = c.fetchall()
            # Statistics
            total = len(rows)
            open_cnt = sum(1 for r in rows if r[7]=='Open')
            prog_cnt = sum(1 for r in rows if r[7]=='In Progress')
            res_cnt = sum(1 for r in rows if r[7]=='Resolved')
            conn.close()
            self.send_response(303)
            self.send_header('Content-type', 'text/html')
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            rows_html = ''
            for r in rows:
                rows_html += f"<tr><td>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td><td>{r[3]}</td><td>{r[4]}</td><td>{r[5]}</td><td class='priority-{r[6]}'>{r[6]}</td>"
                status_cls = {'Open':'badge-open','In Progress':'badge-progress','Resolved':'badge-resolved'}.get(r[7],'badge-open')
                rows_html += f"<td><span class='badge {status_cls}'>{r[7]}</span></td><td>{r[8]}</td><td><pre>{r[9]}</pre></td><td>{r[10] or ''}</td><td>{r[11] or ''}</td>"
                rows_html += "<td><form method='POST' action='/change_status'>"
                rows_html += f"<input type='hidden' name='ticket_id' value='{r[0]}'/>"
                rows_html += "<select name='status'>"
                rows_html += f"<option value='Open'{' selected' if r[7]=='Open' else ''}>Open</option>"
                rows_html += f"<option value='In Progress'{' selected' if r[7]=='In Progress' else ''}>In Progress</option>"
                rows_html += f"<option value='Resolved'{' selected' if r[7]=='Resolved' else ''}>Resolved</option>"
                rows_html += "</select><input type='submit' value='Update'></form></td></tr>"
            html = f'''<html><head><title>Admin Dashboard</title><style>{STYLE}</style></head><body>
<h1>Complaints Dashboard</h1>
<div class='cards'>
<div class='card'><h2>{total}</h2><p>Total Complaints</p></div>
<div class='card'><h2>{open_cnt}</h2><p>Open</p></div>
<div class='card'><h2>{prog_cnt}</h2><p>In Progress</p></div>
<div class='card'><h2>{res_cnt}</h2><p>Resolved</p></div>
</div>
<div class='table-wrapper'>
<table border="1" cellpadding="5" cellspacing="0">
<tr><th>ID</th><th>Name</th><th>Description</th><th>Category</th><th>Urgency</th><th>Dept</th><th>Priority</th><th>Status</th><th>Created</th><th>Logs</th><th>Email</th><th>Location</th><th>Change</th></tr>
{rows_html}
</table></div></body></html>'''
            self.wfile.write(html.encode())
        else:
            super().do_GET()
    def do_POST(self):
        if self.path == '/submit':
            length = int(self.headers.get('content-length', 0))
            post_data = self.rfile.read(length).decode()
            params = urllib.parse.parse_qs(post_data)
            student_name = params.get('student_name', ['Anonymous'])[0]
            description = params.get('description', [''])[0]
            email = params.get('email', [''])[0]
            location = params.get('location', [''])[0]
            ticket_id, logs = process_complaint(student_name, description, email, location)
            self.send_response(303)
            self.send_header('Content-type', 'text/html')
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            resp = f'''<html><head><title>Submitted</title></head><body>
<h2>Complaint submitted! Ticket ID: {ticket_id}</h2>
<p>Check <a href="/admin">Admin Dashboard</a> for details.</p>
</body></html>'''
            self.wfile.write(resp.encode())
        elif self.path == '/change_status':
            length = int(self.headers.get('content-length', 0))
            post_data = self.rfile.read(length).decode()
            params = urllib.parse.parse_qs(post_data)
            ticket_id = params.get('ticket_id', [''])[0]
            new_status = params.get('status', ['Open'])[0]
            try:
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute('UPDATE tickets SET status = ? WHERE id = ?', (new_status, ticket_id))
                conn.commit()
                conn.close()
                self.send_response(303)
                self.send_header('Location', '/admin')
                self.end_headers()
            except Exception as e:
                self.send_error(500, f'Failed to update status: {e}')
        else:
            self.send_error(404)

def run_server():
    init_db()
    with socketserver.TCPServer((HOST, PORT), RequestHandler) as httpd:
        print(f"Serving on http://{HOST}:{PORT}")
        httpd.serve_forever()

if __name__ == '__main__':
    # When run directly, start server (used for manual demo). For automated test we launch in background.
    run_server()
