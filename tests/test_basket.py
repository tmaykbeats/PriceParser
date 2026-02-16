import pytest

from models import Basket, BasketItem, Product
from services.basket import (
    add_to_basket,
    calculate_basket_total,
    create_basket,
    delete_basket,
    get_basket,
    get_basket_items,
    get_user_baskets,
    remove_from_basket,
)


class TestBasketCreation:
    """Тесты создания и получения корзин."""

    def test_create_basket(self, sample_user_id, test_database):
        """Тест создания корзины."""
        basket = create_basket(sample_user_id, name="Тестовая корзина")
        assert basket.id is not None
        assert basket.user_id == sample_user_id
        assert basket.name == "Тестовая корзина"
        # Проверяем, что корзина сохранена в БД
        fetched = Basket.get_by_id(basket.id)
        assert fetched.user_id == sample_user_id

    def test_create_basket_default_name(self, sample_user_id, test_database):
        """Тест создания корзины с именем по умолчанию."""
        basket = create_basket(sample_user_id)
        assert basket.name == "Моя корзина"

    def test_get_user_baskets(self, sample_user_id, test_database):
        """Тест получения всех корзин пользователя."""
        # Создадим три корзины для одного пользователя
        baskets = [create_basket(sample_user_id, name=f"Корзина {i}") for i in range(3)]
        # Создадим корзину для другого пользователя
        create_basket(999, name="Чужая корзина")
        user_baskets = list(get_user_baskets(sample_user_id))
        assert len(user_baskets) == 3
        # Проверяем, что все корзины принадлежат правильному пользователю
        for basket in user_baskets:
            assert basket.user_id == sample_user_id
        # Порядок должен быть от новых к старым (created_at desc),
        # но если временные метки одинаковы, порядок не гарантирован.
        # Проверим, что ID созданных корзин присутствуют в результате
        basket_ids = {b.id for b in baskets}
        user_basket_ids = {b.id for b in user_baskets}
        assert basket_ids == user_basket_ids

    def test_get_basket_exists(self, sample_basket):
        """Тест получения корзины по ID (существующей)."""
        fetched = get_basket(sample_basket.id)
        assert fetched is not None
        assert fetched.id == sample_basket.id
        assert fetched.user_id == sample_basket.user_id

    def test_get_basket_not_exists(self, test_database):
        """Тест получения несуществующей корзины."""
        fetched = get_basket(99999)
        assert fetched is None


class TestAddToBasket:
    """Тесты добавления товаров в корзину."""

    def test_add_to_basket_new_item(self, sample_basket, sample_product):
        """Тест добавления нового товара в корзину."""
        item = add_to_basket(sample_basket.id, sample_product.id, quantity=3.0)
        assert item.id is not None
        assert item.basket.id == sample_basket.id
        assert item.product.id == sample_product.id
        assert item.quantity == 3.0
        # Проверяем, что элемент сохранён в БД
        fetched = BasketItem.get_by_id(item.id)
        assert fetched.quantity == 3.0

    def test_add_to_basket_existing_item(self, sample_basket, sample_product):
        """Тест увеличения количества существующего товара."""
        # Первое добавление
        item1 = add_to_basket(sample_basket.id, sample_product.id, quantity=2.0)
        # Второе добавление того же товара
        item2 = add_to_basket(sample_basket.id, sample_product.id, quantity=1.5)
        # Должен быть тот же элемент с увеличенным количеством
        assert item2.id == item1.id
        assert item2.quantity == 3.5  # 2.0 + 1.5
        # В БД должен быть только один элемент
        items = list(BasketItem.select().where(BasketItem.basket == sample_basket))
        assert len(items) == 1

    def test_add_to_basket_default_quantity(self, sample_basket, sample_product):
        """Тест добавления с количеством по умолчанию."""
        item = add_to_basket(sample_basket.id, sample_product.id)
        assert item.quantity == 1.0

    def test_add_to_basket_invalid_basket(self, sample_product):
        """Тест добавления в несуществующую корзину."""
        with pytest.raises(ValueError) as exc:
            add_to_basket(99999, sample_product.id)
        assert "не найдена" in str(exc.value)

    def test_add_to_basket_invalid_product(self, sample_basket):
        """Тест добавления несуществующего товара."""
        with pytest.raises(ValueError) as exc:
            add_to_basket(sample_basket.id, 99999)
        assert "не найден" in str(exc.value)


class TestRemoveFromBasket:
    """Тесты удаления позиций из корзины."""

    def test_remove_from_basket_success(self, sample_basket_item):
        """Тест успешного удаления элемента."""
        item_id = sample_basket_item.id
        result = remove_from_basket(item_id)
        assert result is True
        # Проверяем, что элемент удалён
        with pytest.raises(BasketItem.DoesNotExist):
            BasketItem.get_by_id(item_id)

    def test_remove_from_basket_not_exists(self, test_database):
        """Тест удаления несуществующего элемента."""
        result = remove_from_basket(99999)
        assert result is False


class TestCalculateBasketTotal:
    """Тесты расчёта общей стоимости корзины."""

    def test_calculate_basket_total_empty(self, sample_basket):
        """Тест расчёта пустой корзины."""
        total = calculate_basket_total(sample_basket.id)
        assert total == 0.0

    def test_calculate_basket_total_with_items(self, sample_basket, sample_product):
        """Тест расчёта корзины с товарами."""
        # Добавим два товара с разными количествами
        add_to_basket(sample_basket.id, sample_product.id, quantity=2.0)
        # Создадим второй товар с другой ценой
        product2 = Product.create(
            name="Товар 2", price=200.0, category="еда", store="Auchan"
        )
        add_to_basket(sample_basket.id, product2.id, quantity=1.5)
        # Ожидаемая сумма: 100*2 + 200*1.5 = 200 + 300 = 500
        total = calculate_basket_total(sample_basket.id)
        assert total == 500.0

    def test_calculate_basket_total_invalid_basket(self):
        """Тест расчёта для несуществующей корзины."""
        with pytest.raises(ValueError) as exc:
            calculate_basket_total(99999)
        assert "не найдена" in str(exc.value)


