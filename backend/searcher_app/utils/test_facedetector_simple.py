# test_mtcnn.py
import time
import sys

print("=" * 70)
print("ТЕСТИРОВАНИЕ FaceDetector (MTCNN + InceptionResnetV1)")
print("=" * 70)
print(f"Python: {sys.version.split()[0]}")
print()

try:
    from faceDetector import FaceDetector
    
    # Инициализация
    print("1. Инициализация детектора")
    print("-" * 40)
    start = time.time()
    detector = FaceDetector(device='cpu')
    init_time = time.time() - start
    print(f"⏱ Время инициализации: {init_time:.2f} сек")
    print()
    
    # Детекция лиц
    print("2. Детекция лиц")
    print("-" * 40)
    start = time.time()
    count = detector.getFaceCount("nikita.jpg")
    detect_time = time.time() - start
    print(f"⏱ Время детекции: {detect_time:.3f} сек")
    print(f"👤 Найдено лиц: {count}")
    print()
    
    # Получение эмбеддингов
    print("3. Получение эмбеддингов")
    print("-" * 40)
    start = time.time()
    boxes, embeddings = detector.detectFaces("nikita.jpg", returnBoxes=True, returnEmbeddings=True)
    embed_time = time.time() - start
    print(f"⏱ Время получения эмбеддингов: {embed_time:.3f} сек")
    print()
    
    # Результаты
    print("4. Результаты")
    print("-" * 40)
    print(f"📊 Координаты лица: {boxes[0]}")
    print(f"📊 Размер эмбеддинга: {len(embeddings[0])}")
    print(f"📊 Первые 5 значений: {[round(x, 4) for x in embeddings[0][:5]]}")
    print()
    
    # Итоговое время
    total_time = init_time + detect_time + embed_time
    print("=" * 70)
    print(f"✅ ИТОГОВОЕ ВРЕМЯ: {total_time:.2f} сек")
    print(f"   - Инициализация: {init_time:.2f} сек")
    print(f"   - Детекция: {detect_time:.3f} сек")
    print(f"   - Эмбеддинги: {embed_time:.3f} сек")
    print("=" * 70)
    print("\n✅ FaceDetector (MTCNN) работает успешно!")
    
except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()