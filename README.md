# 🚀 Unlimited-OCR-UI

**Веб-интерфейс для Unlimited OCR с поддержкой LLM (llama.cpp, Ollama, SGLang)**

<div align="center">

[![Original Project](https://img.shields.io/badge/Original-Unlimited--OCR-blue?logo=github)](https://github.com/baidu/Unlimited-OCR)
[![Documentation](https://img.shields.io/badge/Docs-README--UNLIMITED--OCR-green)](README-UNLIMITED-OCR.MD)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue?logo=docker)](https://www.docker.com/)
[![API](https://img.shields.io/badge/API-RESTful-orange)](webapp/API_DOCUMENTATION.md)

</div>

---

## 📌 О проекте

Этот репозиторий (**Unlimited-OCR-UI**) предоставляет современный веб-интерфейс и API для работы с моделью **Unlimited OCR** от Baidu.

🔗 **Оригинальный проект**: [baidu/Unlimited-OCR](https://github.com/baidu/Unlimited-OCR)  
📄 **Документация оригинальной модели**: [README-UNLIMITED-OCR.MD](README-UNLIMITED-OCR.MD)

### ✨ Возможности

- 🌐 **Веб-интерфейс**: Drag-and-drop загрузка, прогресс-бар, мультиформатный вывод
- 🔌 **REST API**: Полноценное API v1 для интеграции с внешними системами
- 🤖 **LLM поддержка**: SGLang, llama.cpp, Ollama с настраиваемыми провайдерами
- 📊 **Форматы вывода**: TXT, CSV, JSON, HTML
- 🔄 **Real-time обновления**: SSE streaming для отслеживания прогресса
- 🐳 **Docker Ready**: Запуск в один клик на Windows/Mac/Linux

---

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
├── Dockerfile                  # Образ Docker (PHP + Python + Nginx)
├── docker-compose.yml          # Конфигурация запуска
├── README.md                   # Этот файл (Quick Start)
├── README-UNLIMITED-OCR.MD     # Документация оригинального проекта
├── IMPROVEMENT_IDEAS.md        # Идеи для развития
└── webapp/
    ├── README.md               # Документация приложения
    ├── API_DOCUMENTATION.md    # Полная документация API v1
    ├── LLM_CONFIGURATION.md    # Настройка LLM провайдеров
    ├── python/
    │   └── app.py              # Flask API backend
    ├── templates/
    │   └── index.php           # Веб-интерфейс
    ├── config/
    │   └── llm_config.json     # Конфигурация LLM провайдеров
    ├── uploads/                # Загруженные файлы
    └── outputs/                # Результаты OCR
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

### Основные endpoints

| Метод | Endpoint | Описание |
|-------|----------|----------|
| POST | `/api/v1/ocr/submit` | Отправка документов на распознавание |
| GET | `/api/v1/ocr/status/<job_id>` | Статус и прогресс обработки |
| GET | `/api/v1/ocr/result/<job_id>` | Получение результатов |
| GET | `/api/v1/ocr/stream/<job_id>` | SSE streaming для real-time обновлений |
| POST | `/api/v1/ocr/cancel/<job_id>` | Отмена задания |
| GET | `/api/v1/ocr/list` | Список всех заданий |

### LLM Management

| Метод | Endpoint | Описание |
|-------|----------|----------|
| GET | `/api/v1/llm/providers` | Список доступных LLM провайдеров |
| GET | `/api/v1/llm/config` | Текущая конфигурация LLM |
| POST | `/api/v1/llm/config` | Обновление конфигурации LLM |
| GET | `/api/v1/llm/test/<provider>` | Тест подключения к провайдеру |

📖 **Полная документация API**: [webapp/API_DOCUMENTATION.md](webapp/API_DOCUMENTATION.md)

Пример curl:
```powershell
# Отправка документа на распознавание
curl -X POST http://localhost:5000/api/v1/ocr/submit ^
  -F "files=@document.pdf" ^
  -F "output_format=json"

# Получение статуса
curl http://localhost:5000/api/v1/ocr/status/<job_id>

# Выбор LLM провайдера (Ollama)
curl -X POST http://localhost:5000/api/v1/llm/config ^
  -H "Content-Type: application/json" ^
  -d "{\"active_provider\": \"ollama\"}"
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

## 📞 Поддержка и документация

### Основная документация
- 📄 [Документация приложения](webapp/README.md)
- 📖 [API Documentation v1](webapp/API_DOCUMENTATION.md)
- 🤖 [LLM Configuration Guide](webapp/LLM_CONFIGURATION.md)
- 💡 [Идеи для улучшения](IMPROVEMENT_IDEAS.md)

### Оригинальный проект
- 📚 [Оригинальный Unlimited-OCR](https://github.com/baidu/Unlimited-OCR)
- 📄 [Документация модели](README-UNLIMITED-OCR.MD)
- 🤗 [Hugging Face Model](https://huggingface.co/baidu/Unlimited-OCR)
- 📑 [arXiv Paper](https://arxiv.org/abs/2606.23050)

### LLM Провайдеры
- 🔷 [SGLang Documentation](https://docs.sglang.ai/)
- 🦙 [llama.cpp GitHub](https://github.com/ggerganov/llama.cpp)
- 🦙 [Ollama Documentation](https://ollama.ai/docs)

---

## 🎯 Что дальше?

После успешного запуска вы можете:

1. **Настроить под свои нужды**: Измените `Dockerfile` и `docker-compose.yml`
2. **Добавить функции**: Смотрите [IMPROVEMENT_IDEAS.md](IMPROVEMENT_IDEAS.md)
3. **Интегрировать с другими системами**: Используйте REST API
4. **Масштабировать**: Настройте Kubernetes для production

**Удачи в использовании! 🎉**
