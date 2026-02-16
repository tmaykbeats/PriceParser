# /services/parser.py

import logging

import requests
from bs4 import BeautifulSoup

from config import SCRAPE_URL

logger = logging.getLogger(__name__)


async def scrape_prices():
    try:
        response = requests.get(SCRAPE_URL)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        products = soup.find_all("li", class_="product")
        prices = {}

        for product in products:
            name_tag = product.find("h2", class_="woocommerce-loop-product__title")
            price_tag = product.find("span", class_="woocommerce-Price-amount")

            if not name_tag or not price_tag:
                continue

            name = name_tag.text.strip()
            price_text = (
                price_tag.text.strip()
                .replace("£", "")
                .replace("$", "")
                .replace(",", "")
                .strip()
            )

            try:
                price = float(price_text)
            except ValueError as e:
                logger.error(
                    f"Could not convert price '{price_tag.text}' for product '{name}': {e}"
                )
                continue

            # 🆕 Ищем категорию
            class_list = product.get("class", [])
            categories = [
                cls.replace("product_cat-", "")
                for cls in class_list
                if cls.startswith("product_cat-")
            ]
            category = categories[0] if categories else "uncategorized"

            prices[name] = {"price": price, "category": category}

        logger.info(f"Scraped {len(prices)} products")
        return prices

    except Exception as e:
        logger.error(f"Error scraping prices: {str(e)}")
        return {}
