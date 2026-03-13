"""
Модуль для приведения слов к нормальной форме.
"""

from typing import List
from mawo_pymorphy3 import create_analyzer

# Создаём анализатор один раз при импорте модуля
_analyzer = create_analyzer()

def normalizeText(text: str) -> List[str]:
    """
    Приводит все слова в тексте к нормальной форме.

    Args:
        text (str): "Мы купили красивые машины"
    Returns:
        List[str]: ['мы', 'купить', 'красивый', 'машина']
    """

    if not text or not isinstance(text, str):
        return []

    words: List[str] = text.lower().split()
    result: List[str] = []

    for word in words:
        try:
            # Берём нормальную форму слова
            normal: str = _analyzer.parse(word)[0].normal_form
            result.append(normal)
        except (IndexError, AttributeError):
            # Если что-то пошло не так, оставляем как есть
            result.append(word)

    return result