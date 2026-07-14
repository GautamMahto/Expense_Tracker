"""Default expense categories and keyword hints for auto-categorisation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DefaultCategory:
    name: str
    icon: str
    keywords: tuple[str, ...] = ()

    @property
    def label(self) -> str:
        return f"{self.icon} {self.name}"


# Ordered list of the categories seeded for every deployment.
DEFAULT_CATEGORIES: tuple[DefaultCategory, ...] = (
    DefaultCategory("Food", "🍔", ("food", "lunch", "dinner", "breakfast", "restaurant",
                                    "cafe", "coffee", "starbucks", "mcdonald", "pizza", "snack")),
    DefaultCategory("Transport", "🚕", ("transport", "uber", "ola", "taxi", "cab", "bus",
                                        "train", "metro", "fuel", "petrol", "gas", "fare")),
    DefaultCategory("Grocery", "🛒", ("grocery", "groceries", "supermarket", "walmart",
                                      "vegetables", "market")),
    DefaultCategory("Shopping", "🛍", ("shopping", "amazon", "flipkart", "clothes", "mall",
                                       "shoes", "electronics")),
    DefaultCategory("Rent", "🏠", ("rent", "lease", "landlord")),
    DefaultCategory("Bills", "💡", ("bill", "bills", "electricity", "water", "internet",
                                    "phone", "recharge", "utility")),
    DefaultCategory("Entertainment", "🎬", ("movie", "netflix", "spotify", "game", "concert",
                                            "entertainment", "cinema")),
    DefaultCategory("Healthcare", "🏥", ("doctor", "hospital", "pharmacy", "medicine",
                                         "health", "clinic", "medical")),
    DefaultCategory("Education", "📚", ("school", "college", "course", "book", "tuition",
                                        "education", "udemy")),
    DefaultCategory("Travel", "✈", ("travel", "flight", "hotel", "trip", "airbnb", "vacation")),
    DefaultCategory("Business", "💼", ("business", "office", "client", "invoice", "meeting")),
    DefaultCategory("Other", "📦", ()),
)


def category_labels() -> list[str]:
    return [c.label for c in DEFAULT_CATEGORIES]


def guess_category(text: str) -> str | None:
    """Best-effort category name from free text, or ``None`` if unclear."""
    lowered = text.lower()
    for category in DEFAULT_CATEGORIES:
        if any(keyword in lowered for keyword in category.keywords):
            return category.name
    return None
