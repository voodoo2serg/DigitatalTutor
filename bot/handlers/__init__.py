from .start import router as start_router
from .registration import router as registration_router
from .works import router as works_router
from .submit import router as submit_router
from .plan import router as plan_router
from .communication import router as communication_router

__all__ = [
    'start_router',
    'registration_router', 
    'works_router',
    'submit_router',
    'plan_router',
    'communication_router',
]
