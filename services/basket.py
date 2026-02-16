"""
Модуль для работы с корзиной покупок.
"""

from peewee import DoesNotExist

from models import Basket, BasketItem, Product


def create_basket(user_id, name="Моя корзина"):
    """Создать новую корзину для пользователя."""
    basket = Basket.create(user_id=user_id, name=name)
    return basket


def get_user_baskets(user_id):
    """Получить все корзины пользователя."""
    return (
        Basket.select()
        .where(Basket.user_id == user_id)
        .order_by(Basket.created_at.desc())
    )


def get_basket(basket_id):
    """Получить корзину по ID."""
    try:
        return Basket.get_by_id(basket_id)
    except DoesNotExist:
        return None


def add_to_basket(basket_id, product_id, quantity=1.0):
    """Добавить товар в корзину."""
    basket = get_basket(basket_id)
    if not basket:
        raise ValueError(f"Корзина с ID {basket_id} не найдена")
    try:
        product = Product.get_by_id(product_id)
    except DoesNotExist:
        raise ValueError(f"Товар с ID {product_id} не найден")

    # Проверяем, есть ли уже такой товар в корзине
    existing_item = (
        BasketItem.select()
        .where((BasketItem.basket == basket) & (BasketItem.product == product))
        .first()
    )
    if existing_item:
        # Увеличиваем количество
        existing_item.quantity += quantity
        existing_item.save()
        return existing_item
    else:
        # Создаем новый элемент
        item = BasketItem.create(basket=basket, product=product, quantity=quantity)
        return item


def remove_from_basket(item_id):
    """Удалить позицию из корзины по ID элемента."""
    try:
        item = BasketItem.get_by_id(item_id)
        item.delete_instance()
        return True
    except DoesNotExist:
        return False


def calculate_basket_total(basket_id):
    """Рассчитать общую стоимость корзины с учетом количества."""
    basket = get_basket(basket_id)
    if not basket:
        raise ValueError(f"Корзина с ID {basket_id} не найдена")

    items = BasketItem.select().where(BasketItem.basket == basket).prefetch(Product)
    total = 0.0
    for item in items:
        # Используем текущую цену товара
        total += item.product.price * item.quantity
    return total


def get_basket_items(basket_id):
    """Получить все элементы корзины с информацией о товарах."""
    basket = get_basket(basket_id)
    if not basket:
        return []
    return (
        BasketItem.select()
        .where(BasketItem.basket == basket)
        .order_by(BasketItem.id)
        .prefetch(Product)
    )


def delete_basket(basket_id):
    """Удалить корзину и все её элементы."""
    try:
        basket = Basket.get_by_id(basket_id)
        # Удаляем все элементы корзины перед удалением самой корзины
        BasketItem.delete().where(BasketItem.basket == basket).execute()
        basket.delete_instance()
        return True
    except DoesNotExist:
        return False
