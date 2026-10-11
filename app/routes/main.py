from datetime import date
from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from app.extensions import db
from app.models import Task, Note, Resource, Announcement, Notification
from app.services.dashboard import dashboard_stats, generate_notifications
from app.utils.validation import clean, limited, valid_url

main_bp=Blueprint('main',__name__)

@main_bp.get('/')
def index(): return redirect(url_for('main.dashboard')) if current_user.is_authenticated else redirect(url_for('auth.login'))

@main_bp.get('/dashboard')
@login_required
def dashboard():
    generate_notifications(current_user); return render_template('dashboard.html', stats=dashboard_stats(current_user))

@main_bp.get('/tasks')
@login_required
def tasks(): return render_template('tasks.html', tasks=Task.query.filter_by(user_id=current_user.id).order_by(Task.due_date.asc().nullslast(), Task.created_at.desc()).all())

@main_bp.get('/deadlines')
@login_required
def deadlines(): return render_template('deadlines.html', tasks=Task.query.filter_by(user_id=current_user.id).order_by(Task.due_date.asc().nullslast()).all())

@main_bp.get('/notes')
@login_required
def notes(): return render_template('notes.html', notes=Note.query.filter_by(user_id=current_user.id).order_by(Note.updated_at.desc()).all())

@main_bp.get('/notes/<int:item_id>/export')
@login_required
def export_note_markdown(item_id):
    import re
    from flask import Response
    note = Note.query.filter_by(id=item_id, user_id=current_user.id).first_or_404()
    clean_title = re.sub(r'[^a-zA-Z0-9_\- ]+', '', note.title).strip().replace(' ', '_') or f'note-{note.id}'
    filename = f"{clean_title}.md"
    body = f"# {note.title}\n\n**Subject:** {note.subject or 'General'}\n**Updated:** {note.updated_at.strftime('%Y-%m-%d')}\n\n---\n\n{note.content}\n"
    return Response(body, mimetype='text/markdown', headers={'Content-Disposition': f'attachment; filename="{filename}"'})

@main_bp.get('/resources')
@login_required
def resources(): return render_template('resources.html', resources=Resource.query.order_by(Resource.created_at.desc()).all())

@main_bp.get('/announcements')
@login_required
def announcements(): return render_template('announcements.html', announcements=Announcement.query.order_by(Announcement.created_at.desc()).all())

@main_bp.get('/notifications')
@login_required
def notifications(): return render_template('notifications.html', notifications=Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all())

@main_bp.route('/profile', methods=['GET','POST'])
@login_required
def profile():
    if request.method=='POST':
        try:
            current_user.name=limited(request.form.get('name'),80); current_user.department=limited(request.form.get('department'),100,False); current_user.year=limited(request.form.get('year'),20,False)
            db.session.commit(); flash('Profile updated.', 'success')
        except ValueError as e: flash(str(e),'error')
    return render_template('profile.html')

@main_bp.get('/profile/export')
@login_required
def export_user_data():
    import json
    from flask import Response
    data = {
        'user': {
            'id': current_user.id,
            'name': current_user.name,
            'email': current_user.email,
            'role': current_user.role,
            'department': current_user.department,
            'year': current_user.year,
            'joined_at': current_user.joined_at.isoformat()
        },
        'tasks': [
            {
                'id': t.id,
                'title': t.title,
                'description': t.description,
                'priority': t.priority,
                'category': t.category,
                'due_date': t.due_date.isoformat() if t.due_date else None,
                'completed': t.completed,
                'created_at': t.created_at.isoformat()
            }
            for t in current_user.tasks
        ],
        'notes': [
            {
                'id': n.id,
                'title': n.title,
                'subject': n.subject,
                'content': n.content,
                'created_at': n.created_at.isoformat(),
                'updated_at': n.updated_at.isoformat()
            }
            for n in current_user.notes
        ],
        'notifications': [
            {
                'id': notif.id,
                'title': notif.title,
                'message': notif.message,
                'kind': notif.kind,
                'read': notif.read,
                'created_at': notif.created_at.isoformat()
            }
            for notif in current_user.notifications
        ]
    }
    resp = Response(json.dumps(data, indent=2), mimetype='application/json')
    resp.headers['Content-Disposition'] = 'attachment; filename="campus_hub_data_export.json"'
    return resp

@main_bp.post('/profile/delete-account')
@login_required
def delete_account():
    from flask_login import logout_user
    password = request.form.get('password', '')
    if not current_user.check_password(password):
        flash('Incorrect password. Account deletion aborted.', 'error')
        return redirect(url_for('main.profile'))
    user_to_delete = current_user._get_current_object()
    Resource.query.filter_by(added_by=user_to_delete.id).update({'added_by': None})
    logout_user()
    db.session.delete(user_to_delete)
    db.session.commit()
    flash('Your account and all associated data have been permanently deleted.', 'info')
    return redirect(url_for('auth.login'))
