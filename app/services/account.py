from app.extensions import db
from app.models import Resource

def export_user_account_data(user):
    """Serialize all personal data and associated records for a user."""
    return {
        'user': {
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'role': user.role,
            'department': user.department or '',
            'year': user.year or '',
            'joined_at': user.joined_at.isoformat() if user.joined_at else None
        },
        'tasks': [
            {
                'id': t.id,
                'title': t.title,
                'description': t.description or '',
                'priority': t.priority,
                'category': t.category,
                'due_date': t.due_date.isoformat() if t.due_date else None,
                'completed': t.completed,
                'created_at': t.created_at.isoformat() if t.created_at else None,
                'updated_at': t.updated_at.isoformat() if t.updated_at else None
            }
            for t in user.tasks
        ],
        'notes': [
            {
                'id': n.id,
                'title': n.title,
                'subject': n.subject or 'General',
                'content': n.content,
                'created_at': n.created_at.isoformat() if n.created_at else None,
                'updated_at': n.updated_at.isoformat() if n.updated_at else None
            }
            for n in user.notes
        ],
        'notifications': [
            {
                'id': notif.id,
                'title': notif.title,
                'message': notif.message,
                'kind': notif.kind,
                'read': notif.read,
                'created_at': notif.created_at.isoformat() if notif.created_at else None
            }
            for notif in user.notifications
        ]
    }

def delete_user_account(user):
    """Permanently delete a user account and associated personal records, safely disassociating shared resources."""
    try:
        from flask_login import logout_user
        logout_user()
    except Exception:
        pass

    # Disassociate resources added by this user so resources are not left pointing to deleted user
    Resource.query.filter_by(added_by=user.id).update({'added_by': None})
    db.session.delete(user)
    db.session.commit()
