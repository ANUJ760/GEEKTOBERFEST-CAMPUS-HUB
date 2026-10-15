import html
import re
from sqlalchemy import or_, and_
from app.models import Task, Note

def escape_like(s):
    """Escape special SQL LIKE wildcards % and _ using forward slash as escape character."""
    return s.replace('/', '//').replace('%', '/%').replace('_', '/_')

def parse_query_tokens(query_str):
    """Parse search query into tokens, supporting quoted phrases and individual words."""
    q = (query_str or '').strip()
    if not q:
        return []
    tokens = re.findall(r'"([^"]+)"|(\S+)', q)
    result = []
    for phrase, word in tokens:
        val = (phrase or word).strip()
        if val:
            result.append(val)
    return result

def highlight_excerpt(text, query, max_len=160):
    """
    Generate an HTML-safe excerpt around the best matched keyword or phrase,
    with matching terms wrapped in <mark> tags.
    """
    if not text:
        return ''

    lower_text = text.lower()
    lower_q = (query or '').strip().lower()
    clean_q = re.sub(r'["\']', '', lower_q)

    # Find the best match location
    idx = lower_text.find(clean_q) if clean_q else -1
    if idx == -1:
        words = [w for w in re.split(r'\s+', clean_q) if len(w) > 1]
        for w in words:
            idx = lower_text.find(w)
            if idx != -1:
                break

    if idx == -1:
        excerpt = text[:max_len]
        if len(text) > max_len:
            excerpt += '...'
    else:
        start = max(0, idx - 40)
        end = min(len(text), idx + max_len - 40)
        excerpt = text[start:end]
        if start > 0:
            excerpt = '...' + excerpt
        if end < len(text):
            excerpt = excerpt + '...'

    # Escape HTML to prevent XSS
    escaped = html.escape(excerpt)

    # Highlight matching words/phrases using <mark>
    tokens = parse_query_tokens(query)
    if tokens:
        # Sort by length descending so longer phrases match first
        tokens = sorted(set(tokens), key=len, reverse=True)
        safe_tokens = [re.escape(html.escape(t)) for t in tokens if t]
        if safe_tokens:
            pattern = '|'.join(safe_tokens)
            escaped = re.sub(f'(?i)({pattern})', r'<mark>\1</mark>', escaped)

    return escaped

def calculate_task_score(task, tokens, raw_query):
    """Calculate relevance score for a task (title matches > content matches > category matches)."""
    score = 0
    t_title = (task.title or '').lower()
    t_desc = (task.description or '').lower()
    t_cat = (task.category or '').lower()
    lower_raw = raw_query.lower()

    if lower_raw in t_title:
        score += 20
    if lower_raw in t_desc:
        score += 10

    for token in tokens:
        lt = token.lower()
        if lt in t_title:
            score += 6
        if lt in t_desc:
            score += 3
        if lt in t_cat:
            score += 2

    if not task.completed:
        score += 1

    return score

def calculate_note_score(note, tokens, raw_query):
    """Calculate relevance score for a note (title matches > content matches > subject matches)."""
    score = 0
    n_title = (note.title or '').lower()
    n_content = (note.content or '').lower()
    n_subj = (note.subject or '').lower()
    lower_raw = raw_query.lower()

    if lower_raw in n_title:
        score += 20
    if lower_raw in n_content:
        score += 10

    for token in tokens:
        lt = token.lower()
        if lt in n_title:
            score += 6
        if lt in n_content:
            score += 3
        if lt in n_subj:
            score += 2

    return score

def search_student_content(user_id, query_str, content_type='all'):
    """
    Search tasks and notes strictly scoped to user_id with relevance ranking,
    content-type filtering, and contextual excerpt generation.
    """
    q = (query_str or '').strip()
    if not q:
        return {'query': '', 'tasks': [], 'notes': [], 'total': 0}

    tokens = parse_query_tokens(q)
    if not tokens:
        return {'query': q, 'tasks': [], 'notes': [], 'total': 0}

    norm_type = (content_type or 'all').lower()
    if norm_type not in ('all', 'tasks', 'notes'):
        norm_type = 'all'

    tasks_results = []
    if norm_type in ('all', 'tasks'):
        task_filters = []
        for token in tokens:
            pattern = f"%{escape_like(token)}%"
            task_filters.append(or_(
                Task.title.ilike(pattern, escape='/'),
                Task.description.ilike(pattern, escape='/'),
                Task.category.ilike(pattern, escape='/')
            ))
        tasks_query = Task.query.filter(
            Task.user_id == user_id,
            and_(*task_filters)
        )

        matched_tasks = tasks_query.all()
        # Sort by relevance score descending, then updated_at descending
        matched_tasks.sort(
            key=lambda t: (calculate_task_score(t, tokens, q), t.updated_at.timestamp() if t.updated_at else 0),
            reverse=True
        )

        for t in matched_tasks[:50]:
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
    if norm_type in ('all', 'notes'):
        note_filters = []
        for token in tokens:
            pattern = f"%{escape_like(token)}%"
            note_filters.append(or_(
                Note.title.ilike(pattern, escape='/'),
                Note.content.ilike(pattern, escape='/'),
                Note.subject.ilike(pattern, escape='/')
            ))
        notes_query = Note.query.filter(
            Note.user_id == user_id,
            and_(*note_filters)
        )

        matched_notes = notes_query.all()
        # Sort by relevance score descending, then updated_at descending
        matched_notes.sort(
            key=lambda n: (calculate_note_score(n, tokens, q), n.updated_at.timestamp() if n.updated_at else 0),
            reverse=True
        )

        for n in matched_notes[:50]:
            snippet = highlight_excerpt(n.content or n.title, q)
            notes_results.append({
                'id': n.id,
                'title': n.title,
                'subject': n.subject,
                'snippet': snippet,
                'updated_at': n.updated_at.isoformat() if n.updated_at else None,
                'type': 'note'
            })

    return {
        'query': q,
        'tasks': tasks_results,
        'notes': notes_results,
        'total': len(tasks_results) + len(notes_results)
    }
