import cv2
import numpy as np
import torch
import torch.nn.functional as F
from facenet_pytorch import MTCNN, InceptionResnetV1
from PIL import Image
from typing import List, Tuple, Optional, Union
import warnings

warnings.filterwarnings('ignore')


class FaceDetector:
    """
    Класс для обнаружения лиц и получения эмбеддингов с использованием нейросетей.
    Использует MTCNN для детекции и InceptionResnetV1 для эмбеддингов.
    """

    def __init__(
            self,
            device: Optional[str] = None,
            min_face_size: int = 20,
            thresholds: Optional[List[float]] = None,
            post_process: bool = True,
            margin: int = 20
    ):
        """
        Инициализация детектора лиц.

        Args:
            device: Устройство для вычислений ('cuda', 'cpu', None - автоопределение)
            min_face_size: Минимальный размер лица в пикселях
            thresholds: Пороги для MTCNN (P-Net, R-Net, O-Net)
            post_process: Постобработка результатов
            margin: Отступ вокруг лица при извлечении
        """
        # Устанавливаем значения по умолчанию для thresholds
        if thresholds is None:
            thresholds = [0.6, 0.7, 0.7]

        # Определяем устройство
        if device is None:
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        else:
            self.device = torch.device(device)

        print(f"Используется устройство: {self.device}")

        # Инициализируем MTCNN для детекции лиц
        self.mtcnn = MTCNN(
            image_size=160,
            margin=margin,
            min_face_size=min_face_size,
            thresholds=thresholds,
            post_process=post_process,
            device=self.device,
            keep_all=True
        )

        # Инициализируем модель для получения эмбеддингов
        self.resnet = InceptionResnetV1(pretrained='vggface2').eval().to(self.device)

        # Параметры
        self.margin = margin

    def detectFaces(
            self,
            image: Union[str, np.ndarray, Image.Image],
            returnBoxes: bool = True,
            returnEmbeddings: bool = True
    ) -> Union[
        Tuple[Optional[List[np.ndarray]], Optional[np.ndarray]],
        Optional[List[np.ndarray]],
        Optional[np.ndarray],
        None
    ]:
        """
        Обнаружение лиц на изображении.

        Args:
            image: Путь к изображению, массив numpy или PIL Image
            returnBoxes: Возвращать ли координаты боксов лиц
            returnEmbeddings: Возвращать ли эмбеддинги

        Returns:
            В зависимости от параметров возвращает:
            - (boxes, embeddings): если returnBoxes и returnEmbeddings
            - boxes: если только returnBoxes
            - embeddings: если только returnEmbeddings
            - None: если лица не найдены или оба параметра False
        """
        # Загружаем изображение
        img = self._loadImage(image)

        # Получаем все лица и их координаты
        boxes = self._getFacesBoxes(img)

        if boxes is None or len(boxes) == 0:
            if returnBoxes and returnEmbeddings:
                return None, None
            elif returnBoxes:
                return None
            elif returnEmbeddings:
                return None
            else:
                return None

        # Получаем эмбеддинги для всех лиц
        embeddings = None
        if returnEmbeddings:
            embeddings = self._getEmbeddings(img, boxes)

        if returnBoxes and returnEmbeddings:
            return boxes, embeddings
        elif returnBoxes:
            return boxes
        elif returnEmbeddings:
            return embeddings
        else:
            return None

    def _loadImage(self, image: Union[str, np.ndarray, Image.Image]) -> np.ndarray:
        """Загрузка изображения в формате RGB numpy array."""
        if isinstance(image, str):
            # Загрузка из файла
            img = cv2.imread(image)
            if img is None:
                raise ValueError(f"Не удалось загрузить изображение: {image}")
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        elif isinstance(image, np.ndarray):
            img = image.copy()
            if len(img.shape) == 2:  # Черно-белое
                img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
            elif img.shape[2] == 4:  # RGBA
                img = cv2.cvtColor(img, cv2.COLOR_RGBA2RGB)
            elif img.shape[2] == 3 and img.dtype == np.uint8:
                # Предполагаем, что это RGB
                pass
            else:
                raise ValueError(f"Неподдерживаемый формат изображения: {img.shape}")
        elif isinstance(image, Image.Image):
            img = np.array(image.convert('RGB'))
        else:
            raise ValueError(f"Неподдерживаемый тип изображения: {type(image)}")

        return img

    def _getFacesBoxes(
            self,
            img: np.ndarray
    ) -> Optional[List[np.ndarray]]:
        """
        Получение боксов лиц с помощью MTCNN.

        Returns:
            Список боксов [x1, y1, x2, y2] или None
        """
        # Конвертируем в PIL Image для MTCNN
        img_pil = Image.fromarray(img)

        # Детекция лиц
        boxes, probs = self.mtcnn.detect(img_pil)

        if boxes is None:
            return None

        # Приводим к целым числам и конвертируем в список
        boxes = boxes.astype(int)
        boxes_list = [box for box in boxes]

        return boxes_list

    def _getEmbeddings(
            self,
            img: np.ndarray,
            boxes: List[np.ndarray]
    ) -> np.ndarray:
        """
        Получение эмбеддингов для каждого лица.

        Args:
            img: Исходное изображение
            boxes: Список координат лиц

        Returns:
            embeddings: Массив эмбеддингов размером (n_faces, 512)
        """
        embeddings = []

        for box in boxes:
            # Извлекаем лицо из изображения
            face_img = self._extractFace(img, box)

            if face_img is not None:
                # Нормализуем изображение
                face_tensor = self._preprocessFace(face_img)

                # Получаем эмбеддинг
                with torch.no_grad():
                    embedding = self.resnet(face_tensor.unsqueeze(0))
                    embedding = F.normalize(embedding).cpu().numpy()

                embeddings.append(embedding.flatten())

        if not embeddings:
            return np.array([])

        return np.array(embeddings)

    def _extractFace(
            self,
            img: np.ndarray,
            box: np.ndarray,
            target_size: Tuple[int, int] = (160, 160)
    ) -> Optional[np.ndarray]:
        """
        Извлечение и выравнивание лица по координатам.

        Args:
            img: Исходное изображение
            box: Координаты лица [x1, y1, x2, y2]
            target_size: Целевой размер изображения лица

        Returns:
            face_img: Вырезанное и выровненное лицо
        """
        x1, y1, x2, y2 = box

        # Добавляем отступы
        h, w = img.shape[:2]
        x1 = max(0, x1 - self.margin // 2)
        y1 = max(0, y1 - self.margin // 2)
        x2 = min(w, x2 + self.margin // 2)
        y2 = min(h, y2 + self.margin // 2)

        # Вырезаем лицо
        face = img[y1:y2, x1:x2]

        if face.size == 0:
            return None

        # Изменяем размер
        face = cv2.resize(face, target_size, interpolation=cv2.INTER_LINEAR)

        return face

    def _preprocessFace(self, face_img: np.ndarray) -> torch.Tensor:
        """
        Предобработка изображения лица для нейросети.

        Args:
            face_img: Изображение лица в формате RGB

        Returns:
            face_tensor: Тензор для подачи в сеть
        """
        # Конвертируем в тензор и нормализуем
        face_tensor = torch.from_numpy(face_img).float().permute(2, 0, 1)
        face_tensor = face_tensor / 255.0  # [0, 1]

        # Нормализация как в VGGFace2
        mean = torch.tensor([0.5, 0.5, 0.5]).view(3, 1, 1)
        std = torch.tensor([0.5, 0.5, 0.5]).view(3, 1, 1)
        face_tensor = (face_tensor - mean) / std

        return face_tensor.to(self.device)

    def getEmbeddingsBatch(
            self,
            images: List[Union[str, np.ndarray, Image.Image]]
    ) -> List[Optional[np.ndarray]]:
        """
        Получение эмбеддингов для списка изображений.

        Args:
            images: Список изображений

        Returns:
            embeddings: Список эмбеддингов для каждого изображения
        """
        results = []
        for image in images:
            _, embeddings = self.detectFaces(image, returnBoxes=True, returnEmbeddings=True)
            results.append(embeddings)

        return results

    def compareFaces(
            self,
            face1: Union[str, np.ndarray, Image.Image],
            face2: Union[str, np.ndarray, Image.Image],
            threshold: float = 0.6
    ) -> Tuple[bool, float]:
        """
        Сравнение двух лиц.

        Args:
            face1: Первое лицо (изображение)
            face2: Второе лицо (изображение)
            threshold: Порог схожести (меньше - более строгое сравнение)

        Returns:
            is_same: Являются ли лица одним человеком
            similarity: Значение схожести (косинусное расстояние)
        """
        # Получаем эмбеддинги
        boxes1, emb1 = self.detectFaces(face1, returnBoxes=True, returnEmbeddings=True)
        boxes2, emb2 = self.detectFaces(face2, returnBoxes=True, returnEmbeddings=True)

        if emb1 is None or len(emb1) == 0:
            raise ValueError("Не удалось обнаружить лицо на первом изображении")

        if emb2 is None or len(emb2) == 0:
            raise ValueError("Не удалось обнаружить лицо на втором изображении")

        # Если найдено несколько лиц, берем первое (или можно выбрать по наибольшему размеру)
        emb1 = emb1[0]
        emb2 = emb2[0]

        # Вычисляем косинусное расстояние
        similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))

        return similarity > threshold, similarity

    def getFaceCount(self, image: Union[str, np.ndarray, Image.Image]) -> int:
        """
        Получение количества лиц на изображении.

        Args:
            image: Изображение

        Returns:
            Количество обнаруженных лиц
        """
        boxes = self.detectFaces(image, returnBoxes=True, returnEmbeddings=False)
        if boxes is None:
            return 0
        return len(boxes)
