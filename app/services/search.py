from sqlalchemy import or_, and_
from app.models import Task, Note

def highlight_excerpt(text, query, max_len=160):
    if not text:
        return ''
    lower_text = text.lower()
    lower_q = query.lower()
    idx = lower_text.find(lower_q)
    if idx == -1:
        words = lower_q.split()
        for w in words:
            if len(w) > 2:
                idx = lower_text.find(w)
                if idx != -1:
                    break
    if idx == -1:
        return text[:max_len] + ('...' if len(text) > max_len else '')

    start = max(0, idx - 40)
    end = min(len(text), idx + max_len - 40)
    excerpt = text[start:end]
    if start > 0:
        excerpt = '...' + excerpt
    if end < len(text):
        excerpt = excerpt + '...'
    return excerpt

def search_student_content(user_id, query_str, content_type='all'):
    q = (query_str or '').strip()
    if not q:
        return {'query': '', 'tasks': [], 'notes': [], 'total': 0}

    tokens = [t for t in q.split() if t]

    tasks_results = []
    if content_type in ('all', 'tasks'):
        task_filters = []
        for token in tokens:
            pattern = f"%{token}%"
            task_filters.append(or_(
                Task.title.ilike(pattern),
                Task.description.ilike(pattern),
                Task.category.ilike(pattern)
            ))
        tasks_query = Task.query.filter(
            Task.user_id == user_id,
            and_(*task_filters)
        ).order_by(Task.updated_at.desc())

        for t in tasks_query.limit(50).all():
            snippet = highlight_excerpt(t.description or t.title, q)
            tasks_results.append({
                'id': t.id,
                'title': t.title,
                'description': t.description,
                'category': t.category,
                'priority': t.priority,
                'due_date': t.due_date.isoformat() if t.due_date else None,
                'completed': t.completed,
                'snippet': snippet,
                'type': 'task'
            })

    notes_results = []
    if content_type in ('all', 'notes'):
        note_filters = []
        for token in tokens:
            pattern = f"%{token}%"
            note_filters.append(or_(
                Note.title.ilike(pattern),
                Note.content.ilike(pattern),
                Note.subject.ilike(pattern)
            ))
        notes_query = Note.query.filter(
            Note.user_id == user_id,
            and_(*note_filters)
        ).order_by(Note.updated_at.desc())

        for n in notes_query.limit(50).all():
            snippet = highlight_excerpt(n.content or n.title, q)
            notes_results.append({
                'id': n.id,
                'title': n.title,
                'subject': n.subject,
                'snippet': snippet,
                'updated_at': n.updated_at.isoformat(),
                'type': 'note'
            })

    return {
        'query': q,
        'tasks': tasks_results,
        'notes': notes_results,
        'total': len(tasks_results) + len(notes_results)
    }
