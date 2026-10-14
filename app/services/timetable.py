from datetime import datetime, time, date
from app.models import TimetableEntry, DAYS_OF_WEEK


def parse_time_str(val):
    if isinstance(val, time):
        return val
    if not val:
        raise ValueError("Time is required.")
    val = val.strip()
    try:
        parts = val.split(':')
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError()
        return time(hour, minute)
    except Exception:
        raise ValueError("Time must be in HH:MM format (24-hour).")


def get_weekly_timetable(user):
    entries = TimetableEntry.query.filter_by(user_id=user.id).order_by(TimetableEntry.day_of_week.asc(), TimetableEntry.start_time.asc()).all()
    schedule = {i: [] for i in range(7)}
    for entry in entries:
        schedule[entry.day_of_week].append(entry)
    return schedule


def get_upcoming_classes(user, limit=5):
    now = datetime.now()
    today_weekday = now.weekday()
    now_time = now.time()

    all_entries = TimetableEntry.query.filter_by(user_id=user.id).all()
    if not all_entries:
        return []

    # Sort classes cyclically starting from (today_weekday, now_time)
    upcoming = []
    # Check 7 days ahead (offset 0 to 7 to wrap around past classes today to next week)
    for offset in range(8):
        target_day = (today_weekday + offset) % 7
        day_classes = [e for e in all_entries if e.day_of_week == target_day]
        day_classes.sort(key=lambda e: e.start_time)
        for c in day_classes:
            if offset == 0 and c.end_time < now_time:
                # Class ended already today, will appear next week at offset 7
                continue
            if offset == 7 and c.end_time >= now_time:
                # Already included under offset 0
                continue
            is_today = (offset == 0)
            is_ongoing = (offset == 0 and c.start_time <= now_time <= c.end_time)
            upcoming.append({
                'entry': c,
                'is_today': is_today,
                'is_ongoing': is_ongoing,
                'day_name': DAYS_OF_WEEK[target_day],
                'offset_days': offset
            })
            if len(upcoming) >= limit:
                return upcoming
    return upcoming
