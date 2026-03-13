from __future__ import annotations

from dataclasses import dataclass


@dataclass
class User:
    userId: int | None
    mail: str
    name: str
    passwordHash: str
    role: str = "user"
    createAccountData: str | None = None
    lastVIsitData: str | None = None
    countOfPictures: int = 0
