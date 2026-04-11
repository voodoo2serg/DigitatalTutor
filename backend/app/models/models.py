# Re-export from the canonical source at bot/models/
# This avoids model duplication between bot and backend
from bot.models.models import Base
from bot.models.models import User, WorkType, StudentWork, File, Communication, AIProvider, AIAnalysisLog, MessageTemplate

__all__ = [
    'Base', 'User', 'WorkType', 'StudentWork', 'File', 'Communication',
    'AIProvider', 'AIAnalysisLog', 'MessageTemplate',
]
