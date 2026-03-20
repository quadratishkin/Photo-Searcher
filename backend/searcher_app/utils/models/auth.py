"""
Модуль для аутентификации пользователей.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any

from ..databaseManager import DatabaseManager, UserRecord
from ..functions.hash import generateHash


@dataclass
class AuthResult:
    """
    Результат аутентификации.

    Attributes:
        code: 0 - успех, 1 - неверный пароль, 2 - пользователь не найден
        user: данные пользователя (при успехе)
        message: текстовое описание
    """
    code: int
    user: Optional[UserRecord] = None
    message: str = ""

    def toDict(self) -> Dict[str, Any]:
        """
        Преобразует результат в словарь для JSON ответа.

        Returns:
            Dict[str, Any]: словарь с кодом, сообщением и данными пользователя
        """
        result: Dict[str, Any] = {
            "code": self.code,
            "message": self.message
        }

        if self.user is not None:
            result["user"] = {
                "userId": self.user.userId if self.user.userId is not None else 0,
                "mail": self.user.mail,
                "name": self.user.name,
                "role": self.user.role,
                "lastVisitData": self.user.lastVIsitData,
                "countOfPictures": self.user.countOfPictures
            }

        return result


def authenticate(email: str, password: str, db: DatabaseManager) -> AuthResult:
    """
    Аутентифицирует пользователя по email и паролю.

    Логика:
        1. Проверить email в БД
        2. Если email есть:
            - Хешировать password
            - Сравнить с hash из БД
            - Совпадают → код 0 + данные пользователя
            - Не совпадают → код 1
        3. Если email нет → код 2
        4. При успехе обновить lastVisitData

    Args:
        email: email пользователя
        password: пароль в открытом виде
        db: менеджер базы данных

    Returns:
        AuthResult: результат аутентификации
    """
    # Ищем пользователя по email
    user = db.findUserByMail(email)

    # Пользователь не найден
    if user is None:
        return AuthResult(
            code=2,
            message="Пользователь с таким email не найден"
        )

    # Хешируем введённый пароль
    hashedPassword = generateHash(password)

    # Сравниваем хеши
    if user.passwordHash != hashedPassword:
        return AuthResult(
            code=1,
            message="Неверный пароль"
        )

    # Успешная аутентификация - обновляем lastVisitData
    currentTime = datetime.now().isoformat()

    # Создаём обновлённую запись пользователя
    updatedUser = UserRecord(
        userId=user.userId,
        mail=user.mail,
        name=user.name,
        passwordHash=user.passwordHash,
        role=user.role,
        createAccountData=user.createAccountData,
        lastVIsitData=currentTime,
        countOfPictures=user.countOfPictures
    )

    # Сохраняем в БД
    db.updateUser(updatedUser)

    # Возвращаем успешный результат
    return AuthResult(
        code=0,
        user=updatedUser,
        message="Аутентификация успешна"
    )

