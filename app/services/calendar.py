from datetime import date, datetime, timedelta, timezone

def escape_ics(text):
    if not text:
        return ''
    return str(text).replace('\\', '\\\\').replace(';', r'\;').replace(',', r'\,').replace('\r\n', r'\n').replace('\n', r'\n').replace('\r', r'\n')

def generate_ics_calendar(tasks, cal_name="CampusHub Deadlines"):
    now_utc = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//CampusHub//CampusHub Tasks Calendar//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{escape_ics(cal_name)}",
        "X-WR-TIMEZONE:UTC",
    ]

    for t in tasks:
        if not t.due_date:
            continue
        dtstart = t.due_date.strftime('%Y%m%d')
        dtend = (t.due_date + timedelta(days=1)).strftime('%Y%m%d')
        priority_map = {'high': '1', 'medium': '5', 'low': '9'}
        priority = priority_map.get(t.priority, '5')
        status = 'COMPLETED' if t.completed else 'NEEDS-ACTION'
        percent = '100' if t.completed else '0'

        lines.extend([
            "BEGIN:VEVENT",
            f"UID:task-{t.id}-{t.user_id}@campushub",
            f"DTSTAMP:{now_utc}",
            f"DTSTART;VALUE=DATE:{dtstart}",
            f"DTEND;VALUE=DATE:{dtend}",
            f"SUMMARY:{escape_ics(t.title)}",
            f"DESCRIPTION:{escape_ics(t.description or '')}",
            f"CATEGORIES:{escape_ics(t.category.title() if t.category else 'Task')}",
            f"PRIORITY:{priority}",
            f"STATUS:{status}",
            f"PERCENT-COMPLETE:{percent}",
            "END:VEVENT"
        ])

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"
