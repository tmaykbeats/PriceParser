"""
Модуль для сохранения результатов парсинга PIT в базу данных PriceParser.
Использует модели Peewee из models.py.
"""
import logging
from datetime import datetime
from models import Product, PriceHistory

logger = logging.getLogger(__name__)


def generate_external_id(store, product_name, unit_size, unit_type):
    """Генерация внешнего идентификатора для сопоставления товаров."""
    import hashlib
    key = f"{store}_{product_name}_{unit_size}_{unit_type}".encode('utf-8')
    return hashlib.md5(key).hexdigest()


def get_or_create_product(item):
    """
    Находит существующий товар или создаёт новый.
    Критерии поиска: store + name + unit_size + unit_type.
    Возвращает кортеж (product, created).
    """
    store = item['store']
    name = item['product_name']
    unit_size = item['unit_size']
    unit_type = item['unit_type']
    
    # Поиск по комбинации полей
    query = Product.select().where(
        (Product.store == store) &
        (Product.name == name) &
        (Product.unit_size == unit_size) &
        (Product.unit_type == unit_type)
    )
    
    product = query.first()
    created = False
    
    if product:
        logger.debug(f"Найден существующий товар: {product.id} {store} {name}")
        return product, created
    else:
        # Создаём новый товар
        product = Product(
            name=name,
            price=item['price'],
            category='pit',  # специальная категория для товаров из PIT
            store=store,
            unit_size=unit_size,
            unit_type=unit_type,
            price_per_unit=item['price_per_unit'],
            external_id=item.get('external_id') or generate_external_id(store, name, unit_size, unit_type)
        )
        product.save()
        created = True
        logger.info(f"Создан новый товар: {product.id} {store} {name}")
        return product, created


def add_price_history(product, item):
    """
    Добавляет запись в историю цен для товара, если цена изменилась.
    Возвращает True, если запись добавлена, иначе False.
    """
    # Получаем последнюю запись истории для этого товара
    last_history = PriceHistory.select().where(
        PriceHistory.product == product
    ).order_by(PriceHistory.timestamp.desc()).first()
    
    # Если последней записи нет или цена отличается, добавляем новую
    if not last_history or last_history.price != item['price']:
        PriceHistory.create(
            product=product,
            price=item['price'],
            unit_size=item['unit_size'],
            unit_type=item['unit_type'],
            price_per_unit=item['price_per_unit'],
            timestamp=datetime.now()
        )
        logger.debug(f"Добавлена запись истории цен для товара {product.id}")
        return True
    else:
        logger.debug(f"Цена не изменилась для товара {product.id}, история не добавляется")
        return False


def save_pit_results(results):
    """
    Сохраняет результаты парсинга PIT в базу данных PP.
    Аргумент:
        results (list): список словарей, возвращаемый pit_parser.run_pit_parsing()
    Возвращает:
        dict: статистика по сохраненным данным
    """
    stats = {
        'total_processed': len(results),
        'products_created': 0,
        'products_updated': 0,
        'history_added': 0,
        'errors': 0
    }
    
    for item in results:
        try:
            # Получаем или создаём товар
            product, created = get_or_create_product(item)
            if created:
                stats['products_created'] += 1
            else:
                stats['products_updated'] += 1
            
            # Если товар существовал, проверяем, изменилась ли цена
            if not created:
                old_price = product.price
                old_price_per_unit = product.price_per_unit
                
                # Обновляем цену и цену за единицу
                if old_price != item['price'] or old_price_per_unit != item['price_per_unit']:
                    product.price = item['price']
                    product.price_per_unit = item['price_per_unit']
                    product.save()
                    logger.info(f"Обновлена цена товара {product.id}: {old_price} -> {item['price']}")
            
            # Добавляем запись в историю
            history_added = add_price_history(product, item)
            if history_added:
                stats['history_added'] += 1
                
        except Exception as e:
            logger.error(f"Ошибка сохранения товара {item.get('product_name')}: {e}")
            stats['errors'] += 1
    
    logger.info(f"Сохранение завершено: обработано {stats['total_processed']} записей, "
                f"создано {stats['products_created']} товаров, "
                f"добавлено {stats['history_added']} записей истории.")
    return stats


def get_pit_products(store=None, product_name=None):
    """
    Возвращает список товаров, полученных через PIT.
    Параметры:
        store (str): фильтр по магазину
        product_name (str): фильтр по названию товара
    """
    query = Product.select().where(Product.category == 'pit')
    if store:
        query = query.where(Product.store == store)
    if product_name:
        query = query.where(Product.name.contains(product_name))
    
    return list(query.order_by(Product.store, Product.name))


if __name__ == '__main__':
    # Тестирование модуля
    import logging
    logging.basicConfig(level=logging.DEBUG)
    
    # Пример тестовых данных
    test_results = [
        {
            'store': 'Auchan',
            'product_name': 'Milk',
            'price': 89.99,
            'unit_size': 1.0,
            'unit_type': 'л',
            'price_per_unit': 89.99,
            'external_id': None
        },
        {
            'store': 'Auchan',
            'product_name': 'Bread',
            'price': 45.50,
            'unit_size': 0.5,
            'unit_type': 'кг',
            'price_per_unit': 91.0,
            'external_id': None
        }
    ]
    
    stats = save_pit_results(test_results)
    print(f"Статистика: {stats}")
    
    products = get_pit_products()
    print(f"Найдено товаров: {len(products)}")
    for p in products:
        print(f"  {p.store} - {p.name}: {p.price} руб., {p.unit_size}{p.unit_type}")