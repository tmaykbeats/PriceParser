# /PriceParser/services/history.py

import os
from datetime import datetime, timedelta

import matplotlib.pyplot as plt

from models import Product


def get_price_history(product_name=None, days=7):
    since = datetime.now() - timedelta(days=days)
    query = Product.select().where(Product.timestamp >= since)
    if product_name:
        query = query.where(Product.name == product_name)
    query = query.order_by(Product.timestamp)

    return [
        {
            "timestamp": record.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "price": record.price,
        }
        for record in query
    ]


def plot_price_history(data, product_name="product"):
    dates = [datetime.strptime(d["timestamp"], "%Y-%m-%d %H:%M:%S") for d in data]
    prices = [d["price"] for d in data]

    plt.figure(figsize=(10, 5))
    plt.plot(dates, prices, marker="o")
    plt.title(f"Price History for {product_name}")
    plt.xlabel("Date")
    plt.ylabel("Price")
    plt.grid(True)

    path = f"static/{product_name}_history.png"
    plt.tight_layout()
    plt.savefig(path)
    plt.close()
    return path
