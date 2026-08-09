# 🚀 Quick Start - Unlimited OCR Web App

## Для Windows с Docker Desktop

### Шаг 1: Подготовка

1. Установите [Docker Desktop для Windows](https://www.docker.com/products/docker-desktop/)
2. Включите поддержку WSL 2 (рекомендуется)
3. Убедитесь, что есть NVIDIA GPU с последними драйверами

### Шаг 2: Запуск приложения

```powershell
# Откройте PowerShell или CMD в директории проекта
cd C:\path\to\workspace

# Запустите контейнер
docker-compose up --build -d

# Следите за логами (опционально)
docker-compose logs -f
```

### Шаг 3: Доступ к приложению

Откройте браузер и перейдите на:
```
http://localhost:8080
```

### Шаг 4: Использование

1. **Загрузите файлы**: Перетащите PDF/изображения в область загрузки
2. **Выберите формат**: TXT, CSV, JSON или HTML
3. **Запустите распознавание**: Нажмите кнопку "🚀 Запустить распознавание"
4. **Следите за прогрессом**: Прогресс-бар покажет статус обработки
5. **Получите результат**: Скачайте распознанный текст

---

## 📁 Структура файлов

```
/workspace/
├── Dockerfile              # Образ Docker (PHP + Python + Nginx)
├── docker-compose.yml      # Конфигурация запуска
├── IMPROVEMENT_IDEAS.md    # Идеи для развития
├── QUICKSTART.md           # Этот файл
└── webapp/
    ├── README.md           # Документация приложения
    ├── python/
    │   └── app.py          # Flask API backend
    ├── templates/
    │   └── index.php       # Веб-интерфейс
    ├── uploads/            # Загруженные файлы
    └── outputs/            # Результаты OCR
```

---

## ⚙️ Команды управления

```powershell
# Просмотр логов
docker-compose logs -f

# Остановка приложения
docker-compose down

# Перезапуск
docker-compose restart

# Полная очистка (включая данные)
docker-compose down -v

# Обновление кода и пересборка
docker-compose up --build -d
```

---

## 🔌 API Endpoints

| Метод | Endpoint | Описание |
|-------|----------|----------|
| POST | `/api/upload` | Загрузка файлов |
| GET | `/api/progress/<job_id>` | Статус обработки |
| GET | `/api/result/<job_id>` | Получение результатов |
| GET | `/api/formats` | Доступные форматы |

Пример curl:
```powershell
curl -X POST http://localhost:8080/api/upload ^
  -F "files=@document.pdf" ^
  -F "format=txt"
```

---

## ⚠️ Важные замечания

### Требования к ресурсам
- **RAM**: Минимум 16GB (рекомендуется 32GB)
- **GPU**: NVIDIA с поддержкой CUDA (обязательно для быстрой работы)
- **Диск**: 50GB свободного места
- **Модель**: ~20GB (загружается при первом запуске)

### Первый запуск
При первом запуске модель Unlimited-OCR будет загружена из HuggingFace. Это может занять 10-30 минут в зависимости от скорости интернета.

### Поддерживаемые форматы
- **Входные**: PDF, PNG, JPG, JPEG, WEBP, BMP
- **Выходные**: TXT, CSV, JSON, HTML

### Максимальный размер файла
500MB на файл (можно изменить в Dockerfile)

---

## 🐛 Решение проблем

### Контейнер не запускается
```powershell
# Проверьте статус Docker Desktop
# Убедитесь, что WSL 2 включен
wsl --list --verbose

# Проверьте логи
docker-compose logs
```

### Ошибка с GPU
```powershell
# Проверьте доступность GPU
docker run --rm --gpus all nvidia/cuda:11.0-base nvidia-smi

# В Docker Desktop: Settings → Resources → WSL Integration
```

### Медленная обработка
- Убедитесь, что используется GPU, а не CPU
- Уменьшите DPI для PDF в настройках
- Обрабатывайте файлы по очереди вместо пакетной обработки

### Нет результата после обработки
```powershell
# Проверьте логи Python приложения
docker-compose logs | grep python

# Проверьте права доступа к папкам
docker-compose exec unlimited-ocr-app ls -la /app/outputs
```

---

## 📞 Поддержка

- 📄 [Документация приложения](webapp/README.md)
- 💡 [Идеи для улучшения](IMPROVEMENT_IDEAS.md)
- 📚 [Оригинальный Unlimited-OCR](https://github.com/baidu/Unlimited-OCR)

---

## 🎯 Что дальше?

После успешного запуска вы можете:

1. **Настроить под свои нужды**: Измените `Dockerfile` и `docker-compose.yml`
2. **Добавить функции**: Смотрите [IMPROVEMENT_IDEAS.md](IMPROVEMENT_IDEAS.md)
3. **Интегрировать с другими системами**: Используйте REST API
4. **Масштабировать**: Настройте Kubernetes для production

**Удачи в использовании! 🎉**
