from datetime import datetime

from peewee import (
    BooleanField,
    CharField,
    DateTimeField,
    FloatField,
    ForeignKeyField,
    IntegerField,
    Model,
    SqliteDatabase,
    TextField,
)

from config import DATABASE_PATH

db = SqliteDatabase(DATABASE_PATH)


class BaseModel(Model):
    class Meta:
        database = db


class Product(BaseModel):
    name = CharField()
    price = FloatField()
    category = CharField(default="uncategorized")
    timestamp = DateTimeField(default=datetime.now)
    # Новые поля для интеграции с PIT
    store = CharField(default="unknown")  # магазин (например, "Auchan")
    unit_size = FloatField(null=True)  # размер упаковки (например, 1.0)
    unit_type = CharField(null=True)  # единица измерения ("л", "кг", "шт")
    price_per_unit = FloatField(null=True)  # цена за единицу измерения
    external_id = CharField(null=True)  # внешний идентификатор из PIT


class Subscription(BaseModel):
    user_id = IntegerField(unique=True)
    subscribed = BooleanField(default=True)
    notify_only_on_change = BooleanField(default=False)  # новая опция


class PriceHistory(BaseModel):
    """История изменения цен для товаров."""

    product = ForeignKeyField(Product, backref="price_history")
    price = FloatField()
    unit_size = FloatField(null=True)
    unit_type = CharField(null=True)
    price_per_unit = FloatField(null=True)
    timestamp = DateTimeField(default=datetime.now)


class Basket(BaseModel):
    """Корзина пользователя."""

    user_id = IntegerField(null=False)  # ID пользователя Telegram
    name = CharField(default="Моя корзина")
    created_at = DateTimeField(default=datetime.now)


class BasketItem(BaseModel):
    """Элемент корзины."""

    basket = ForeignKeyField(Basket, backref="items")
    product = ForeignKeyField(Product, backref="basket_items")
    quantity = FloatField(default=1.0)  # количество упаковок


def init_db():
    db.connect()
    db.create_tables(
        [Product, Subscription, PriceHistory, Basket, BasketItem], safe=True
    )
    db.close()
