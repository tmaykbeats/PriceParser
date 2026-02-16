# План интеграции PIT (product-inflation-tracker) в проект PriceParser (PP)

## Обзор
Цель: интегрировать механизм парсинга продуктов с инфляционными данными из PIT в существующий проект PriceParser, расширив функциональность отслеживания цен с учетом размера упаковки и цены за единицу измерения.

## Текущее состояние проекта PP

### Структура проекта
```
PriceParser/
├── config.py                    # Конфигурация (токен бота, пути)
├── models.py                    # Модели Peewee: Product, Subscription
├── handlers.py                  # Обработчики Telegram-бота
├── main.py                      # Точка входа, планировщик (использует APScheduler)
├── web_app.py                   # FastAPI веб-приложение
├── services/
│   ├── parser.py               # Парсер сайта scrapeme.live (async, requests+BeautifulSoup)
│   ├── history.py              # Функции работы с историей цен
│   └── notifier.py             # Уведомления
├── static/                      # Статические файлы (изображения)
├── templates/                   # HTML шаблоны
└── requirements.txt             # Зависимости
```

### База данных
- Используется SQLite через Peewee ORM.
- Таблица `Product`: `id`, `name`, `price`, `category`, `timestamp`.
- Таблица `Subscription`: `user_id`, `subscribed`, `notify_only_on_change`.
- **Отсутствует** таблица истории цен (`PriceHistory`) как отдельная сущность.
- **Отсутствуют** поля для упаковки и цены за единицу.

### Парсинг в PP
- Асинхронная функция `scrape_prices()` в `services/parser.py`.
- Простой парсинг одного сайта (scrapeme.live) через requests.
- Нет поддержки Selenium, конфигурируемых магазинов, извлечения упаковки.

## Код PIT (product-inflation-tracker)

### Структура PIT
```
product-inflation-tracker/
├── store_productscraper.py      # Основной модуль (815 строк)
├── store_config.txt             # Конфигурация магазинов (текстовый формат)
├── product_inflation.db         # База данных SQLite
├── price-inflation-database-to-json-converter.py
└── README.md
```

### Ключевые возможности PIT
1. **Конфигурация магазинов** через `store_config.txt` (шаблоны HTML для извлечения названия и цены).
2. **Парсинг через Selenium и requests** в зависимости от сайта.
3. **Извлечение информации об упаковке** (размер, единица измерения) из названия товара.
4. **Расчет цены за единицу** (цена за кг/л/шт) с конвертацией единиц.
5. **Сохранение в SQLite** с таблицами: Store, ProductType, PriceSample.
6. **Расчет инфляции** между последовательными замерами.

### Ограничения PIT
- Синхронный код (блокирующие вызовы Selenium/requests).
- Предполагает автономное выполнение, не интегрирован в асинхронное окружение.
- Использует собственную схему БД, отличную от PP.

## Этапы интеграции

### Этап 0. Подготовка и анализ зависимостей

**Цель:** Установить недостающие зависимости и создать структуру директорий для интеграции.

**Задачи:**
1. Добавить в `requirements.txt` зависимости PIT:
   ```
   selenium>=4.0.0
   webdriver-manager
   beautifulsoup4
   requests
   ```
2. Проверить наличие Firefox/Chrome и драйверов (geckodriver/chromedriver) в системе.
3. Создать директорию для модулей PIT внутри PP:
   ```
   mkdir -p services/pit_integration
   ```
4. Скопировать необходимые файлы из PIT:
   - `store_productscraper.py` → `services/pit_integration/store_productscraper.py`
   - `store_config.txt` → `services/pit_integration/store_config.txt`
5. Создать модуль-адаптер для работы с кодом PIT в асинхронном окружении.

**Файлы для изменения:**
- `requirements.txt` – добавить зависимости.
- Создать `services/pit_integration/__init__.py`.

---

### Этап 1. Расширение моделей базы данных PP

**Цель:** Добавить в PP поля для хранения информации об упаковке и цене за единицу, а также таблицу истории цен.

**Задачи:**
1. Изменить модель `Product` в `models.py`:
   - Добавить поля: `unit_size` (Float), `unit_type` (String), `price_per_unit` (Float), `external_id` (String, nullable), `store` (String) для имени магазина.
   - Возможно, добавить поле `country` (String).
2. Создать модель `PriceHistory` для хранения исторических записей цен с полями:
   - `id`, `product_id` (ForeignKey), `price` (Float), `unit_size`, `unit_type`, `price_per_unit`, `timestamp`.
3. Создать скрипт миграции или обновить `init_db.py` для создания новых таблиц/полей.
4. Убедиться, что существующие данные остаются совместимыми (поле `store` можно заполнить значением по умолчанию).

**Файлы для изменения:**
- `models.py` – расширение моделей.
- `init_db.py` – обновление создания таблиц.
- Возможно, `config.py` – добавить путь к новой БД (если будет отдельная).

