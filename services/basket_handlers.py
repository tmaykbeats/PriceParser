"""
Обработчики команд Telegram-бота для работы с корзиной покупок.
"""
import logging
from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.utils.exceptions import MessageTextIsEmpty
from models import Basket, BasketItem, Product
from services.basket import (
    create_basket,
    get_user_baskets,
    get_basket,
    add_to_basket,
    remove_from_basket,
    calculate_basket_total,
    get_basket_items,
    delete_basket,
)

logger = logging.getLogger(__name__)


async def mybaskets_command(message: types.Message, state: FSMContext):
    """
    Команда /mybaskets - список корзин пользователя.
    """
    await state.finish()
    user_id = message.from_user.id
    try:
        baskets = get_user_baskets(user_id)
        if not baskets:
            await message.reply("У вас пока нет корзин. Создайте новую командой /create_basket.")
            return

        lines = ["*Ваши корзины:*"]
        for basket in baskets:
            # Подсчитаем количество товаров и общую стоимость
            item_count = BasketItem.select().where(BasketItem.basket == basket).count()
            total = calculate_basket_total(basket.id)
            lines.append(
                f"• #{basket.id} **{basket.name}** "
                f"(товаров: {item_count}, сумма: {total:.2f} ₽)\n"
                f"  Создана: {basket.created_at.strftime('%d.%m.%Y %H:%M')}"
            )

        await message.reply("\n".join(lines), parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Ошибка в команде /mybaskets: {e}")
        await message.reply("Произошла ошибка при получении списка корзин.")


async def create_basket_command(message: types.Message, state: FSMContext):
    """
    Команда /create_basket <название> - создать новую корзину.
    """
    await state.finish()
    args = message.get_args()
    name = args.strip() if args else "Моя корзина"
    user_id = message.from_user.id

    try:
        basket = create_basket(user_id, name)
        await message.reply(
            f"Корзина **{basket.name}** создана!\n"
            f"ID: `{basket.id}`\n"
            f"Используйте /add_to_basket {basket.id} <product_id> чтобы добавить товары.",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Ошибка в команде /create_basket: {e}")
        await message.reply("Не удалось создать корзину.")


async def delete_basket_command(message: types.Message, state: FSMContext):
    """
    Команда /delete_basket <id> - удалить корзину.
    """
    await state.finish()
    args = message.get_args()
    if not args:
        await message.reply("Укажите ID корзины: /delete_basket <id>")
        return

    try:
        basket_id = int(args)
        user_id = message.from_user.id
        # Проверяем, что корзина принадлежит пользователю
        basket = get_basket(basket_id)
        if not basket:
            await message.reply("Корзина с указанным ID не найдена.")
            return
        if basket.user_id != user_id:
            await message.reply("Вы не можете удалить чужую корзину.")
            return

        success = delete_basket(basket_id)
        if success:
            await message.reply(f"Корзина #{basket_id} удалена.")
        else:
            await message.reply("Не удалось удалить корзину.")

    except ValueError:
        await message.reply("ID корзины должен быть числом.")
    except Exception as e:
        logger.error(f"Ошибка в команде /delete_basket: {e}")
        await message.reply("Произошла ошибка при удалении корзины.")


async def basket_command(message: types.Message, state: FSMContext):
    """
    Команда /basket <id> - показать содержимое корзины с общей стоимостью.
    """
    await state.finish()
    args = message.get_args()
    if not args:
        await message.reply("Укажите ID корзины: /basket <id>")
        return

    try:
        basket_id = int(args)
        user_id = message.from_user.id
        basket = get_basket(basket_id)
        if not basket:
            await message.reply("Корзина с указанным ID не найдена.")
            return
        if basket.user_id != user_id:
            await message.reply("Вы не можете просматривать чужую корзину.")
            return

        items = get_basket_items(basket_id)
        if not items:
            await message.reply(f"Корзина **{basket.name}** пуста.", parse_mode="Markdown")
            return

        total = calculate_basket_total(basket_id)

        lines = [f"*{basket.name}* (ID: {basket.id})"]
        for item in items:
            product = item.product
            unit_info = ""
            if product.unit_size and product.unit_type:
                unit_info = f" ({product.unit_size}{product.unit_type})"
            subtotal = product.price * item.quantity
            lines.append(
                f"• #{item.id} {product.name}{unit_info} — "
                f"{product.price:.2f} ₽ × {item.quantity} = {subtotal:.2f} ₽"
            )

        lines.append(f"\n*Итого: {total:.2f} ₽*")
        await message.reply("\n".join(lines), parse_mode="Markdown")

    except ValueError:
        await message.reply("ID корзины должен быть числом.")
    except Exception as e:
        logger.error(f"Ошибка в команде /basket: {e}")
        await message.reply("Произошла ошибка при получении информации о корзине.")


async def add_to_basket_command(message: types.Message, state: FSMContext):
    """
    Команда /add_to_basket <basket_id> <product_id> [количество] - добавить товар в корзину.
    """
    await state.finish()
    args = message.get_args()
    if not args:
        await message.reply(
            "Использование: /add_to_basket <basket_id> <product_id> [количество]\n"
            "Количество по умолчанию: 1.0"
        )
        return

    parts = args.split()
    if len(parts) < 2:
        await message.reply("Укажите ID корзины и ID товара.")
        return

    try:
        basket_id = int(parts[0])
        product_id = int(parts[1])
        quantity = float(parts[2]) if len(parts) > 2 else 1.0

        user_id = message.from_user.id
        basket = get_basket(basket_id)
        if not basket:
            await message.reply("Корзина с указанным ID не найдена.")
            return
        if basket.user_id != user_id:
            await message.reply("Вы не можете добавлять товары в чужую корзину.")
            return

        item = add_to_basket(basket_id, product_id, quantity)
        product = Product.get_by_id(product_id)

        await message.reply(
            f"Товар **{product.name}** добавлен в корзину **{basket.name}**.\n"
            f"Количество: {item.quantity}\n"
            f"Стоимость позиции: {product.price * item.quantity:.2f} ₽",
            parse_mode="Markdown"
        )

    except ValueError as e:
        await message.reply("Проверьте правильность числовых параметров (ID и количество).")
    except Exception as e:
        logger.error(f"Ошибка в команде /add_to_basket: {e}")
        await message.reply(f"Не удалось добавить товар: {e}")


async def remove_from_basket_command(message: types.Message, state: FSMContext):
    """
    Команда /remove_from_basket <item_id> - удалить позицию из корзины.
    """
    await state.finish()
    args = message.get_args()
    if not args:
        await message.reply("Укажите ID элемента корзины: /remove_from_basket <item_id>")
        return

    try:
        item_id = int(args)
        # Проверяем, что элемент принадлежит корзине пользователя
        item = BasketItem.get_or_none(BasketItem.id == item_id)
        if not item:
            await message.reply("Элемент с указанным ID не найден.")
            return
        basket = item.basket
        if basket.user_id != message.from_user.id:
            await message.reply("Вы не можете удалять элементы из чужой корзины.")
            return

        success = remove_from_basket(item_id)
        if success:
            await message.reply(f"Позиция #{item_id} удалена из корзины.")
        else:
            await message.reply("Не удалось удалить позицию.")

    except ValueError:
        await message.reply("ID элемента должен быть числом.")
    except Exception as e:
        logger.error(f"Ошибка в команде /remove_from_basket: {e}")
        await message.reply("Произошла ошибка при удалении позиции.")


def register_basket_handlers(dp):
    """
    Регистрирует обработчики команд корзины в диспетчере.
    """
    dp.register_message_handler(mybaskets_command, commands=['mybaskets'])
    dp.register_message_handler(create_basket_command, commands=['create_basket'])
    dp.register_message_handler(delete_basket_command, commands=['delete_basket'])
    dp.register_message_handler(basket_command, commands=['basket'])
    dp.register_message_handler(add_to_basket_command, commands=['add_to_basket'])
    dp.register_message_handler(remove_from_basket_command, commands=['remove_from_basket'])