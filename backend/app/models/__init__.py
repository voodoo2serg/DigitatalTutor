# Backend models are now shared with bot
# Import from the canonical source at bot/models/
from bot.models.models import Base, User, WorkType, StudentWork, File, Communication
from bot.services.db import get_async_session as get_db

__all__ = [
    'Base', 'User', 'WorkType', 'StudentWork', 'File', 'Communication',
    'get_db',
]
