import torch
from PIL import Image
from transformers import BlipProcessor, BlipForConditionalGeneration
from transformers import CLIPProcessor, CLIPModel
from typing import Union, List, Optional

# Добавляем путь для импорта
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from translator import Translator

class PhotoHandler:
    """
    Класс для генерации текстового описания изображения c помощью BLIP и/или CLIP.
    """

    def __init__(self, device: Optional[str] = None):
        """
        Инициализация моделей BLIP и CLIP.
        :param device: 'cuda' или 'cpu'. Если None, выбирается автоматически.
        """
        self.device = device or ('cuda' if torch.cuda.is_available() else 'cpu')
        print(f"Инициализация на устройстве: {self.device}")
        
        # BLIP
        print("Загрузка BLIP модели...")
        self.blip_processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
        self.blip_model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base").to(self.device)
        print("✓ BLIP загружен")
        
        # CLIP через transformers
        print("Загрузка CLIP модели (через transformers)...")
        self.clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(self.device)
        self.clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        print("✓ CLIP загружен")
        
        self.translator = Translator()
        print("✓ Переводчик загружен")

    def describe_with_blip(self, image: Image.Image) -> str:
        """
        Генерирует описание изображения c помощью BLIP.
        :param image: PIL Image
        :return: текстовое описание (на английском)
        """
        inputs = self.blip_processor(image, return_tensors="pt").to(self.device)
        out = self.blip_model.generate(**inputs, max_length=50)
        description = self.blip_processor.decode(out[0], skip_special_tokens=True)
        return description

    def describe_with_clip(self, image: Image.Image, candidate_descriptions: List[str]) -> str:
        """
        Выбирает наиболее подходящее описание из списка кандидатов c помощью CLIP.
        :param image: PIL Image
        :param candidate_descriptions: список возможных описаний
        :return: лучшее описание (на английском)
        """
        inputs = self.clip_processor(
            text=candidate_descriptions, 
            images=image, 
            return_tensors="pt", 
            padding=True
        ).to(self.device)
        
        with torch.no_grad():
            outputs = self.clip_model(**inputs)
            # logits_per_image показывает соответствие изображения каждому тексту
            logits_per_image = outputs.logits_per_image
            best_idx = logits_per_image.argmax().item()
        
        return candidate_descriptions[best_idx]

    def describe_combined(self, image: Image.Image, candidate_descriptions: Optional[List[str]] = None) -> str:
        """
        Комбинированный метод:
        - Если передан candidate_descriptions, использует CLIP для выбора лучшего.
        - Если нет — генерирует описание через BLIP.
        :param image: PIL Image
        :param candidate_descriptions: опциональный список описаний
        :return: описание (на английском)
        """
        if candidate_descriptions:
            return self.describe_with_clip(image, candidate_descriptions)
        else:
            return self.describe_with_blip(image)

    def get_description(self, image: Image.Image, lang: str = "ru") -> str:
        """
        Основной метод для внешнего вызова.
        Возвращает описание изображения на указанном языке.
        :param image: PIL Image
        :param lang: 'ru' или 'en'
        :return: описание на нужном языке
        """
        description_en = self.describe_combined(image)
        if lang == "ru":
            return self.translator.translate(description_en)
        return description_en