"""
Модуль для извлечения ключевых слов из текста с использованием Navec.
Модель скачивается автоматически при первом запуске.
"""

from typing import List, Set, Tuple
import numpy as np
from numpy import ndarray
from navec import Navec
from wordNormalizer import normalizeText
import re


def get_navec_model():
    """Возвращает модель Navec, скачивая при необходимости."""
    try:
        from navec import download_navec
        model_path = download_navec()
        return Navec.load(model_path)
    except ImportError:
        import urllib.request
        from pathlib import Path

        cache_dir = Path.home() / '.cache' / 'navec'
        cache_dir.mkdir(parents=True, exist_ok=True)

        model_path = cache_dir / 'navec_news_v1_1B_250K_300d_100q.tar'

        if not model_path.exists():
            print("📥 Скачивание модели Navec (25 МБ)...")
            url = "https://storage.yandexcloud.net/natasha-navec/packs/navec_news_v1_1B_250K_300d_100q.tar"
            urllib.request.urlretrieve(url, model_path)
            print("✅ Готово!")

        return Navec.load(str(model_path))


class KeyWordsDetector:
    """Детектор ключевых слов с приоритетом существительных."""

    def __init__(self) -> None:
        """Инициализация детектора. Скачивает модель при необходимости."""
        self._navec = get_navec_model()

        # Окончания прилагательных
        self._adjEndings: Tuple[str, ...] = ('ый', 'ий', 'ой', 'ая', 'ое', 'ые', 'ие')

        # Стоп-слова
        self._stopWords: Set[str] = {
            'и', 'в', 'на', 'с', 'по', 'для', 'а', 'но',
            'или', 'из', 'у', 'к', 'о', 'об', 'от', 'до',
            'без', 'над', 'под', 'за', 'при', 'про', 'через',
            'этот', 'тот', 'весь', 'свой', 'наш', 'ваш', 'мой',
            'быть', 'стать', 'мочь', 'хотеть', 'гулять', 'ходить',
            'сказать', 'говорить', 'смотреть', 'видеть'
        }

    def _isAdjective(self, word: str) -> bool:
        """Проверяет, является ли слово прилагательным по окончанию."""
        return word.endswith(self._adjEndings)

    def extractKeywords(self, text: str, maxWords: int = 5) -> List[str]:
        """
        Извлекает ключевые слова с приоритетом существительных.

        Args:
            text: входной текст
            maxWords: максимальное количество слов

        Returns:
            List[str]: ключевые слова
        """
        if not text or not isinstance(text, str):
            return []

        # Очистка от знаков препинания
        text = re.sub(r'[^\w\s-]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()

        # Нормализация
        words = normalizeText(text.lower())

        # Фильтрация стоп-слов и коротких слов
        filtered = [w for w in words if len(w) > 2 and w not in self._stopWords]

        if not filtered:
            return []

        # Разделяем на существительные и прилагательные
        nouns: List[str] = []
        adjectives: List[str] = []

        for word in filtered:
            if self._isAdjective(word):
                adjectives.append(word)
            else:
                nouns.append(word)

        # Оцениваем все слова
        wordScores: List[Tuple[str, float]] = []

        # Существительные с бонусом x2
        for word in nouns:
            if word in self._navec:
                vec: ndarray = self._navec[word]
                score: float = float(np.linalg.norm(vec)) * 2.0
                wordScores.append((word, score))
            else:
                wordScores.append((word, float(len(word)) * 2.0))

        # Прилагательные без бонуса
        for word in adjectives:
            if word in self._navec:
                vec: ndarray = self._navec[word]
                score: float = float(np.linalg.norm(vec))
                wordScores.append((word, score))
            else:
                wordScores.append((word, float(len(word))))

        # Сортировка по убыванию важности
        wordScores.sort(key=lambda x: x[1], reverse=True)

        # Убираем дубликаты
        result: List[str] = []
        seen: Set[str] = set()
        for word, _ in wordScores:
            if word not in seen:
                seen.add(word)
                result.append(word)

        return result[:maxWords]

    def addStopWords(self, words: List[str]) -> None:
        """Добавляет новые стоп-слова."""
        self._stopWords.update(words)

    def removeStopWords(self, words: List[str]) -> None:
        """Удаляет слова из списка стоп-слов."""
        for word in words:
            self._stopWords.discard(word)

    def getStopWords(self) -> List[str]:
        """Возвращает текущий список стоп-слов."""
        return sorted(list(self._stopWords))


def extractKeywords(text: str, maxWords: int = 5) -> List[str]:
    """Упрощённая функция для быстрого извлечения ключевых слов."""
    detector = KeyWordsDetector()
    return detector.extractKeywords(text, maxWords)


