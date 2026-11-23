import urllib.parse, urllib.request, urllib.error, time, json, re
HOST = '127.0.0.1'
PORT = 8000

def submit(name, desc):
    data = urllib.parse.urlencode({'student_name': name, 'description': desc}).encode()
    req = urllib.request.Request(f'http://{HOST}:{PORT}/submit', data=data)
    with urllib.request.urlopen(req) as f:
        f.read()

def get_admin_page():
    with urllib.request.urlopen(f'http://{HOST}:{PORT}/admin') as f:
        return f.read().decode()

def change_status(ticket_id, status):
    data = urllib.parse.urlencode({'ticket_id': str(ticket_id), 'status': status}).encode()
    req = urllib.request.Request(f'http://{HOST}:{PORT}/change_status', data=data)
    # follow redirect
    opener = urllib.request.build_opener(urllib.request.HTTPRedirectHandler())
    with opener.open(req) as f:
        f.read()

def parse_tickets(html):
    # simple regex to extract rows
    rows = []
    for match in re.finditer(r'<tr><td>(\d+)</td><td>([^<]+)</td><td>([^<]+)</td><td>([^<]+)</td><td>([^<]+)</td><td>([^<]+)</td><td>([^<]+)</td><td>([^<]+)</td><td>([^<]+)</td>', html):
        rows.append({
            'id': int(match.group(1)),
            'name': match.group(2),
            'desc': match.group(3),
            'category': match.group(4),
            'urgency': match.group(5),
            'dept': match.group(6),
            'priority': match.group(7),
            'status': match.group(8),
            'created': match.group(9)
        })
    return rows

# Wait for server to be ready
time.sleep(2)
scenarios = [
    ('TestUser1', 'Wi-Fi not working in AIML lab; entire class affected.'),
    ('TestUser2', 'Smoke and sparking near an electrical socket.'),
    ('TestUser3', 'Projector not working in Classroom 204.'),
    ('TestUser4', 'Laboratory computer keyboard damaged.'),
    ('TestUser5', 'Water leakage near the washroom.')
]
for name, desc in scenarios:
    submit(name, desc)
    time.sleep(0.2)
admin_html = get_admin_page()
print('ADMIN PAGE LENGTH', len(admin_html))
# Parse tickets
tickets = parse_tickets(admin_html)
print('Parsed tickets:', tickets)
# Change status of first ticket to In Progress then Resolved
if tickets:
    first_id = tickets[0]['id']
    change_status(first_id, 'In Progress')
    time.sleep(0.2)
    change_status(first_id, 'Resolved')
    time.sleep(0.2)
    admin_html2 = get_admin_page()
    tickets2 = parse_tickets(admin_html2)
    print('After status changes:', [t for t in tickets2 if t['id']==first_id])
else:
    print('No tickets found')
