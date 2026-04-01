# test_deepface.py
import time
import sys

print("=" * 70)
print("ТЕСТИРОВАНИЕ FaceDetector (DeepFace)")
print("=" * 70)
print(f"Python: {sys.version.split()[0]}")
print()

try:
    from faceDetectorDeepFace import FaceDetector
    
    # Инициализация
    print("1. Инициализация детектора")
    print("-" * 40)
    start = time.time()
    detector = FaceDetector(modelName='Facenet', detectorBackend='opencv')
    init_time = time.time() - start
    print(f"⏱ Время инициализации: {init_time:.2f} сек")
    print()
    
    # Детекция лиц
    print("2. Детекция лиц")
    print("-" * 40)
    start = time.time()
    faces = detector.detectFaces("image1.jpg")
    detect_time = time.time() - start
    print(f"⏱ Время детекции: {detect_time:.3f} сек")
    print(f"👤 Найдено лиц: {len(faces)}")
    if faces:
        print(f"📊 Координаты лиц: {faces}")
    print()
    
    # Получение эмбеддингов
    print("3. Получение эмбеддингов")
    print("-" * 40)
    start = time.time()
    embeddings = detector.extractEmbeddings("nikita.jpg")
    embed_time = time.time() - start
    print(f"⏱ Время получения эмбеддингов: {embed_time:.3f} сек")
    print()
    
    # Результаты
    print("4. Результаты")
    print("-" * 40)
    if embeddings:
        print(f"📊 Количество эмбеддингов: {len(embeddings)}")
        print(f"📊 Размер эмбеддинга: {len(embeddings[0])}")
        print(f"📊 Первые 5 значений: {[round(x, 4) for x in embeddings[0][:5]]}")
    else:
        print("⚠️ Эмбеддинги не получены")
    print()
    
    # Итоговое время
    total_time = init_time + detect_time + embed_time
    print("=" * 70)
    print(f"✅ ИТОГОВОЕ ВРЕМЯ: {total_time:.2f} сек")
    print(f"   - Инициализация: {init_time:.2f} сек")
    print(f"   - Детекция: {detect_time:.3f} сек")
    print(f"   - Эмбеддинги: {embed_time:.3f} сек")
    print("=" * 70)
    print("\n✅ FaceDetector (DeepFace) работает успешно!")
    
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    print("\nРешение:")
    print("  pip install deepface tensorflow")
    print("  Примечание: DeepFace несовместим с Python 3.14")
    
except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()