**Пример изменений `models.py`:**
```python
class Product(BaseModel):
    name = CharField()
    price = FloatField()
    category = CharField(default="uncategorized")
    timestamp = DateTimeField(default=datetime.now)
    # Новые поля
    store = CharField(default="unknown")  # магазин (например, "Auchan")
    unit_size = FloatField(null=True)    # размер упаковки (например, 1.0)
    unit_type = CharField(null=True)     # единица измерения ("л", "кг", "шт")
    price_per_unit = FloatField(null=True)  # цена за единицу
    external_id = CharField(null=True)   # внешний идентификатор из PIT

class PriceHistory(BaseModel):
    product = ForeignKeyField(Product, backref='price_history')
    price = FloatField()
    unit_size = FloatField(null=True)
    unit_type = CharField(null=True)
    price_per_unit = FloatField(null=True)
    timestamp = DateTimeField(default=datetime.now)
```

---

### Этап 2. Интеграция парсеров PIT в PP

**Цель:** Адаптировать код PIT для работы в рамках PP, создав асинхронную обертку и конвейер обработки.

**Задачи:**
1. Создать модуль `services/pit_parser.py` – основной адаптер, который:
   - Загружает конфигурацию из `store_config.txt`.
   - Для каждого магазина запускает парсинг (синхронный код PIT) в отдельном потоке (`asyncio.to_thread`).
   - Преобразует результаты PIT в формат, совместимый с моделями PP.
2. Рефакторинг функций PIT для использования в качестве библиотеки:
   - Выделить из `store_productscraper.py` ключевые функции: `parse_config`, `fetch_page_selenium`, `extract_price_info`, `extract_package_info`, `calculate_price_per_unit`.
   - Убрать прямые вызовы `save_to_database` (сохранение будет в PP).
3. Создать конфигурационный менеджер для магазинов:
   - Возможно, перенести конфигурацию из текстового файла в YAML/JSON для удобства.
   - Добавить возможность добавлять/удалять магазины через админку/бота.

**Файлы для создания/изменения:**
- `services/pit_parser.py` – основной адаптер.
- `services/pit_integration/core.py` – вынесенные функции PIT.
- `services/pit_integration/config_loader.py` – загрузка конфигурации.

**Пример структуры `pit_parser.py`:**
```python
import asyncio
from .pit_integration.core import parse_config, fetch_page_selenium, extract_product_data

async def run_pit_parsing():
    configs = parse_config('services/pit_integration/store_config.txt')
    results = []
    for config in configs:
        # Запуск синхронного парсинга в отдельном потоке
        html = await asyncio.to_thread(fetch_page_selenium, config['url'])
        if html:
            data = extract_product_data(html, config)
            results.append({
                'store': config['store'],
                'product_name': config['product'],
                'price': data['price'],
                'unit_size': data['unit_size'],
                'unit_type': data['unit_type'],
                'price_per_unit': data['price_per_unit'],
                'external_id': data.get('external_id')
            })
    return results
```

---

### Этап 3. Сохранение результатов в БД PP

**Цель:** Сохранять данные, полученные от PIT, в таблицы Product и PriceHistory.

**Задачи:**
1. Создать функцию `save_pit_results(results)` в `services/pit_parser.py` или отдельном модуле `services/pit_db.py`.
2. Логика сохранения:
   - Для каждого результата искать существующий товар по комбинации `store` + `name` + `unit_size` (или `external_id`).
   - Если товар не найден – создать новый `Product`.
   - Если найден – обновить `price`, `price_per_unit`.
   - В любом случае создать запись в `PriceHistory` (только если цена изменилась).
3. Учесть валюту: PIT хранит цены в разных валютах, PP работает в рублях (или единой валюте). Возможно, потребуется конвертация.

**Файлы для создания:**
- `services/pit_db.py` – функции сохранения.
- Обновление `services/pit_parser.py` для вызова save.

**Пример функции сохранения:**
```python
async def save_pit_results(results):
    for item in results:
        # Поиск существующего товара
        product = Product.get_or_none(
            (Product.store == item['store']) &
            (Product.name == item['product_name']) &
            (Product.unit_size == item['unit_size'])
        )
        if product is None:
            product = Product.create(
                name=item['product_name'],
                store=item['store'],
                price=item['price'],
                unit_size=item['unit_size'],
                unit_type=item['unit_type'],
                price_per_unit=item['price_per_unit'],
                external_id=item.get('external_id'),
                category='pit'  # специальная категория
            )
        else:
            product.price = item['price']
            product.price_per_unit = item['price_per_unit']
            product.save()
        # Создать запись истории, если цена изменилась
        last_history = PriceHistory.select().where(PriceHistory.product == product).order_by(PriceHistory.timestamp.desc()).first()
        if not last_history or last_history.price != item['price']:
            PriceHistory.create(
                product=product,
                price=item['price'],
                unit_size=item['unit_size'],
                unit_type=item['unit_type'],
                price_per_unit=item['price_per_unit']
            )
```

---

### Этап 4. Интеграция с планировщиком PP

**Цель:** Добавить периодический запуск парсера PIT в существующий планировщик PP.

