# ~/PriceParser/handlers.py

import logging

from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext

from models import Subscription
from services.basket_handlers import register_basket_handlers
from services.history import get_price_history, plot_price_history
from services.parser import scrape_prices
from services.pit_handlers import register_pit_handlers
from utils import get_latest_prices, get_previous_prices, save_prices

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def start(message: types.Message, state: FSMContext):
    await state.finish()
    logger.info(f"User {message.from_user.id} started bot")
    await message.reply(
        "Welcome to PriceParser! Use /subscribe to receive price updates or /report for the latest prices."
    )


async def subscribe(message: types.Message, state: FSMContext):
    await state.finish()
    user_id = message.from_user.id
    Subscription.replace(user_id=user_id, subscribed=True).execute()
    logger.info(f"User {user_id} subscribed")
    await message.reply("You are now subscribed to hourly price reports.")


async def unsubscribe(message: types.Message, state: FSMContext):
    await state.finish()
    user_id = message.from_user.id
    Subscription.replace(user_id=user_id, subscribed=False).execute()
    logger.info(f"User {user_id} unsubscribed")
    await message.reply("You have unsubscribed from price reports.")


from aiogram.dispatcher.filters import Command


# Команда /sort — переключение сортировки между "name" и "price"
async def sort_command(message: types.Message, state: FSMContext):
    current_sort = await state.get_data()
    sort_by = current_sort.get("sort_by", "name")
    new_sort = "price" if sort_by == "name" else "name"
    await state.update_data(sort_by=new_sort)
    await message.reply(
        f"Sorting method switched to *{new_sort}*.", parse_mode="Markdown"
    )


# Команда /help — описание всех команд
async def help_command(message: types.Message):
    help_text = (
        "/start - Start the bot and receive a welcome message\n"
        "/subscribe - Subscribe to hourly price reports\n"
        "/unsubscribe - Unsubscribe from price reports\n"
        "/report - Get the current price report\n"
        "/reportchanges - Show only products with price changes\n"
        "/sort - Toggle report sorting (by name/price)\n"
        "/history - Show price history graph for the last 7 days\n"
        "/notifychange - Toggle notifications only when prices change\n"
        "/pit_products - Show products from PIT (optional: store filter)\n"
        "/price_per_unit - Show price per unit details by product ID\n"
        "/compare_units - Compare unit prices across stores\n"
        "/run_pit_now - Run PIT parsing immediately (admin only)\n"
        "/mybaskets - List your baskets\n"
        "/create_basket <name> - Create a new basket\n"
        "/delete_basket <id> - Delete a basket\n"
        "/basket <id> - Show basket contents with total cost\n"
        "/add_to_basket <basket_id> <product_id> [quantity] - Add product to basket\n"
        "/remove_from_basket <item_id> - Remove item from basket\n"
        "/help - Show this help message"
    )
    await message.reply(help_text)


# Обновлённая команда /report с учётом сортировки из состояния
async def report(message: types.Message, state: FSMContext):
    await state.finish()
    data = await state.get_data()
    sort_by = data.get("sort_by", "name")

    prices = await scrape_prices()
    if prices:
        save_prices(prices)
        latest = get_latest_prices()
        previous = get_previous_prices()

        categories = {}
        for name, data_price in prices.items():
            category = data_price.get("category", "uncategorized")
            if category not in categories:
                categories[category] = []
            old_price = previous.get(name)
            new_price = data_price["price"]
            if old_price is None:
                change = "🆕"
            elif old_price == new_price:
                change = "→"
            else:
                delta = new_price - old_price
                symbol = "🔺" if delta > 0 else "🔻"
                change = f"{symbol} ${abs(delta):.2f}"
            categories[category].append((name, new_price, change))

        lines = []
        for category in sorted(categories.keys()):
            lines.append(f"\n📦 *{category.title()}*")

            if sort_by == "price":
                sorted_items = sorted(categories[category], key=lambda x: x[1])
            else:  # default sort by name
                sorted_items = sorted(categories[category], key=lambda x: x[0].lower())

            for name, price, change in sorted_items:
                lines.append(f"• {name:15} | ${price:6.2f} | {change}")

        report_text = "\n".join(lines)
    else:
        report_text = "No prices available. Try again later."

    await message.reply(report_text, parse_mode="Markdown")
    logger.info(f"Sent report to {message.from_user.id}")


async def report_changes_command(message: types.Message, state: FSMContext):
    await state.finish()
    data = await state.get_data()
    sort_by = data.get("sort_by", "name")

    prices = await scrape_prices()
    if prices:
        save_prices(prices)
        latest = get_latest_prices()
        previous = get_previous_prices()

        categories = {}
        for name, data_price in prices.items():
            category = data_price.get("category", "uncategorized")
            if category not in categories:
                categories[category] = []

            old_price = previous.get(name)
            new_price = data_price["price"]

            # Только изменения (включая новые)
            if old_price is None:
                change = "🆕"
            elif old_price == new_price:
                continue
            else:
                delta = new_price - old_price
                symbol = "🔺" if delta > 0 else "🔻"
                change = f"{symbol} ${abs(delta):.2f}"

            categories[category].append((name, new_price, change))

        lines = []
        for category in sorted(categories.keys()):
            if not categories[category]:
                continue
            lines.append(f"\n📦 *{category.title()}*")

            if sort_by == "price":
                sorted_items = sorted(categories[category], key=lambda x: x[1])
            else:
                sorted_items = sorted(categories[category], key=lambda x: x[0].lower())

            for name, price, change in sorted_items:
                lines.append(f"• {name:15} | ${price:6.2f} | {change}")

        report_text = "\n".join(lines) if lines else "No price changes found."
    else:
        report_text = "No prices available. Try again later."

    await message.reply(report_text, parse_mode="Markdown")


async def history_command(message: types.Message):
    # Получаем историю за 7 дней
    history = get_price_history(days=7)
    if not history:
        await message.reply("No price history available for the last 7 days.")
        return

    # Создаём график и получаем путь к файлу
    img_path = plot_price_history(history)

    # Отправляем картинку пользователю
    with open(img_path, "rb") as photo:
        await message.answer_photo(photo, caption="Price history for the last 7 days")


async def notify_change_toggle(message: types.Message):
    print(f"[DEBUG] /notifychange triggered by user {message.from_user.id}")
    user_id = message.from_user.id
    sub, created = Subscription.get_or_create(user_id=user_id)
    sub.notify_only_on_change = not sub.notify_only_on_change
    sub.save()
    status = "enabled" if sub.notify_only_on_change else "disabled"
    await message.reply(
        f"Notify only on price changes is now *{status}*.", parse_mode="Markdown"
    )


def register_handlers(dp: Dispatcher):
    dp.register_message_handler(start, commands=["start"])
    dp.register_message_handler(subscribe, commands=["subscribe"])
    dp.register_message_handler(unsubscribe, commands=["unsubscribe"])
    dp.register_message_handler(report, commands=["report"])
    dp.register_message_handler(sort_command, commands=["sort"])
    dp.register_message_handler(help_command, commands=["help"])
    dp.register_message_handler(history_command, commands=["history"])
    dp.register_message_handler(notify_change_toggle, commands=["notifychange"])
    dp.register_message_handler(report_changes_command, commands=["reportchanges"])
    # Регистрация обработчиков PIT
    register_pit_handlers(dp)
    # Регистрация обработчиков корзины
    register_basket_handlers(dp)
