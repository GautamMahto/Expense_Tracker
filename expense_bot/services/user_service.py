"""User lifecycle and preferences (application layer)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.categories import DEFAULT_CATEGORIES
from ..core.config import get_settings
from ..core.schemas import UserProfile
from ..db.models import User
from ..db.repositories import CategoryRepository, UserRepository


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)

    async def get_or_create(
        self,
        *,
        telegram_user_id: int,
        username: str | None,
        full_name: str | None,
    ) -> User:
        """Return the existing user or register a new one (implicit auth)."""
        user = await self.users.get_by_telegram_id(telegram_user_id)
        if user is not None:
            return user
        settings = get_settings()
        return await self.users.create(
            telegram_user_id=telegram_user_id,
            username=username,
            full_name=full_name,
            currency=settings.default_currency,
            timezone=settings.default_timezone,
        )

    async def profile(self, user: User) -> UserProfile:
        return UserProfile.model_validate(user)

    async def update_preferences(self, user: User, **fields: object) -> User:
        allowed = {
            "currency",
            "timezone",
            "default_payment_method",
            "language",
            "export_format",
            "reminder_time",
        }
        payload = {k: v for k, v in fields.items() if k in allowed}
        return await self.users.update_fields(user, **payload)

    async def users_with_reminders(self) -> list[User]:
        return await self.users.all_with_reminders()


async def ensure_categories_seeded(session: AsyncSession) -> None:
    """Seed the global default categories once."""
    repo = CategoryRepository(session)
    if await repo.count() == 0:
        await repo.bulk_create([(c.name, c.icon) for c in DEFAULT_CATEGORIES])
