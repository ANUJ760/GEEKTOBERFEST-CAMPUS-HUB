from datetime import date, timedelta
from sqlalchemy import func
from app.models import Task, Note, Announcement, Notification

def parse_stat_date(val):
    if not val: return None
    try:
        from datetime import datetime
        return datetime.strptime(val, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return None

def dashboard_stats(user, start_date=None, end_date=None, period='7d'):
    tasks=Task.query.filter_by(user_id=user.id)
    total=tasks.count(); completed=tasks.filter_by(completed=True).count(); pending=total-completed
    upcoming=tasks.filter(Task.completed.is_(False), Task.due_date.isnot(None), Task.due_date>=date.today()).order_by(Task.due_date.asc()).limit(5).all()
    recent_notes=Note.query.filter_by(user_id=user.id).order_by(Note.updated_at.desc()).limit(5).all()
    announcements=Announcement.query.order_by(Announcement.created_at.desc()).limit(5).all()
    productivity=round((completed/total)*100) if total else 0

    today=date.today()
    parsed_start=parse_stat_date(start_date)
    parsed_end=parse_stat_date(end_date) or today

    if parsed_start and parsed_end and parsed_start<=parsed_end:
        effective_start=parsed_start; effective_end=parsed_end; period_name='custom'
    elif period=='14d':
        effective_start=today-timedelta(days=13); effective_end=today; period_name='14d'
    elif period=='30d':
        effective_start=today-timedelta(days=29); effective_end=today; period_name='30d'
    elif period=='month':
        effective_start=date(today.year,today.month,1); effective_end=today; period_name='month'
    else:
        effective_start=today-timedelta(days=6); effective_end=today; period_name='7d'

    num_days=(effective_end-effective_start).days+1
    if num_days>90:
        num_days=90; effective_start=effective_end-timedelta(days=89)

    days=[effective_start+timedelta(days=i) for i in range(num_days)]
    daily=[]
    period_completed=0
    for day in days:
        day_str=day.isoformat()
        count=tasks.filter(Task.completed.is_(True), func.date(Task.updated_at)==day_str).count()
        label=day.strftime('%d %b') if num_days>7 else day.strftime('%a')
        daily.append({'day':label,'date':day_str,'count':count})
        period_completed+=count

    return {
        'total':total,'completed':completed,'pending':pending,'productivity':productivity,
        'upcoming':upcoming,'recent_notes':recent_notes,'announcements':announcements,
        'daily':daily,'period':period_name,'start_date':effective_start.isoformat(),
        'end_date':effective_end.isoformat(),'period_completed':period_completed
    }

def generate_notifications(user):
    from app.extensions import db
    today=date.today(); tomorrow=today+timedelta(days=1)
    existing={(n.title,n.message) for n in user.notifications if n.created_at.date()==today}
    for task in user.tasks:
        if not task.completed and task.due_date:
            if task.due_date < today: title='Task overdue'; message=f'"{task.title}" is overdue.'; kind='warning'
            elif task.due_date == tomorrow: title='Task due tomorrow'; message=f'"{task.title}" is due tomorrow.'; kind='info'
            else: continue
            if (title,message) not in existing: db.session.add(Notification(user_id=user.id,title=title,message=message,kind=kind))
    db.session.commit()
