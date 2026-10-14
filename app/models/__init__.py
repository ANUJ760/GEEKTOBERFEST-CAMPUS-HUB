from .models import User, Task, Note, Resource, Announcement, Notification


def __getattr__(name):
    from . import models
    return getattr(models, name)
