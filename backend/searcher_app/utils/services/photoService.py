# Получает: фото
# Последовательность:
# 1. PhotoHandler → описание
# 2. KeyWordsDetector → ключевые слова
# 3. SynonymGenerator → синонимы
# 4. FaceDetector → эмбеддинги лиц

# Возвращает:
# {
#     'extractEmbeddings': list,       # векторы лиц
#     'detectFaces': int,              # лица
#     'extractKeywords': list,         # ключевые слова
#     'synonyms': list,                # синонимы
# }