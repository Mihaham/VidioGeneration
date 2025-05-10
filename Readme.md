# 🎥 Видеогенератор на базе Stable Diffusion и нейросетевых моделей Sber

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)

**Проект позволяет генерировать анимированный контент с полным локальным выполнением задач, используя современные нейросетевые технологии.**

## 🌟 Основные возможности
- 🖼️ Генерация видео
- 🔒 Полностью локальное выполнение (без облачных зависимостей)
- ⚙️ Использование кастомных моделей Stable Diffusion
- 🤖 Интеграция с нейросетевыми моделями Sber для улучшения качества
- 🎚️ Тонкая настройка параметров рендеринга

## ⚡ Быстрый старт

### Предварительные требования
- NVIDIA GPU (не менее 8GB VRAM)
- Python 3.9+
- CUDA 11.7+
- Docker

### Установка
```bash
# Клонировать репозиторий
git clone git@github.com:Mihaham/VidioGeneration.git
cd VidioGeneration

# Создать структуру каталогов и шаблоны конфигов
python scripts/init_project.py
```

Заполните файлы
```
telegram-bot\database\.env'
telegram-bot\.env
```
по сгенерированным шаблонам, а так же вставьте свои файлы
```
telegram-bot\client_secrets.json
telegram-bot\russian_trusted_root_ca.cer
```

```bash

#Запуск docker-compose
docker-compose up -d --build
```

# 🗂 Структура проекта

```
├───stable-diffusion/                  # Ядро генерации контента
│   └───models/                        # Хранилище моделей и пресетов
│       ├───Codeformer/                # Модель для восстановления/апскейла лиц
│       ├───deepbooru/                 # Теггер изображений (аниме-контент)
│       ├───GFPGAN/                    # Улучшение качества лиц
│       ├───hypernetworks/             # Гиперсети для тонкой настройки генерации
│       ├───karlo/                     # Модель Karlo для текстурирования
│       ├───Lora/                      # LoRA-адаптеры для стилевой адаптации
│       ├───RealESRGAN/                # Апскейлер общего назначения
│       ├───Stable-diffusion/          # Основные веса Stable Diffusion (CKPT/Safetensors)
│       ├───VAE/                       # Вариационные автоэнкодеры
│       └───VAE-approx/                # Быстрые аппроксимации VAE

└───telegram-bot/                      # Телеграм-бот и сопутствующие сервисы
    ├───bot/                           # Основная логика бота
    │   ├───handlers/                  # Обработчики команд и сообщений
    │   └───services/                  # Сервисные модули (генерация, API-клиенты)
    │
    ├───database/                      # Работа с данными
    │   └───postgres_data/             # Данные PostgreSQL (Docker volume)
    │
    ├───fonts/                         # Шрифты для субтитров/водяных знаков
    ├───logs/                          # Логи выполнения (автозаполняются)
    │
    ├───output/                        # Все результаты работы системы
    │   ├───covers/                    # Обложки для видео (превью)
    │   ├───generated/                 # Финальные видеофайлы (MP4)
    │   ├───progress/                  # Промежуточные кадры генерации
    │   ├───sequential/                # Последовательности кадров (PNG)
    │   ├───sound/                     # Сгенерированные/обработанные аудиодорожки
    │   └───video/                     # Видео после постобработки
    │
    └───videogeneration/               # Пайплайны рендеринга (композиция/эффекты)
```

# 🔧 Интеграция с моделями Sber

Проект использует нейросетевые модели от Sber для:

1. Генерации запросов к Stable Diffusion

2. Генерации названия видео

3. Озвучивание видео

Важно: Модели Sber используются исключительно внутри системы и не предоставляются как отдельный API.

# 🤝 Как помочь проекту

1. Форкните репозиторий

2. Создайте ветку (git checkout -b feature/amazing-feature)

3. Сделайте коммит (git commit -m 'Add some amazing feature')

4. Запушьте изменения (git push origin feature/amazing-feature)

5. Откройте Pull Request

# 📜 Лицензия

Распространяется под лицензией MIT. Подробности см. в файле LICENSE.

# ✉️ Контакты

Автор: Городецкий Михаил

Email: misha19102005@yandex.ru

Telegram: [@MihahamYT](MihahamYT)