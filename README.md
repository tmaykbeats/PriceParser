# PriceParser: Telegram Bot + Web Interface for Price Monitoring

## Overview

### Problem
Businesses and freelancers often need to monitor product prices (e.g., competitors), but manual tracking is time-consuming and inefficient.

### Solution
**PriceParser** is a Python-powered price tracking tool that scrapes data from websites, stores price history, detects changes, and sends updates via Telegram or renders them in a web interface using FastAPI + Jinja2.

### Impact
Automates the entire price-monitoring process, saves time, and helps users react faster to market changes through visual reports and timely alerts.

---

## About the Project

**PriceParser** is a lightweight full-stack solution that includes:

- 🤖 A Telegram bot (built with `aiogram`) for notifications and user commands.
- 🌐 A FastAPI web interface with HTML templates for viewing prices and trends.
- 📈 Historical graphs for each product (7‑day timeline).
- 💬 Flexible commands like `/report`, `/reportdelta`, `/history`, `/notifychange`.
- ⚙️ Per-user preference: receive all prices or only price changes.
- 🛒 **New:** Integration with **Product Inflation Tracker (PIT)** for parsing real‑world grocery prices with unit‑size awareness.
- 🛍️ **New:** Shopping basket functionality – create, manage, and calculate total cost of baskets.

The tool uses `BeautifulSoup`, `Selenium`, and `peewee` for scraping and storage, `matplotlib` for graph generation, and `schedule` for periodic tasks.

---

## New Capabilities (Recent Updates)

- **Integration with PIT (Product Inflation Tracker)** – parses food product prices from international stores (Пятёрочка, Дикси, Walmart, ATB Market, etc.) with support for package size and unit price (per kg/l/piece).
- **Automatic unit‑price calculation** – converts total price to price per unit for easy comparison.
- **Shopping basket functionality** – create multiple baskets, add/remove items, calculate total cost.
- **Extended test coverage** – comprehensive tests for models, PIT integration, and basket logic (see `TESTING.md`).
- **New Telegram bot commands** for PIT and basket management (see below).
- **Enhanced data models** – added fields for unit size, unit type, external ID, store, and price‑per‑unit.

---

## Features

- **Web Scraping**: Extracts product names and prices from a target source.
- **Price History**: Stores daily prices in SQLite for comparisons.
- **Telegram Notifications**: Sends hourly reports to subscribed users.
- **Subscription Model**: Users can subscribe/unsubscribe to notifications via Telegram commands.
- **Periodic Updates**: Runs hourly checks using the schedule library.
- **Selective Alerts**: Option to receive all updates or only price changes.
- **Sort & Filter**: Sort reports by name or price.
- **Web Interface (FastAPI)**:
  - Homepage with filterable, sortable product table
  - Price history charts
  - JSON API (`/api/products`, `/api/products/{name}`)
- **PIT Integration**:
  - Asynchronous parsing via Selenium
  - Support for multiple store configurations
  - Unit‑price calculation and storage
- **Shopping Baskets**:
  - Create, rename, delete baskets
  - Add/remove items, adjust quantities
  - Calculate total cost per basket
- **Bot Commands**:
  - Core commands: `/start`, `/subscribe`, `/unsubscribe`, `/report`, `/reportdelta`, `/notifychange`, `/sort`, `/history {product}`
  - PIT commands: `/pit_products`, `/price_per_unit`, `/compare_units`, `/run_pit_now`
  - Basket commands: `/mybaskets`, `/create_basket`, `/delete_basket`, `/basket`, `/add_to_basket`, `/remove_from_basket`

---

## How to Work with PriceParser

### Telegram Bot Usage

Find the bot in Telegram (e.g., t.me/PriceParserGoodBot, or @PriceParserGoodBot) or run locally (see Setup Instructions).

#### Core Commands
1. `/start` — greet the bot
2. `/subscribe` — receive hourly reports
3. `/unsubscribe` — stop updates
4. `/report` — get all product prices
5. `/reportdelta` — show only price changes
6. `/notifychange` — toggle notification mode (all vs only changes)
7. `/sort` — toggle sorting by name/price
8. `/history` — receive 7‑day chart
9. `/help` — show help message

#### PIT Commands
10. `/pit_products` — list products parsed via PIT
11. `/price_per_unit` — show price per unit for a product
12. `/compare_units` — compare unit prices across stores
13. `/run_pit_now` — manually trigger PIT parsing

#### Basket Commands
14. `/mybaskets` — list your shopping baskets
15. `/create_basket` — create a new basket
16. `/delete_basket` — delete a basket by name
17. `/basket` — view contents of a specific basket
18. `/add_to_basket` — add a product to a basket
19. `/remove_from_basket` — remove an item from a basket

---

### Web Interface

- Homepage: `http://localhost:8000`
  - Filter by category (e.g., `?category=Pokemon`)
  - Sort (e.g., `?sort=price`)
- Product chart: `http://localhost:8000/history/Bulbasaur`
- JSON API:
  - `/api/products` — all products
  - `/api/products?category=...` — by category
  - `/api/products/{name}` — individual product data

---

## Setup Instructions

### 1. Create Virtual Environment
Clone the repository:

```bash
git clone https://github.com/Rostislav62/PriceParser.git
cd PriceParser
```

Create and activate a virtual environment:

