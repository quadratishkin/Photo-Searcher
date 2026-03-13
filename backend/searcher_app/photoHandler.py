import torch
from PIL import Image
from transformers import BlipProcessor, BlipForConditionalGeneration
import clip
from typing import Union, List, Optional
from backend.searcher_app.translator import Translator

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
        
        # BLIP
        self.blip_processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
        self.blip_model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base").to(self.device)
        
        # CLIP
        self.clip_model, self.clip_preprocess = clip.load("ViT-B/32", device=self.device)
        
        self.translator = Translator()

    def describe_with_blip(self, image: Image.Image) -> str:
        """
        Генерирует описание изображения c помощью BLIP.
        :param image: PIL Image
        :return: текстовое описание (на английском)
        """
        inputs = self.blip_processor(image, return_tensors="pt").to(self.device)
        out = self.blip_model.generate(**inputs)
        description = self.blip_processor.decode(out[0], skip_special_tokens=True)
        return description

    def describe_with_clip(self, image: Image.Image, candidate_descriptions: List[str]) -> str:
        """
        Выбирает наиболее подходящее описание из списка кандидатов c помощью CLIP.
        :param image: PIL Image
        :param candidate_descriptions: список возможных описаний
        :return: лучшее описание (на английском)
        """
        image_input = self.clip_preprocess(image).unsqueeze(0).to(self.device)
        text_tokens = clip.tokenize(candidate_descriptions).to(self.device)

        with torch.no_grad():
            image_features = self.clip_model.encode_image(image_input)
            text_features = self.clip_model.encode_text(text_tokens)
            similarity = (image_features @ text_features.T).squeeze(0)
            best_idx = similarity.argmax().item()

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