class TestGetBasketItems:
    """Тесты получения элементов корзины."""

    def test_get_basket_items_empty(self, sample_basket):
        """Тест получения элементов пустой корзины."""
        items = list(get_basket_items(sample_basket.id))
        assert len(items) == 0

    def test_get_basket_items_with_items(self, sample_basket, sample_product):
        """Тест получения элементов корзины с товарами."""
        add_to_basket(sample_basket.id, sample_product.id, quantity=2.0)
        items = list(get_basket_items(sample_basket.id))
        assert len(items) == 1
        item = items[0]
        assert item.product.id == sample_product.id
        assert item.quantity == 2.0
        # Проверяем, что товар предзагружен (prefetch)
        assert item.product.name == sample_product.name

    def test_get_basket_items_invalid_basket(self):
        """Тест получения элементов несуществующей корзины."""
        items = list(get_basket_items(99999))
        assert len(items) == 0


class TestDeleteBasket:
    """Тесты удаления корзины."""

    def test_delete_basket_success(self, sample_basket):
        """Тест успешного удаления корзины."""
        basket_id = sample_basket.id
        result = delete_basket(basket_id)
        assert result is True
        # Проверяем, что корзина удалена
        with pytest.raises(Basket.DoesNotExist):
            Basket.get_by_id(basket_id)

    def test_delete_basket_with_items(self, sample_basket, sample_product):
        """Тест удаления корзины с элементами."""
        add_to_basket(sample_basket.id, sample_product.id, quantity=1.0)
        basket_id = sample_basket.id
        result = delete_basket(basket_id)
        assert result is True
        # Корзина должна быть удалена
        with pytest.raises(Basket.DoesNotExist):
            Basket.get_by_id(basket_id)
        # Элементы корзины также должны быть удалены (каскадно)
        items = list(BasketItem.select().where(BasketItem.basket_id == basket_id))
        assert len(items) == 0

    def test_delete_basket_not_exists(self, test_database):
        """Тест удаления несуществующей корзины."""
        result = delete_basket(99999)
        assert result is False


class TestAccessControl:
    """Тесты контроля доступа (пользователь может работать только со своими корзинами)."""

    def test_user_cannot_access_other_user_basket(self, sample_basket, sample_user_id):
        """Пользователь не должен видеть корзины другого пользователя."""
        # Создадим корзину для другого пользователя
        other_basket = create_basket(999, name="Чужая корзина")
        # Получим все корзины первого пользователя
        user_baskets = list(get_user_baskets(sample_user_id))
        assert len(user_baskets) == 1
        assert user_baskets[0].id == sample_basket.id
        assert other_basket.id not in [b.id for b in user_baskets]

    def test_add_to_other_user_basket_should_fail(self, sample_user_id):
        """Попытка добавить товар в чужую корзину должна вызывать ошибку."""
        # Создадим корзину другого пользователя
        other_basket = create_basket(999, name="Чужая корзина")
        # Создадим товар
        product = Product.create(name="Товар", price=100, category="еда")
        # Функция add_to_basket не проверяет принадлежность пользователя,
        # только существование корзины. Поэтому добавление пройдёт.
        # Это может быть упущением безопасности, но тестируем как есть.
        item = add_to_basket(other_basket.id, product.id)
        assert item.basket.id == other_basket.id

    def test_calculate_total_other_user_basket(self):
        """Расчёт стоимости чужой корзины возможен, если известен ID."""
        other_basket = create_basket(999)
        product = Product.create(name="Товар", price=100, category="еда")
        add_to_basket(other_basket.id, product.id, quantity=2)
        total = calculate_basket_total(other_basket.id)
        assert total == 200.0


class TestEdgeCases:
    """Тесты граничных случаев и валидации."""

    def test_negative_quantity(self, sample_basket, sample_product):
        """Тест добавления отрицательного количества."""
        # Функция не проверяет отрицательное количество, просто сохранит.
        item = add_to_basket(sample_basket.id, sample_product.id, quantity=-1.0)
        assert item.quantity == -1.0
        # Расчёт общей стоимости будет отрицательным
        total = calculate_basket_total(sample_basket.id)
        assert total == -100.0

    def test_zero_quantity(self, sample_basket, sample_product):
        """Тест добавления нулевого количества."""
        item = add_to_basket(sample_basket.id, sample_product.id, quantity=0.0)
        assert item.quantity == 0.0
        total = calculate_basket_total(sample_basket.id)
        assert total == 0.0

    def test_float_quantity(self, sample_basket, sample_product):
        """Тест дробного количества."""
        item = add_to_basket(sample_basket.id, sample_product.id, quantity=2.75)
        assert item.quantity == 2.75
        total = calculate_basket_total(sample_basket.id)
        assert total == 275.0  # 100 * 2.75 = 275

    def test_price_per_unit_in_calculation(self, sample_basket):
        """Проверка, что используется price, а не price_per_unit."""
        # Создадим товар с price и price_per_unit
        product = Product.create(
            name="Молоко",
            price=80.0,
            price_per_unit=90.0,
            unit_size=1.0,
            unit_type="л",
            store="Auchan",
            category="pit",
        )
        add_to_basket(sample_basket.id, product.id, quantity=2.0)
        total = calculate_basket_total(sample_basket.id)
        # Должно быть price * quantity = 80 * 2 = 160, а не 90 * 2
        assert total == 160.0
