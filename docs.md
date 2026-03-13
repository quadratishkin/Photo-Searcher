# Project Notes

## Что приведено в соответствие с последним сообщением Никиты

### База данных

Файл: [searcher_app/utils/databaseManager.py](/Users/xmodern/Documents/Photo-Searcher/searcher_app/utils/databaseManager.py)

Используется SQLite.

Создаются таблицы:

1. `users`
- `user_id`
- `mail`
- `name`
- `passwordHash`
- `role`
- `createAccountData`
- `lastVIsitData`
- `countOfPictures`

2. `photos`
- `photo_id`
- `user_id`
- `filePath`
- `keyWords`
- `vectors`

Дополнительно оставлена служебная таблица `keyword_synonyms`, чтобы не ломать уже сделанный `synonymGenerator`.

Основные методы:
- `addUser`
- `deleteUser`
- `findUserById`
- `findUserByMail`
- `updateUser`
- `addRecord`
- `deleteRecord`
- `findRecord`
- `findRecordsByUser`
- `findRecordsByKeyword`
- `updatePhoto`

### Дополнительные классы

Файл: [searcher_app/utils/user.py](/Users/xmodern/Documents/Photo-Searcher/searcher_app/utils/user.py)
- класс `User`

Файл: [searcher_app/utils/admin.py](/Users/xmodern/Documents/Photo-Searcher/searcher_app/utils/admin.py)
- класс `Admin`

Файл: [searcher_app/utils/requestQueue.py](/Users/xmodern/Documents/Photo-Searcher/searcher_app/utils/requestQueue.py)
- класс `RequestQueue`
- лимит по умолчанию `50`

Файл: [searcher_app/utils/hashFunction.py](/Users/xmodern/Documents/Photo-Searcher/searcher_app/utils/hashFunction.py)
- функция `generateHash`

Файл: [searcher_app/utils/faceDetector.py](/Users/xmodern/Documents/Photo-Searcher/searcher_app/utils/faceDetector.py)
- класс `FaceDetector`
- пока оставлен как каркас

## Что проверено

- база создается с нужными полями;
- запись пользователя работает;
- запись фото работает;
- `countOfPictures` обновляется;
- `RequestQueue` работает;
- `Admin` наследуется от `User`;
- все новые файлы проходят `py_compile`.
