# ~/PriceParser/services/notifier.py

from models import Subscription  # Импортируем модель Subscription


async def notify_subscribers(bot, prices):
    if not prices:
        return
    latest = get_latest_prices()
    previous = get_previous_prices()

    # Подготовим полные отчёты с изменениями для каждого продукта
    full_report_lines = []
    changed_report_lines = []

    for name, price in prices.items():
        change = ""
        if name in previous and previous[name] != price:
            delta = price - previous[name]
            direction = "up" if delta > 0 else "down"
            change = f" ({direction} ${abs(delta):.2f})"
            changed_report_lines.append(f"Product: {name}, Price: ${price:.2f}{change}")
        else:
            # Если цена не изменилась или нет в previous — в full_report, но не в changed_report
            full_report_lines.append(f"Product: {name}, Price: ${price:.2f}{change}")

        # Добавляем в полный отчёт всё подряд, включая изменённые
        if change:
            full_report_lines.append(f"Product: {name}, Price: ${price:.2f}{change}")
        elif name not in previous:
            # новый товар
            full_report_lines.append(f"Product: {name}, Price: ${price:.2f} (new)")

    full_report_text = "\n".join(full_report_lines)
    changed_report_text = "\n".join(changed_report_lines)

    # Телеграм уведомления
    for sub in Subscription.select().where(Subscription.subscribed == True):
        user_id = sub.user_id
        try:
            if sub.notify_only_on_change:
                if changed_report_text:
                    await bot.send_message(user_id, changed_report_text)
                    logger.info(f"Sent price changes report to {user_id}")
                else:
                    logger.info(f"No price changes to notify user {user_id}")
            else:
                # Отправляем полный отчёт всегда
                await bot.send_message(user_id, full_report_text)
                logger.info(f"Sent full price report to {user_id}")
        except Exception as e:
            logger.error(f"Error sending Telegram report to {user_id}: {str(e)}")

    # Email-уведомления оставляем без изменений, если нужно — можно сделать тоже проверку
