from deep_translator import GoogleTranslator
from typing import Optional

class Translator:
    """
    Класс для перевода текста с английского на русский.
    """
    
    def __init__(self):
        self.translator = GoogleTranslator(source='en', target='ru')
    
    def translate(self, text: str) -> Optional[str]:
        """
        Переводит текст с английского на русский.
        :param text: исходный текст
        :return: переведённый текст или None в случае ошибки
        """
        try:
            return self.translator.translate(text)
        except Exception as e:
            print(f"[Translator] Ошибка перевода: {e}")
            return None

# Использование
trans = Translator()
result = trans.translate("hello world")
print(result)