```bash
# Linux / macOS
python -m venv priceparser-bot
source priceparser-bot/bin/activate

# Windows
python -m venv priceparser-bot
.\priceparser-bot\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

**Note:** The `requirements.txt` now includes additional packages for PIT integration and testing:
- `selenium>=4.0.0`
- `webdriver-manager`
- `pytest>=7.0.0`
- `pytest-asyncio>=0.21.0`
- `pytest-mock>=3.0.0`

### 3. Selenium Setup (for PIT)
If you plan to use PIT parsing, you need a browser driver.

**For Firefox:**
- Install Firefox (if not already installed)
- Install `geckodriver` (automatically managed by `webdriver-manager`)

**For Chrome:**
- Install Chrome
- `webdriver-manager` will handle ChromeDriver automatically.

No additional configuration is required; the code uses `webdriver-manager` to provision drivers.

### 4. Create Database

Run the initialization script to create the SQLite database:

```bash
python init_db.py
```

### 5. Configure Telegram and Email

Create a `.env` file in the project root:

```env
BOT_TOKEN=your_telegram_bot_token
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USER=your_email@gmail.com
EMAIL_PASSWORD=your_email_password
```

- Replace `your_telegram_bot_token` with the token from BotFather.
- For email, configure SMTP settings (e.g., Gmail credentials).

### 6. Start the Telegram bot

```bash
python main.py
```

### 7. Run the web server

```bash
uvicorn web_app:app --reload
```

---

## Project Structure

```
PriceParser/
├── main.py                # Starts the Telegram bot and scheduler
├── handlers.py            # Telegram command logic (core commands)
├── config.py              # Configuration (Telegram token, SMTP settings)
├── models.py              # ORM models (Product, Subscription, PriceHistory, Basket, BasketItem)
├── utils.py               # Price saving/loading utilities
├── init_db.py             # Database initialization script
├── services/
│   ├── parser.py          # Web scraping logic (legacy)
│   ├── notifier.py        # Notification logic
│   ├── history.py         # Charting and historical data
│   ├── pit_parser.py      # Adapter for asynchronous PIT parsing
│   ├── pit_db.py          # Save PIT results to database
│   ├── pit_handlers.py    # Telegram bot commands for PIT
│   ├── basket.py          # Basket management functions
│   └── basket_handlers.py # Telegram bot commands for baskets
├── services/pit_integration/
│   ├── __init__.py
│   ├── store_config.txt   # Store‑specific parsing configuration
│   └── store_productscraper.py # Selenium‑based scraper
├── web_app.py             # FastAPI web interface
├── templates/             # Jinja2 HTML templates
├── static/                # CSS, images, and chart output
├── tests/                 # Comprehensive test suite
│   ├── __init__.py
│   ├── conftest.py        # pytest fixtures
│   ├── test_models.py     # Model tests
│   ├── test_pit_integration.py
│   └── test_basket.py
├── TESTING.md             # Detailed testing documentation
├── requirements.txt
└── .env
```

---

## Data Models

The database includes the following tables (defined in `models.py`):

### Product
- `name` – product name
- `price` – total price
- `category` – product category
- `timestamp` – last update time
- **New fields for PIT integration:**
  - `store` – store name (e.g., "Auchan")
  - `unit_size` – package size (e.g., 1.0)
  - `unit_type` – unit of measurement ("л", "кг", "шт")
  - `price_per_unit` – calculated price per unit
  - `external_id` – external identifier from PIT

### PriceHistory
- `product` – foreign key to Product
- `price` – historical price
- `unit_size`, `unit_type`, `price_per_unit` – preserved unit info for historical tracking
- `timestamp` – when the price was recorded

### Subscription
- `user_id` – Telegram user ID
- `subscribed` – subscription status
- `notify_only_on_change` – preference for change‑only notifications

### Basket
- `user_id` – Telegram user ID
- `name` – basket name
- `created_at` – creation timestamp

### BasketItem
- `basket` – foreign key to Basket
- `product` – foreign key to Product
- `quantity` – number of packages

---

## Testing

A comprehensive test suite is located in the `tests/` directory. See `TESTING.md` for full documentation.

### Quick Start

Install test dependencies (already in `requirements.txt`):

```bash
pip install -r requirements.txt
```

Run all tests:

```bash
python -m pytest tests/ -v
```

Run specific test modules:

```bash
python -m pytest tests/test_models.py -v
python -m pytest tests/test_basket.py -v
python -m pytest tests/test_pit_integration.py -v
```

### Test Coverage
- **`test_models.py`** – validates database models, relationships, and constraints.
- **`test_pit_integration.py`** – tests PIT parsing and database integration using mocks.
- **`test_basket.py`** – tests basket creation, item management, and total calculation.

Fixtures in `conftest.py` provide isolated test databases, sample data, and mocked Selenium/HTTP requests.

---

## Technologies

- **Python 3.8.10**: Core language.
- **aiogram 2.21**: Telegram Bot API framework.
- **BeautifulSoup**: HTML parsing.
- **Selenium**: Browser automation for PIT parsing.
- **webdriver‑manager**: Automatic driver management.
- **requests**: HTTP requests.
- **schedule**: Periodic tasks.
- **peewee**: SQLite ORM.
- **python‑dotenv**: Environment variables support.
- **FastAPI + Jinja2**: Web rendering.
- **matplotlib**: Charts.
- **pytest**: Testing framework.
- **pytest‑asyncio / pytest‑mock**: Async and mocking support.
- **Git**: Version control.

---

## Author

Rostislav — Full‑stack developer specializing in automation, bots, data scraping and API integration.
This project is part of my portfolio, showcasing expertise in Telegram bots, NLP, and data automation.

Telegram: @rostislav62

---

## License

MIT License
