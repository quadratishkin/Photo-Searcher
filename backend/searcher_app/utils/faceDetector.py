"""
Модуль для обнаружения лиц и извлечения эмбеддингов с использованием DeepFace.
"""

from __future__ import annotations

from typing import Any, List
from deepface import DeepFace


class FaceDetector:
    """
    Детектор лиц на изображениях с извлечением эмбеддингов.

    Пример:
        >>> detector = FaceDetector()
        >>> faces = detector.detectFaces('photo.jpg')
        >>> embeddings = detector.extractEmbeddings('photo.jpg')
    """

    def __init__(self, modelName: str = 'Facenet', detectorBackend: str = 'opencv') -> None:
        """
        Инициализация детектора лиц.

        Args:
            modelName: модель для эмбеддингов ('Facenet', 'Facenet512', 'ArcFace')
            detectorBackend: бэкенд для детекции ('opencv', 'mtcnn', 'retinaface')
        """
        self._modelName = modelName
        self._detectorBackend = detectorBackend
        self._model = DeepFace.build_model(modelName)

    def detectFaces(self, imagePath: str) -> List[Any]:
        """
        Обнаруживает лица на изображении и возвращает их координаты.

        Args:
            imagePath: путь к изображению

        Returns:
            List[Any]: список координат лиц [x, y, w, h]
        """
        try:
            faces = DeepFace.extract_faces(
                img_path=imagePath,
                detector_backend=self._detectorBackend,
                enforce_detection=False
            )

            result = []
            for face in faces:
                area = face.get('facial_area', {})
                result.append([
                    area.get('x', 0),
                    area.get('y', 0),
                    area.get('w', 0),
                    area.get('h', 0)
                ])
            return result

        except Exception:
            return []

    def extractEmbeddings(self, imagePath: str) -> List[List[float]]:
        """
        Извлекает эмбеддинги для всех лиц на изображении.

        Args:
            imagePath: путь к изображению

        Returns:
            List[List[float]]: список эмбеддингов (каждый эмбеддинг - список float)
        """
        try:
            results = DeepFace.represent(
                img_path=imagePath,
                model_name=self._modelName,
                detector_backend=self._detectorBackend,
                enforce_detection=False
            )

            embeddings = []
            for r in results:
                if isinstance(r, dict) and 'embedding' in r:
                    embeddings.append(r['embedding'])
                elif isinstance(r, list):
                    embeddings.append(r)

            return embeddings

        except Exception:
            return []