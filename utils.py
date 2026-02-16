# /Project/PriceParser/utils.py

from collections import defaultdict
from datetime import datetime

from peewee import fn

from models import Product, Subscription


def save_prices(prices):
    for name, data in prices.items():
        Product.create(
            name=name,
            price=data["price"],
            category=data.get("category", "uncategorized"),
            timestamp=datetime.now(),
        )


def get_latest_prices():
    """Возвращает последние цены каждого продукта."""
    subquery = Product.select(
        Product.name, fn.MAX(Product.timestamp).alias("max_time")
    ).group_by(Product.name)

    latest_prices = {}
    for row in subquery:
        latest_record = (
            Product.select()
            .where((Product.name == row.name) & (Product.timestamp == row.max_time))
            .first()
        )
        if latest_record:
            latest_prices[latest_record.name] = latest_record.price
    return latest_prices


def get_previous_prices():
    """Возвращает предпоследние цены каждого продукта."""
    previous_prices = {}
    # Группируем записи по имени
    grouped = defaultdict(list)
    for product in Product.select().order_by(Product.name, Product.timestamp.desc()):
        grouped[product.name].append(product)

    for name, records in grouped.items():
        if len(records) >= 2:
            previous_prices[name] = records[1].price  # 2-я по времени
    return previous_prices


def get_subscribers():
    return [
        sub.user_id
        for sub in Subscription.select().where(Subscription.subscribed == True)
    ]
