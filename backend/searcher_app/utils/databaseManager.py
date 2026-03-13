from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_DB_PATH = Path(__file__).resolve().parents[3] / "photo_searcher.sqlite3"


@dataclass
class UserRecord:
    userId: int | None
    mail: str
    name: str
    passwordHash: str
    role: str = "user"
    createAccountData: str | None = None
    lastVIsitData: str | None = None
    countOfPictures: int = 0


@dataclass
class PhotoRecord:
    photoId: int | None
    userId: int
    filePath: str
    keyWords: list[str]
    vectors: bytes | None = None


@dataclass
class KeywordSynonymRecord:
    id: int | None
    baseWord: str
    normalizedBaseWord: str
    synonymWord: str
    normalizedSynonymWord: str
    source: str = "generated"


class DatabaseManager:
    def __init__(self, dbPath: str | Path = DEFAULT_DB_PATH) -> None:
        self.dbPath = Path(dbPath)
        self.dbPath.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.dbPath)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.initializeDatabase()

    def initializeDatabase(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                mail TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                passwordHash TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('admin', 'user')),
                createAccountData TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                lastVIsitData TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                countOfPictures INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS photos (
                photo_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                filePath TEXT NOT NULL,
                keyWords TEXT NOT NULL DEFAULT '[]',
                vectors BLOB,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS keyword_synonyms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                base_word TEXT NOT NULL,
                normalized_base_word TEXT NOT NULL,
                synonym_word TEXT NOT NULL,
                normalized_synonym_word TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'generated',
                UNIQUE (normalized_base_word, normalized_synonym_word)
            );

            CREATE INDEX IF NOT EXISTS idx_users_mail ON users(mail);
            CREATE INDEX IF NOT EXISTS idx_photos_user_id ON photos(user_id);
            CREATE INDEX IF NOT EXISTS idx_synonyms_base_word ON keyword_synonyms(normalized_base_word);
            """
        )
        self.connection.commit()

    def addUser(self, record: UserRecord) -> UserRecord:
        cursor = self.connection.execute(
            """
            INSERT INTO users (
                mail,
                name,
                passwordHash,
                role,
                createAccountData,
                lastVIsitData,
                countOfPictures
            )
            VALUES (?, ?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP), COALESCE(?, CURRENT_TIMESTAMP), ?)
            """,
            (
                record.mail,
                record.name,
                record.passwordHash,
                record.role,
                record.createAccountData,
                record.lastVIsitData,
                record.countOfPictures,
            ),
        )
        self.connection.commit()
        createdRecord = self.findUserById(cursor.lastrowid)
        if createdRecord is None:
            raise RuntimeError("Failed to load the created user record.")
        return createdRecord

    def deleteUser(self, userId: int) -> bool:
        cursor = self.connection.execute(
            """
            DELETE FROM users
            WHERE user_id = ?
            """,
            (userId,),
        )
        self.connection.commit()
        return cursor.rowcount > 0

    def findUserById(self, userId: int) -> UserRecord | None:
        row = self.connection.execute(
            """
            SELECT *
            FROM users
            WHERE user_id = ?
            """,
            (userId,),
        ).fetchone()
        if row is None:
            return None
        return self._mapUser(row)

    def findUserByMail(self, mail: str) -> UserRecord | None:
        row = self.connection.execute(
            """
            SELECT *
            FROM users
            WHERE mail = ?
            """,
            (mail,),
        ).fetchone()
        if row is None:
            return None
        return self._mapUser(row)

    def updateUser(self, record: UserRecord) -> UserRecord | None:
        if record.userId is None:
            raise ValueError("UserRecord.userId must be set for updateUser.")

        self.connection.execute(
            """
            UPDATE users
            SET mail = ?,
                name = ?,
                passwordHash = ?,
                role = ?,
                createAccountData = COALESCE(?, createAccountData),
                lastVIsitData = COALESCE(?, lastVIsitData),
                countOfPictures = ?
            WHERE user_id = ?
            """,
            (
                record.mail,
                record.name,
                record.passwordHash,
                record.role,
                record.createAccountData,
                record.lastVIsitData,
                record.countOfPictures,
                record.userId,
            ),
        )
        self.connection.commit()
        return self.findUserById(record.userId)

    def addRecord(self, record: PhotoRecord) -> PhotoRecord:
        cursor = self.connection.execute(
            """
            INSERT INTO photos (user_id, filePath, keyWords, vectors)
            VALUES (?, ?, ?, ?)
            """,
            (
                record.userId,
                record.filePath,
                json.dumps(record.keyWords, ensure_ascii=False),
                record.vectors,
            ),
        )
        self._refreshCountOfPictures(record.userId)
        self.connection.commit()
        createdRecord = self.findRecord(cursor.lastrowid, record.userId)
        if createdRecord is None:
            raise RuntimeError("Failed to load the created photo record.")
        return createdRecord

    def deleteRecord(self, recordId: int, userId: int) -> bool:
        cursor = self.connection.execute(
            """
            DELETE FROM photos
            WHERE photo_id = ? AND user_id = ?
            """,
            (recordId, userId),
        )
        self._refreshCountOfPictures(userId)
        self.connection.commit()
        return cursor.rowcount > 0

    def findRecord(self, recordId: int, userId: int) -> PhotoRecord | None:
        row = self.connection.execute(
            """
            SELECT *
            FROM photos
            WHERE photo_id = ? AND user_id = ?
            """,
            (recordId, userId),
        ).fetchone()
        if row is None:
            return None
        return self._mapPhoto(row)

    def findRecordsByUser(self, userId: int) -> list[PhotoRecord]:
        rows = self.connection.execute(
            """
            SELECT *
            FROM photos
            WHERE user_id = ?
            ORDER BY photo_id DESC
            """,
            (userId,),
        ).fetchall()
        return [self._mapPhoto(row) for row in rows]

    def findRecordsByKeyword(self, keyword: str, userId: int) -> list[PhotoRecord]:
        normalizedKeyword = keyword.strip().lower()
        rows = self.connection.execute(
            """
            SELECT *
            FROM photos
            WHERE user_id = ?
            ORDER BY photo_id DESC
            """,
            (userId,),
        ).fetchall()

        matchedRecords: list[PhotoRecord] = []
        for row in rows:
            record = self._mapPhoto(row)
            normalizedKeywords = [item.strip().lower() for item in record.keyWords]
            if normalizedKeyword in normalizedKeywords:
                matchedRecords.append(record)
        return matchedRecords

    def updatePhoto(self, record: PhotoRecord) -> PhotoRecord | None:
        if record.photoId is None:
            raise ValueError("PhotoRecord.photoId must be set for updatePhoto.")

        self.connection.execute(
            """
            UPDATE photos
            SET filePath = ?,
                keyWords = ?,
                vectors = ?
            WHERE photo_id = ? AND user_id = ?
            """,
            (
                record.filePath,
                json.dumps(record.keyWords, ensure_ascii=False),
                record.vectors,
                record.photoId,
                record.userId,
            ),
        )
        self.connection.commit()
        return self.findRecord(record.photoId, record.userId)

    def addSynonym(self, synonym: KeywordSynonymRecord) -> KeywordSynonymRecord:
        self.connection.execute(
            """
            INSERT OR IGNORE INTO keyword_synonyms (
                base_word,
                normalized_base_word,
                synonym_word,
                normalized_synonym_word,
                source
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                synonym.baseWord,
                synonym.normalizedBaseWord,
                synonym.synonymWord,
                synonym.normalizedSynonymWord,
                synonym.source,
            ),
        )
        self.connection.commit()
        row = self.connection.execute(
            """
            SELECT *
            FROM keyword_synonyms
            WHERE normalized_base_word = ? AND normalized_synonym_word = ?
            """,
            (synonym.normalizedBaseWord, synonym.normalizedSynonymWord),
        ).fetchone()
        if row is None:
            raise RuntimeError("Failed to load the synonym record.")
        return self._mapSynonym(row)

    def getSynonyms(self, normalizedBaseWord: str) -> list[KeywordSynonymRecord]:
        rows = self.connection.execute(
            """
            SELECT *
            FROM keyword_synonyms
            WHERE normalized_base_word = ?
            ORDER BY id ASC
            """,
            (normalizedBaseWord,),
        ).fetchall()
        return [self._mapSynonym(row) for row in rows]

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> DatabaseManager:
        return self

    def __exit__(self, excType: type[BaseException] | None, exc: BaseException | None, excTb: Any) -> None:
        self.close()

    def _refreshCountOfPictures(self, userId: int) -> None:
        self.connection.execute(
            """
            UPDATE users
            SET countOfPictures = (
                SELECT COUNT(*)
                FROM photos
                WHERE photos.user_id = users.user_id
            )
            WHERE user_id = ?
            """,
            (userId,),
        )

    def _mapUser(self, row: sqlite3.Row) -> UserRecord:
        return UserRecord(
            userId=row["user_id"],
            mail=row["mail"],
            name=row["name"],
            passwordHash=row["passwordHash"],
            role=row["role"],
            createAccountData=row["createAccountData"],
            lastVIsitData=row["lastVIsitData"],
            countOfPictures=row["countOfPictures"],
        )

    def _mapPhoto(self, row: sqlite3.Row) -> PhotoRecord:
        return PhotoRecord(
            photoId=row["photo_id"],
            userId=row["user_id"],
            filePath=row["filePath"],
            keyWords=json.loads(row["keyWords"]),
            vectors=row["vectors"],
        )

    def _mapSynonym(self, row: sqlite3.Row) -> KeywordSynonymRecord:
        return KeywordSynonymRecord(
            id=row["id"],
            baseWord=row["base_word"],
            normalizedBaseWord=row["normalized_base_word"],
            synonymWord=row["synonym_word"],
            normalizedSynonymWord=row["normalized_synonym_word"],
            source=row["source"],
        )
