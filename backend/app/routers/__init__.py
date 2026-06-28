from .auth          import router as auth_router
from .assignments   import router as assignments_router
from .submissions   import router as submissions_router
from .users         import router as users_router
from .notifications import router as notifications_router

__all__ = [
    "auth_router",
    "assignments_router",
    "submissions_router",
    "users_router",
    "notifications_router",
]