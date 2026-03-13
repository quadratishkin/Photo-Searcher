from __future__ import annotations

from dataclasses import dataclass

from searcher_app.utils.user import User


@dataclass
class Admin(User):
    role: str = "admin"