**Задачи:**
1. Изучить текущий планировщик в `main.py` (использует APScheduler).
2. Добавить новую задачу (например, ежедневно в 2:00) для вызова `run_pit_parsing` и `save_pit_results`.
3. Учесть асинхронность: обернуть вызовы в `asyncio.run_coroutine_threadsafe` или использовать async‑совместимый планировщик.
4. Добавить логирование и обработку ошибок.

**Файлы для изменения:**
- `main.py` – добавление новой задачи.
- Возможно, создать отдельный модуль `scheduler_tasks.py`.

**Пример изменения `main.py`:**
```python
from services.pit_parser import run_pit_parsing, save_pit_results

async def pit_parse_job():
    results = await run_pit_parsing()
    await save_pit_results(results)

def schedule_pit_tasks(scheduler):
    scheduler.add_job(
        lambda: asyncio.run(pit_parse_job()),
        trigger='cron',
        hour=2,
        minute=0,
        id='pit_parser'
    )
```

---

### Этап 5. Расширение функциональности бота и веб-интерфейса

**Цель:** Показать пользователям данные о цене за единицу, добавить команды для работы с товарами PIT.

**Задачи:**
1. Добавить в бота команды:
   - `/pit_products` – список товаров, полученных через PIT.
   - `/price_per_unit <product_id>` – отобразить цену за единицу.
   - `/compare_units` – сравнить цены за единицу между магазинами.
2. Обновить веб-интерфейс (`templates/products.html`, `web_app.py`):
   - Добавить колонки "Размер упаковки", "Цена за единицу".
   - Возможно, добавить график изменения цены за единицу.
3. Реализовать функциональность "Корзина" (опционально, как в PLAN.md):
   - Создать модели Basket и BasketItem.
   - Добавить команды бота для управления корзиной.

**Файлы для изменения:**
- `handlers.py` – новые команды.
- `web_app.py` – новые маршруты.
- `templates/products.html` – обновление таблицы.
- `models.py` – модели Basket, BasketItem (если нужно).

---

### Этап 6. Тестирование и валидация

**Цель:** Убедиться, что интеграция работает корректно, данные парсятся и сохраняются.

**Задачи:**
1. Написать unit-тесты для ключевых функций (извлечение упаковки, расчет цены за единицу).
2. Провести интеграционное тестирование:
   - Запустить парсинг для одного магазина (например, Auchan) вручную.
   - Проверить, что данные появились в БД PP.
   - Проверить отображение в боте и веб-интерфейсе.
3. Настроить логирование для отслеживания ошибок парсинга.
4. Оптимизация производительности:
   - Параллельный парсинг нескольких магазинов.
   - Кэширование драйверов Selenium.

**Файлы для создания:**
- `tests/test_pit_parser.py`
- `tests/test_pit_db.py`
- Обновление `logging.conf` (если есть).

---

## Зависимости, которые нужно добавить в requirements.txt

```
selenium>=4.0.0
webdriver-manager
beautifulsoup4
requests
```

Если планируется использовать конвертацию валют:
```
forex-python
```

## Потенциальные проблемы и решения

1. **Синхронный код PIT в асинхронном окружении**:
   - Использовать `asyncio.to_thread` для вызовов Selenium/requests.
   - Ограничить количество одновременных потоков, чтобы не перегрузить систему.

2. **Разные валюты**:
   - PIT хранит цены в валюте магазина (USD, EUR, RUB и т.д.).
   - PP, возможно, ожидает одну валюту (рубли).
   - Решение: конвертировать цены в рубли по текущему курсу (используя API ЦБ или forex-python) либо хранить валюту отдельно.

3. **Дублирование товаров**:
   - Использовать уникальный ключ: `store + name + unit_size`.
   - Добавить поле `external_id` для связи с оригинальной записью PIT.

4. **Производительность парсинга**:
   - Selenium требует много времени на загрузку страниц.
   - Рассмотреть использование `requests` + `BeautifulSoup` где возможно.
   - Использовать headless-режим и кэширование.

5. **Обновление конфигурации магазинов**:
   - Текстовый файл `store_config.txt` неудобен для динамического обновления.
   - В будущем перенести конфигурацию в БД и добавить админ-интерфейс.

## Структура директорий после интеграции

```
PriceParser/
├── services/
│   ├── pit_integration/
│   │   ├── __init__.py
│   │   ├── store_productscraper.py      # скопированный исходник (с минимальными изменениями)
│   │   ├── config_loader.py             # загрузка конфигурации
│   │   ├── core.py                      # вынесенные функции парсинга
│   │   └── store_config.txt             # конфигурация магазинов
│   ├── pit_parser.py                    # основной адаптер
│   ├── pit_db.py                        # сохранение результатов
│   ├── parser.py                        # оригинальный парсер (оставить)
│   └── ...
├── models.py                            # расширенные модели
├── INTEGRATION_PLAN.md                  # этот файл
└── ...
```

## Следующие шаги

1. **Согласование плана** с заказчиком/командой.
2. **Реализация по этапам** с использованием соответствующих мод (Code mode).
3. **Тестирование** после каждого этапа.
4. **Документирование** изменений.

---
*План составлен на основе анализа кода от 2026-02-16.*
