from googletrans import Translator as GoogleTranslator
from typing import Optional

class Translator:
    """
    Класс для перевода текста  с английского на русский с помощью Google Translate.
    """

    def __init__(self):
        self.translator = GoogleTranslator()

    def translate(self, text: str, dest: str = "ru", src: str = "en") -> Optional[str]:
        """
        Переводит текст с английского на русский.
        :param text: исходный текст
        :param dest: целевой язык (по умолчанию русский)
        :param src: исходный язык (по умолчанию английский)
        :return: переведённый текст или None в случае ошибки
        """
        try:
            result = self.translator.translate(text, src=src, dest=dest)
            return result.text
        except Exception as e:
            print(f"[Translator] Ошибка перевода: {e}")
            return None