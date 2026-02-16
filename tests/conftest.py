import pytest
from peewee import SqliteDatabase
import sys
import os

# Добавляем корневую директорию проекта в путь Python
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import db, Product, Subscription, PriceHistory, Basket, BasketItem, init_db
import config

# Переопределяем DATABASE_PATH на временную базу в памяти для тестов
config.DATABASE_PATH = ':memory:'


@pytest.fixture(scope='session')
def test_database():
    """Создаёт временную базу данных в памяти для всех тестов."""
    # Используем ту же глобальную базу данных из models.py
    db = SqliteDatabase(':memory:')
    # Заменяем базу данных у моделей
    for model in [Product, Subscription, PriceHistory, Basket, BasketItem]:
        model._meta.database = db
    db.connect()
    db.create_tables([Product, Subscription, PriceHistory, Basket, BasketItem])
    yield db
    db.drop_tables([Product, Subscription, PriceHistory, Basket, BasketItem])
    db.close()


@pytest.fixture(autouse=True)
def clean_database(test_database):
    """Очищает все таблицы перед каждым тестом."""
    # Удаляем все записи из всех таблиц
    with test_database.atomic():
        BasketItem.delete().execute()
        Basket.delete().execute()
        PriceHistory.delete().execute()
        Subscription.delete().execute()
        Product.delete().execute()
    yield


@pytest.fixture
def sample_product(test_database):
    """Создаёт тестовый товар."""
    product = Product.create(
        name='Тестовый товар',
        price=100.0,
        category='еда',
        store='Auchan',
        unit_size=1.0,
        unit_type='л',
        price_per_unit=100.0,
        external_id='test_123'
    )
    return product


@pytest.fixture
def sample_user_id():
    """Возвращает тестовый ID пользователя."""
    return 123456


@pytest.fixture
def sample_basket(sample_user_id, test_database):
    """Создаёт тестовую корзину для пользователя."""
    basket = Basket.create(user_id=sample_user_id, name='Тестовая корзина')
    return basket


@pytest.fixture
def sample_basket_item(sample_basket, sample_product, test_database):
    """Создаёт тестовый элемент корзины."""
    item = BasketItem.create(basket=sample_basket, product=sample_product, quantity=2.0)
    return item


@pytest.fixture
def mock_selenium(mocker):
    """Мокает Selenium WebDriver."""
    mock_driver = mocker.Mock()
    mock_driver.find_element.return_value = mocker.Mock()
    mock_driver.page_source = '<html>Mock page</html>'
    mock_driver.quit = mocker.Mock()
    mocker.patch('services.pit_parser.webdriver.Chrome', return_value=mock_driver)
    return mock_driver