"""
DigitalTutor Bot - Handlers Package
"""
from .start import router as start_router
from .registration import router as registration_router
from .works import router as works_router
from .submit import router as submit_router
from .plan import router as plan_router
from .communication import router as communication_router
from .ai_review import router as ai_review_router
from .works_review import router as works_review_router
from .students import router as students_router

__all__ = [
    'start_router',
    'registration_router',
    'works_router',
    'submit_router',
    'plan_router',
    'communication_router',
    'ai_review_router',
    'works_review_router',
    'students_router',
]
