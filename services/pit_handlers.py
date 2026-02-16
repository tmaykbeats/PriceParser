"""
Обработчики команд Telegram-бота для работы с данными PIT.
"""

import logging

from aiogram import types
from aiogram.dispatcher import FSMContext

from models import PriceHistory, Product
from services.pit_db import get_pit_products, save_pit_results
from services.pit_parser import run_pit_parsing

logger = logging.getLogger(__name__)


async def pit_products_command(message: types.Message, state: FSMContext):
    """
    Команда /pit_products - показывает список товаров, полученных через PIT.
    Можно фильтровать по магазину: /pit_products [store]
    """
    await state.finish()
    args = message.get_args()
    store_filter = args.strip() if args else None

    try:
        products = get_pit_products(store=store_filter)
        if not products:
            await message.reply(
                "Товары PIT не найдены."
                + (f" Фильтр по магазину: '{store_filter}'" if store_filter else "")
            )
            return

        lines = []
        for p in products:
            unit_info = (
                f" ({p.unit_size}{p.unit_type})" if p.unit_size and p.unit_type else ""
            )
            price_per_unit = (
                f", {p.price_per_unit:.2f} ₽/{p.unit_type}" if p.price_per_unit else ""
            )
            lines.append(
                f"• {p.store} - {p.name}{unit_info}: {p.price:.2f} ₽{price_per_unit}"
            )

        header = f"Товары PIT ({len(products)} шт.)"
        if store_filter:
            header += f" (магазин: {store_filter})"
        await message.reply(header + "\n" + "\n".join(lines))

    except Exception as e:
        logger.error(f"Ошибка в команде /pit_products: {e}")
        await message.reply("Произошла ошибка при получении списка товаров.")


async def price_per_unit_command(message: types.Message, state: FSMContext):
    """
    Команда /price_per_unit <product_id> - показывает детальную информацию о цене за единицу.
    """
    await state.finish()
    args = message.get_args()
    if not args:
        await message.reply("Укажите ID товара: /price_per_unit <id>")
        return

    try:
        product_id = int(args)
        product = Product.get_or_none(
            Product.id == product_id, Product.category == "pit"
        )
        if not product:
            await message.reply(
                "Товар с указанным ID не найден или не является товаром PIT."
            )
            return

        # Получаем историю цен
        history = (
            PriceHistory.select()
            .where(PriceHistory.product == product)
            .order_by(PriceHistory.timestamp.desc())
            .limit(5)
        )

        lines = [
            f"*{product.name}*",
            f"Магазин: {product.store}",
            f"Текущая цена: {product.price:.2f} ₽",
            f"Размер упаковки: {product.unit_size or '?'}{product.unit_type or ''}",
            f"Цена за единицу: {product.price_per_unit or '?'} ₽/{product.unit_type or 'ед.'}",
            "\n*История цен:*",
        ]

        for h in history:
            lines.append(
                f"• {h.timestamp.strftime('%d.%m %H:%M')}: {h.price:.2f} ₽ "
                f"({h.price_per_unit or '?'} ₽/{product.unit_type or 'ед.'})"
            )

        await message.reply("\n".join(lines), parse_mode="Markdown")

    except ValueError:
        await message.reply("ID товара должен быть числом.")
    except Exception as e:
        logger.error(f"Ошибка в команде /price_per_unit: {e}")
        await message.reply("Произошла ошибка при получении информации о товаре.")


async def compare_units_command(message: types.Message, state: FSMContext):
    """
    Команда /compare_units <product_name> - сравнивает цены за единицу в разных магазинах.
    """
    await state.finish()
    args = message.get_args()
    if not args:
        await message.reply(
            "Укажите название товара (частично): /compare_units <название>"
        )
        return

    try:
        products = (
            Product.select()
            .where((Product.category == "pit") & (Product.name.contains(args)))
            .order_by(Product.price_per_unit)
        )

        if not products:
            await message.reply(f"Товары с названием, содержащим '{args}', не найдены.")
            return

        lines = [f"*Сравнение цен за единицу: '{args}'*"]
        for p in products:
            unit_info = (
                f" ({p.unit_size}{p.unit_type})" if p.unit_size and p.unit_type else ""
            )
            lines.append(
                f"• {p.store}: {p.price:.2f} ₽{unit_info} → {p.price_per_unit or '?'} ₽/{p.unit_type or 'ед.'}"
            )

        await message.reply("\n".join(lines), parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Ошибка в команде /compare_units: {e}")
        await message.reply("Произошла ошибка при сравнении цен.")


async def run_pit_now_command(message: types.Message, state: FSMContext):
    """
    Команда /run_pit_now - запускает немедленный парсинг PIT (только для администраторов).
    """
    await state.finish()
    # Простая проверка на администратора (можно расширить)
    admin_ids = [123456789]  # заменить на реальные ID администраторов
    if message.from_user.id not in admin_ids:
        await message.reply("У вас нет прав для выполнения этой команды.")
        return

    try:
        await message.reply("Запуск парсинга PIT...")
        results = await run_pit_parsing()
        if results:
            stats = save_pit_results(results)
            await message.reply(
                f"Парсинг завершен!\n"
                f"Обработано: {stats['total_processed']}\n"
                f"Создано товаров: {stats['products_created']}\n"
                f"Обновлено товаров: {stats['products_updated']}\n"
                f"Добавлено записей истории: {stats['history_added']}"
            )
        else:
            await message.reply("Парсинг не вернул результатов.")
    except Exception as e:
        logger.error(f"Ошибка в команде /run_pit_now: {e}")
        await message.reply("Произошла ошибка при парсинге.")


def register_pit_handlers(dp):
    """
    Регистрирует обработчики команд PIT в диспетчере.
    """
    dp.register_message_handler(pit_products_command, commands=["pit_products"])
    dp.register_message_handler(price_per_unit_command, commands=["price_per_unit"])
    dp.register_message_handler(compare_units_command, commands=["compare_units"])
    dp.register_message_handler(run_pit_now_command, commands=["run_pit_now"])
