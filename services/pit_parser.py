"""
Адаптер для парсинга магазинов через PIT (product-inflation-tracker).
Интегрирует синхронный код PIT в асинхронное окружение PriceParser.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Добавляем путь к модулям PIT
sys.path.insert(0, str(Path(__file__).parent / "pit_integration"))

logger = logging.getLogger(__name__)

# Константы
CONFIG_PATH = Path(__file__).parent / "pit_integration" / "store_config.txt"


async def parse_config_async():
    """
    Асинхронно загружает конфигурацию магазинов из файла.
    Возвращает список конфигураций в формате словаря.
    """

    # Синхронную операцию чтения файла выполняем в отдельном потоке
    def load_config():
        from store_productscraper import parse_config

        return parse_config(str(CONFIG_PATH))

    loop = asyncio.get_event_loop()
    configs = await loop.run_in_executor(None, load_config)
    logger.info(f"Загружено {len(configs)} конфигураций магазинов")
    return configs


async def fetch_page_async(url, use_selenium=True):
    """
    Асинхронно загружает страницу, используя Selenium или requests.
    Параметры:
        url (str): URL для загрузки
        use_selenium (bool): если True, использует Selenium; иначе requests.
    Возвращает HTML (str) или None при ошибке.
    """
    from store_productscraper import fetch_page_requests, fetch_page_selenium

    def fetch():
        if use_selenium:
            return fetch_page_selenium(url)
        else:
            # fetch_page_requests возвращает BeautifulSoup, преобразуем в HTML
            soup = fetch_page_requests(url)
            return str(soup) if soup else None

    loop = asyncio.get_event_loop()
    try:
        html = await loop.run_in_executor(None, fetch)
        return html
    except Exception as e:
        logger.error(f"Ошибка загрузки страницы {url}: {e}")
        return None


async def extract_product_data_async(config, variant="cheapest"):
    """
    Извлекает данные о продукте для заданной конфигурации и варианта.
    Возвращает словарь с полями:
        store, country, product_name, variant, full_name, full_price,
        price, unit_size, unit_type, price_per_unit, external_id
    Если данные не найдены, возвращает None.
    """
    from store_productscraper import extract_data_from_template

    url = config["URLS"].get(variant)
    if not url:
        logger.warning(
            f"URL для варианта {variant} не указан в конфигурации {config['STORE']}"
        )
        return None

    # Загружаем страницу (используем Selenium, так как большинство магазинов требуют JS)
    html = await fetch_page_async(url, use_selenium=True)
    if not html:
        return None

    # Извлекаем заголовок и цену по шаблону
    def extract():
        title = extract_data_from_template(config["TITLE"], html)
        price = extract_data_from_template(config["PRICE"], html)
        return title, price

    loop = asyncio.get_event_loop()
    try:
        title, price = await loop.run_in_executor(None, extract)
    except Exception as e:
        logger.error(f"Ошибка извлечения данных для {config['STORE']}: {e}")
        return None

    # Если нет данных, пропускаем
    if not title or not price:
        logger.warning(
            f"Не удалось извлечь title или price для {config['STORE']} - {config['PRODUCT']}"
        )
        return None

    # Извлекаем информацию об упаковке и рассчитываем цену за единицу
    # Используем функции из store_productscraper
    from store_productscraper import (
        UNIT_BASE_LABELS,
        calculate_price_per_unit,
        extract_package_info,
        extract_price_info,
    )

    # Извлекаем числовую цену и валюту
    price_number, currency = extract_price_info(price, config.get("CURRENCY_MAP", {}))
    # Извлекаем размер упаковки
    package_string, package_size, package_unit = extract_package_info(title)
    # Вычисляем цену за единицу
    price_per_unit_string, price_per_unit_number = calculate_price_per_unit(
        price_number, package_size, package_unit, currency
    )

    # Формируем результат
    result = {
        "store": config["STORE"],
        "country": config["COUNTRY"],
        "product_name": config["PRODUCT"],
        "variant": variant,
        "full_name": title,
        "full_price": price,
        "price": price_number,
        "currency": currency,
        "unit_size": package_size,
        "unit_type": package_unit,
        "price_per_unit": price_per_unit_number,
        "price_per_unit_string": price_per_unit_string,
        "external_id": None,  # можно сгенерировать хэш
    }

    logger.info(
        f"Извлечены данные: {config['STORE']} - {config['PRODUCT']} цена {price_number} {currency}"
    )
    return result


async def run_pit_parsing(store_filter=None, product_filter=None):
    """
    Основная функция парсинга: загружает конфигурации, обрабатывает каждый магазин,
    возвращает список результатов.
    Параметры:
        store_filter (list): список названий магазинов для фильтрации (опционально)
        product_filter (list): список названий продуктов для фильтрации (опционально)
    """
    configs = await parse_config_async()
    results = []

    for config in configs:
        store = config["STORE"]
        product = config["PRODUCT"]

        if store_filter and store not in store_filter:
            continue
        if product_filter and product not in product_filter:
            continue

        # Обрабатываем оба варианта (cheapest, most_expensive)
        for variant in ["cheapest", "most_expensive"]:
            if variant not in config["URLS"] or not config["URLS"][variant]:
                continue

            data = await extract_product_data_async(config, variant)
            if data:
                results.append(data)

    logger.info(f"Парсинг завершен, собрано {len(results)} записей")
    return results


if __name__ == "__main__":
    # Тестирование модуля
    import asyncio

    logging.basicConfig(level=logging.INFO)

    async def test():
        print("Запуск тестового парсинга PIT...")
        results = await run_pit_parsing(
            store_filter=["Auchan"], product_filter=["Milk"]
        )
        for r in results:
            print(
                f"{r['store']} - {r['product_name']}: {r['price']} {r['currency']}, "
                f"упаковка {r['unit_size']} {r['unit_type']}, "
                f"цена за единицу {r['price_per_unit']}"
            )

    asyncio.run(test())
