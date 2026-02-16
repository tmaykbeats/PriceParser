import os
import pickle
import re
import sqlite3
import sys
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service

CONFIG_FILE = "store_config.txt"
DATABASE_FILE = "product_inflation.db"

# === Units and Conversions ===
UNIT_BASE_LABELS = {
    "oz": "kg",
    "lb": "kg",
    "g": "kg",
    "kg": "kg",
    "ml": "l",
    "l": "l",
    "fl oz": "l",
    "г": "kg",
    "кг": "kg",
    "л": "l",
    "мл": "l",
    "шт": "one piece",
    "ea": "one piece",
    "piece": "one piece",
    "pieces": "one piece",
    "pcs": "one piece",
    "pc": "one piece",
}

UNIT_PATTERNS = {
    "oz": 0.0283495,
    "fl oz": 0.0295735,
    "lb": 0.453592,
    "kg": 1.0,
    "кг": 1.0,
    "g": 0.001,
    "l": 1.0,
    "ml": 0.001,
    "г": 0.001,
    "мл": 0.001,
    "л": 1.0,
    "шт": 1.0,
    "ea": 1.0,
    "piece": 1.0,
    "pieces": 1.0,
    "pcs": 1.0,
    "pc": 1.0,
}


def fetch_page_requests(url):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
        ),
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.google.com/",
        "Connection": "keep-alive",
        "DNT": "1",  # Do Not Track
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Upgrade-Insecure-Requests": "1",
    }
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def fetch_page_selenium(url):
    firefox_options = FirefoxOptions()
    firefox_options.binary_location = (
        r"d:\Programs and browsers\Mozilla Firefox-For-Selenium\firefox.exe"
    )
    # firefox_options.add_argument("--headless")
    firefox_options.set_capability("moz:webdriverClick", False)

    firefox_options.set_preference("javascript.enabled", True)
    firefox_options.set_preference("network.cookie.lifetimePolicy", 0)
    # firefox_options.set_preference("network.cookie.cookieBehavior", 0)

    profile_path = r"d:\Programs and browsers\Mozilla Firefox-For-Selenium\7wztt9ek.firefox-for-selenium"
    firefox_options.add_argument(f"--profile")
    firefox_options.add_argument(profile_path)

    # Enhanced SSL/TLS settings
    firefox_options.set_preference("security.enterprise_roots.enabled", True)
    firefox_options.set_preference("dom.webdriver.enabled", False)
    firefox_options.set_preference("webdriver_accept_untrusted_certs", True)
    firefox_options.set_preference("acceptInsecureCerts", True)

    # Additional SSL/TLS preferences
    firefox_options.set_preference(
        "security.tls.insecure_fallback_hosts", "www.hipercor.es"
    )
    firefox_options.set_preference("security.cert_pinning.enforcement_level", 0)
    firefox_options.set_preference("security.mixed_content.block_active_content", False)
    firefox_options.set_preference(
        "security.mixed_content.block_display_content", False
    )
    firefox_options.set_preference("security.tls.hello_downgrade_check", False)
    firefox_options.set_preference("security.tls.version.enable-deprecated", True)

    # Network settings
    firefox_options.set_preference("network.http.connection-timeout", 60)
    firefox_options.set_preference("network.http.connection-retry-timeout", 60)

    # User agent to avoid detection
    firefox_options.set_preference(
        "general.useragent.override",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
    )

    driver_path = os.path.join(os.getcwd(), "geckodriver.exe")
    service = Service(executable_path=driver_path)

    driver = webdriver.Firefox(service=service, options=firefox_options)

    try:
        # print(f"Attempting to load: {url}")
        driver.get(url)
        driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        # Wait for page to load and check if we reached an error page
        time.sleep(15)
        current_url = driver.current_url

        if "about:neterror" in current_url:
            print(f"Error: Reached Firefox error page")
            print(f"Current URL: {current_url}")
            return None

        # Additional wait for dynamic content
        time.sleep(15)
        html = driver.page_source
        # print(f"Successfully loaded page, HTML length: {len(html)}")
        return html

    except Exception as e:
        print(f"Exception during page load: {e}")
        return None
    finally:
        driver.quit()


# Save Selenium output into HTML file on localdisk - for debugging
# This function is called from main() - uncomment the call to activate it
def save_html_to_file(html_content, store_name, variant):
    """Save HTML content to file for debugging"""
    # Create a safe filename
    safe_store_name = re.sub(r"[^\w\-_\.]", "_", store_name)
    filename = f"{safe_store_name}_{variant}_page.html"
    filepath = os.path.join(os.getcwd(), filename)

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"HTML saved to: {filename}")
    except Exception as e:
        print(f"Error saving HTML: {e}")


def create_database():
    """Create database and tables if they don't exist"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()

    # Create Store table with country column
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS Store (
            store_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            country TEXT
        )
    """
    )

    # Create ProductType table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS ProductType (
            product_type_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
    """
    )

    # Create PriceSample table with all required columns
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS PriceSample (
            sample_id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id INTEGER NOT NULL,
            product_type_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            variant TEXT CHECK(variant IN ('cheapest', 'most_expensive')) NOT NULL,
            full_name TEXT,
            full_price_string TEXT,
            price_number REAL NOT NULL,
            price_currency TEXT,
            package_size_string TEXT,
            package_size_number REAL,
            package_unit TEXT,
            price_per_unit_string TEXT,
            price_per_unit_number REAL,
            inflation_rate REAL,
            FOREIGN KEY (store_id) REFERENCES Store(store_id),
            FOREIGN KEY (product_type_id) REFERENCES ProductType(product_type_id),
            UNIQUE(store_id, product_type_id, date, variant)
        )
    """
    )

    conn.commit()
    conn.close()


def get_or_create_store(store_name, country_name):
    """Get store_id for store name, create if doesn't exist"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()

    # Try to find existing store
    cursor.execute("SELECT store_id FROM Store WHERE name = ?", (store_name,))
    result = cursor.fetchone()

    if result:
        store_id = result[0]
    else:
        # Create new store with country
        cursor.execute(
            "INSERT INTO Store (name, country) VALUES (?, ?)",
            (store_name, country_name),
        )
        store_id = cursor.lastrowid
        conn.commit()

    conn.close()
    return store_id


def get_or_create_product_type(product_name):
    """Get product_type_id for product name, create if doesn't exist"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()

    # Try to find existing product type
    cursor.execute(
        "SELECT product_type_id FROM ProductType WHERE name = ?", (product_name,)
    )
    result = cursor.fetchone()

    if result:
        product_type_id = result[0]
    else:
        # Create new product type
        cursor.execute("INSERT INTO ProductType (name) VALUES (?)", (product_name,))
        product_type_id = cursor.lastrowid
        conn.commit()

    conn.close()
    return product_type_id


def extract_price_info(price_string, currency_map):
    """Extract price number from price string and get currency from currency_map"""
    if not price_string:
        return 0.0, ""

    currency = ""
    if currency_map:
        currency = list(currency_map.values())[0]

    price_clean = re.sub(r"[^\d.,]", "", price_string)

    # --- Normalize separators based on position and length ---
    if "," in price_clean and "." in price_clean:
        # Both separators exist: decide which is decimal
        if price_clean.rfind(",") > price_clean.rfind("."):
            # Example: 1.390,80 -> thousands '.' and decimal ','
            price_clean = price_clean.replace(".", "").replace(",", ".")
        else:
            # Example: 2,499.99 -> thousands ',' and decimal '.'
            price_clean = price_clean.replace(",", "")
    elif "," in price_clean:
        # Only comma present
        parts = price_clean.split(",")
        if len(parts[-1]) == 2:
            # Likely decimal comma: 1390,80 -> 1390.80
            price_clean = price_clean.replace(",", ".")
        else:
            # Likely thousands comma: 1,390 -> 1390
            price_clean = price_clean.replace(",", "")
    elif "." in price_clean:
        # Only dot present
        parts = price_clean.split(".")
        if len(parts[-1]) >= 3:
            # Likely thousands dot: 1.390 -> 1390
            price_clean = price_clean.replace(".", "")
        # else leave as is (13.90)
    # ---------------------------------------------------------

    try:
        price_number = float(price_clean)
    except:
        price_number = 0.0

    print(f"Price number to database: {price_number}")
    return price_number, currency


def extract_package_info(title_string):
    """Extract package size and unit from product title"""
    if not title_string:
        return "", 0.0, ""

    # Look for patterns like "24 oz", "2L", "500g", etc.
    patterns = [
        r"(\d+(?:[,\.]\d+)?)\s*(oz|lb|g|kg|ml|l|fl oz|г|мл|л|кг|шт|ea|piece|pieces|pcs|pc)\b",
        r"(\d+(?:[,\.]\d+)?)\s*(ounce|pound|gram|kilogram|liter|litre)\b",
    ]

    for pattern in patterns:
        matches = re.findall(pattern, title_string, re.IGNORECASE)
        if matches:
            # Take the first match
            size_number_str, unit = matches[0]

            # Handle comma as decimal separator
            size_number_str = size_number_str.replace(",", ".")
            size_number = float(size_number_str)
            unit = unit.lower()

            # Normalize unit names
            unit_map = {
                "ounce": "oz",
                "pound": "lb",
                "gram": "g",
                "kilogram": "kg",
                "liter": "l",
                "litre": "l",
                "кг": "kg",
                "pieces": "piece",
                "pcs": "pc",
            }
            unit = unit_map.get(unit, unit)

            package_string = f"{size_number} {unit}"
            return package_string, size_number, unit

    return "", 0.0, ""


def calculate_price_per_unit(price_number, package_size, package_unit, currency):
    """Calculate price per standard unit (kg or l or one piece)"""
    if package_size == 0 or not package_unit:
        return "", 0.0

    # Convert to standard unit
    if package_unit not in UNIT_PATTERNS:
        return "", 0.0

    # Get conversion factor
    conversion_factor = UNIT_PATTERNS[package_unit]
    standard_unit = UNIT_BASE_LABELS[package_unit]

    # Convert package size to standard unit
    standard_size = package_size * conversion_factor

    if standard_size == 0:
        return "", 0.0

    # Calculate price per standard unit
    price_per_unit = price_number / standard_size

    # Round to 2 decimal places for currency precision
    price_per_unit = round(price_per_unit, 2)

    # Format the string with proper decimal formatting
    price_per_unit_string = f"{price_per_unit:.2f} {currency}/{standard_unit}"

    print(f"Price per unit string to database: {price_per_unit_string}")
    return price_per_unit_string, price_per_unit


def get_previous_price(store_id, product_type_id, variant):
    """Get the most recent price for calculating inflation"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT price_number FROM PriceSample
        WHERE store_id = ? AND product_type_id = ? AND variant = ?
        ORDER BY date DESC LIMIT 1
    """,
        (store_id, product_type_id, variant),
    )

    result = cursor.fetchone()
    conn.close()

    if result:
        return result[0]
    else:
        return None


def calculate_inflation_rate(current_price, previous_price):
    """Calculate inflation rate as percentage"""
    if previous_price is None or previous_price == 0:
        return 0.0  # Return 0 instead of None for first entry

    inflation_rate = ((current_price - previous_price) / previous_price) * 100
    return round(inflation_rate, 3)  # Round to 3 decimal places


def get_current_date_string():
    """Get current date as string in YYYY-MM-DD format"""
    now = datetime.now()
    date_string = now.strftime("%Y-%m-%d")
    return date_string


def save_to_database(
    store_name,
    country_name,
    product_name,
    variant,
    full_name,
    full_price_string,
    currency_map,
):
    """Save extracted data to database"""
    # Check if product title or price is empty
    if not full_name or not full_name.strip():
        print(
            f"✗ Skipping save: Product title is empty for {store_name} - {product_name} ({variant})"
        )
        return

    if not full_price_string or not full_price_string.strip():
        print(
            f"✗ Skipping save: Product price is empty for {store_name} - {product_name} ({variant})"
        )
        return

    # Get or create store and product type IDs
    store_id = get_or_create_store(store_name, country_name)
    product_type_id = get_or_create_product_type(product_name)

    # Extract price information using currency_map
    price_number, price_currency = extract_price_info(full_price_string, currency_map)

    # print(f"Currency map for {store_name}: {currency_map}")
    # print(f"Extracted price: {price_number}, currency: {price_currency}")

    # Extract package information
    package_string, package_size, package_unit = extract_package_info(full_name)

    # Calculate price per unit
    price_per_unit_string, price_per_unit_number = calculate_price_per_unit(
        price_number, package_size, package_unit, price_currency
    )

    # Get previous price for inflation calculation
    previous_price = get_previous_price(store_id, product_type_id, variant)
    inflation_rate = calculate_inflation_rate(price_number, previous_price)

    # --- Added validation checks ---
    # Check for empty or invalid numeric values
    if (
        not full_name.strip()
        or not full_price_string.strip()
        or not package_string.strip()
        or not price_per_unit_string.strip()
        or price_number <= 0
        or package_size <= 0
        or price_per_unit_number <= 0
        or not isinstance(price_number, (int, float))
        or not isinstance(package_size, (int, float))
        or not isinstance(price_per_unit_number, (int, float))
        or not package_unit
        or not package_unit.strip()
    ):
        print(
            f"✗ Skipping save: Invalid or incomplete data for {store_name} - {product_name} ({variant})"
        )
        return
    # --- End of added checks ---

    # Get current date as string
    current_date_string = get_current_date_string()
    # print(f"Current date: {current_date_string}")

    # Insert into database
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            INSERT OR REPLACE INTO PriceSample (
                store_id, product_type_id, date, variant, full_name,
                full_price_string, price_number, price_currency,
                package_size_string, package_size_number, package_unit,
                price_per_unit_string, price_per_unit_number, inflation_rate
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                store_id,
                product_type_id,
                current_date_string,
                variant,
                full_name,
                full_price_string,
                price_number,
                price_currency,
                package_string,
                package_size,
                package_unit,
                price_per_unit_string,
                price_per_unit_number,
                inflation_rate,
            ),
        )

        conn.commit()
        print(
            f"✓ Saved to database: {store_name} - {product_name} ({variant}) on {current_date_string}"
        )

        # if inflation_rate is not None:
        #    print(f"  Inflation rate: {inflation_rate:.2f}%")
        # else:
        #    print(f"  Inflation rate: N/A (first entry)")

    except sqlite3.Error as e:
        print(f"✗ Database error: {e}")

    conn.close()


def parse_config(file_path):
    with open(file_path, "r", encoding="utf-8-sig") as f:
        lines = [line.strip() for line in f if line.strip()]

    configs = []
    i = 0
    while i < len(lines):
        if lines[i].startswith("STORE"):
            entry = {"TITLE": [], "PRICE": [], "URLS": {}, "CURRENCY_MAP": {}}
            entry["STORE"] = lines[i].split("=", 1)[1].strip()
            entry["COUNTRY"] = lines[i + 1].split("=", 1)[1].strip()
            entry["PRODUCT"] = lines[i + 2].split("=", 1)[1].strip()
            i = i + 3

            # Find TITLE section
            while i < len(lines) and not lines[i].startswith("TITLE"):
                i = i + 1
            i = i + 1  # skip TITLE = [
            while i < len(lines) and not lines[i].startswith("]"):
                entry["TITLE"].append(lines[i])
                i = i + 1
            i = i + 1

            # Find PRICE section
            while i < len(lines) and not lines[i].startswith("PRICE"):
                i = i + 1
            i = i + 1  # skip PRICE = [
            while i < len(lines) and not lines[i].startswith("]"):
                entry["PRICE"].append(lines[i])
                i = i + 1
            i = i + 1

            # Find CURRENCY_MAP section
            while i < len(lines) and not lines[i].startswith("CURRENCY_MAP"):
                i = i + 1
            if i < len(lines):
                currency_line = lines[i]
                # Parse the currency map - format: CURRENCY_MAP = ["$": "USD"]
                try:
                    # Extract the content between [ and ]
                    start = currency_line.find("[")
                    end = currency_line.find("]")
                    if start != -1 and end != -1:
                        currency_content = currency_line[start + 1 : end]
                        # Parse "symbol": "code" format
                        import re

                        matches = re.findall(
                            r'"([^"]+)":\s*"([^"]+)"', currency_content
                        )
                        for symbol, code in matches:
                            entry["CURRENCY_MAP"][symbol] = code
                except:
                    print(f"Warning: Could not parse currency map for {entry['STORE']}")
                i = i + 1

            # Find URLS section
            while i < len(lines) and not lines[i].startswith("URLS"):
                i = i + 1
            i = i + 1  # skip URLS = [
            while i < len(lines) and not lines[i].startswith("]"):
                line = lines[i]
                if "cheapest:" in line:
                    entry["URLS"]["cheapest"] = line.split(":", 1)[1].strip()
                elif "most_expensive:" in line:
                    entry["URLS"]["most_expensive"] = line.split(":", 1)[1].strip()
                i = i + 1
            i = i + 1
            configs.append(entry)
        else:
            i = i + 1
    return configs


def check_element_attributes(element, required_attrs):
    """Check if element has all required attributes - template attrs must be subset of element attrs"""
    for attr_name, required_value in required_attrs.items():
        if attr_name == "class":
            # Handle class attribute - all required classes must be present
            if isinstance(required_value, list):
                required_classes = set(required_value)
            else:
                required_classes = set(required_value.split())
            element_classes = set(element.get("class", []))
            if not required_classes.issubset(element_classes):
                return False
        else:
            # Handle other attributes - element must have the attribute with matching value
            # But element can have additional attributes not in template
            if element.get(attr_name) != required_value:
                return False
    return True


def find_matching_element(page_soup, template_element):
    tag_name = template_element.name
    required_attrs = template_element.attrs

    ##print(f"Looking for {tag_name} with attributes: {required_attrs}")

    candidates = page_soup.find_all(tag_name)
    ##print(f"Found {len(candidates)} {tag_name} elements in page")

    template_text = template_element.get_text().strip()
    prefix = template_text.split("FFF")[0].strip()

    for candidate in candidates:
        if not check_element_attributes(candidate, required_attrs):
            continue

        candidate_text = candidate.get_text(strip=True)

        # Check if candidate text contains prefix, or accept if prefix empty
        if prefix == "" or prefix.lower() in candidate_text.lower():
            ##print(f"Found matching element: {candidate}")
            return candidate

    print("No matching element found")
    return None


def remove_struck_elements(element):
    """Remove descendant elements that likely contain struck/old prices."""
    if element is None:
        return
    # keywords that commonly indicate old/line-through prices
    keywords = [
        "line-through",
        "line_through",
        "old",
        "strike",
        "strike-through",
        "product-price__old",
        "price--old",
        "text-decoration-line-through",
    ]
    for desc in list(element.find_all(True)):
        classes = desc.get("class", [])
        cls_string = " ".join(classes).lower() if classes else ""
        # If any keyword appears in the class string, remove the descendant
        if any(k in cls_string for k in keywords):
            desc.decompose()
        else:
            # also check other attributes that might indicate old price
            # e.g. style="text-decoration: line-through"
            style = desc.get("style", "") or ""
            if "line-through" in style:
                desc.decompose()


def extract_text_from_element(element, template_element):
    """Extract text from element, handling nested FFF placeholders"""
    template_text = template_element.get_text()
    # remove struck-through/old-price nodes before extracting
    remove_struck_elements(element)

    element_text = element.get_text(strip=True)

    # If template has no FFF, return empty
    if "FFF" not in template_text:
        return ""

    # For simple cases with one FFF
    if template_text.count("FFF") == 1:
        # Split template by FFF to get prefix and suffix
        template_parts = template_text.split("FFF")
        prefix = template_parts[0]
        suffix = template_parts[1].strip() if len(template_parts) > 1 else ""

        # Find the part between prefix and suffix
        start_pos = 0
        if prefix:
            prefix_pos = element_text.lower().find(prefix.lower())
            if prefix_pos >= 0:
                start_pos = prefix_pos + len(prefix)
            else:
                # If prefix not found, might be exact match case
                return ""

        end_pos = len(element_text)
        if suffix:
            suffix_pos = element_text.lower().find(suffix.lower(), start_pos)
            if suffix_pos >= 0:
                end_pos = suffix_pos

        extracted = element_text[start_pos:end_pos].strip()
        return extracted

    # For multiple FFF, return the whole text (complex nested structure)
    return element_text


def extract_data_from_template(template_lines, page_html):
    """Extract data from page using template"""
    template_html = "\n".join(template_lines)
    # print(f"Template HTML: {template_html}")

    # Fix malformed template HTML - if it starts with attributes, add opening tag
    if template_html.strip().startswith("class=") or template_html.strip().startswith(
        "data-"
    ):
        template_html = "<a " + template_html

    template_soup = BeautifulSoup(template_html, "html.parser")
    page_soup = BeautifulSoup(page_html, "html.parser")

    extracted_parts = []
    processed_elements = []

    # Process each template element that contains FFF
    for template_element in template_soup.find_all():
        if "FFF" not in template_element.decode():
            continue

        # print(f"Processing template: {template_element}")

        # Find matching element in page
        matching_element = find_matching_element(page_soup, template_element)

        if matching_element:
            # Skip if we already processed this element or its parent/child
            skip_element = False
            for processed in processed_elements:
                # Skip if same element
                if matching_element == processed:
                    skip_element = True
                    break
                # Skip if this element is inside a processed element
                if matching_element in processed.descendants:
                    skip_element = True
                    break
                # Skip if a processed element is inside this element
                if processed in matching_element.descendants:
                    skip_element = True
                    break

            if skip_element:
                # print("Skipping - element already processed or related")
                continue

            # Extract text based on template complexity
            if len(template_element.find_all()) > 0:
                # Complex nested template - try to remove old/struck price elements first
                # Work on a copy to avoid altering original page structure used elsewhere
                # BeautifulSoup doesn't provide an easy deep-copy, so operate on the element itself
                remove_struck_elements(matching_element)
                extracted_text = matching_element.get_text(strip=True)
                extracted_text = " ".join(extracted_text.split())  # Clean whitespace
            else:
                # Simple template - use targeted extraction
                extracted_text = extract_text_from_element(
                    matching_element, template_element
                )

            if extracted_text:
                ##print(f"Extracted text: '{extracted_text}'")
                extracted_parts.append(extracted_text)
                processed_elements.append(matching_element)

    # Combine all parts and remove duplicates while preserving order
    final_parts = []
    for part in extracted_parts:
        if part not in final_parts:
            final_parts.append(part)

    if len(final_parts) == 3 and final_parts[0].isdigit() and final_parts[1].isdigit():
        final_result = f"{final_parts[0]}.{final_parts[1]} {final_parts[2]}"
    elif (
        len(final_parts) == 2 and final_parts[0].isdigit() and final_parts[1].isdigit()
    ):
        final_result = f"{final_parts[0]}.{final_parts[1]}"
    elif len(final_parts) >= 2:
        num1 = re.sub(r"\D", "", final_parts[0])
        num2 = re.sub(r"\D", "", final_parts[1])
        if num1.isdigit() and num2.isdigit() and len(num2) == 2:
            joined_price = f"{int(num1)}.{num2}"
            if len(final_parts) > 2:
                final_result = f"{joined_price}{''.join(final_parts[2:])}"
            else:
                final_result = joined_price
        else:
            final_result = " ".join(final_parts)
    elif len(final_parts) == 2:
        final_result = " ".join(final_parts)
    else:
        # New fallback: handle single numeric block with implicit decimal (e.g. 2290 -> 22.90)
        if len(final_parts) == 1:
            num = re.sub(r"\D", "", final_parts[0])
            if num.isdigit() and len(num) > 3 and num[-2:] != "00":
                formatted = f"{int(num[:-2])}.{num[-2:]}"
                final_result = final_parts[0].replace(num, formatted)
            else:
                final_result = final_parts[0]
        else:
            final_result = " ".join(final_parts)

    print(f"Final result extracted: '{final_result}'")
    return final_result


def main():
    if not os.path.exists(CONFIG_FILE):
        print(f"Error: '{CONFIG_FILE}' not found in current directory.")
        return

    # Create database if it doesn't exist
    print("Setting up database...")
    create_database()
    print(f"Database '{DATABASE_FILE}' ready.")

    configs = parse_config(CONFIG_FILE)
    print(f"Loaded {len(configs)} store configurations\n")

    for config in configs:
        print(f"{'='*50}")
        print(
            f"Processing: {config['STORE']} - {config['PRODUCT']} ({config['COUNTRY']})"
        )

        for variant in ["cheapest", "most_expensive"]:
            url = config["URLS"].get(variant)
            if url:
                print(f"\nProcessing {variant} variant: {url}")

                # Fetch HTML from URL using Selenium
                # print("Fetching webpage...")
                page_html = fetch_page_selenium(url)

                # Saves Selenium output into HTML file on localdisk
                # save_html_to_file(page_html, config['STORE'], variant)

                # print("\n--- Extracting TITLE ---")
                product_title = extract_data_from_template(config["TITLE"], page_html)

                # print("\n--- Extracting PRICE ---")
                product_price = extract_data_from_template(config["PRICE"], page_html)

                # Show results
                print(f"\n=== RESULTS for {config['STORE']} ({variant}) ===")
                print(f"Store Name: {config['STORE']}")
                print(f"Country: {config['COUNTRY']}")
                print(f"Product Name: {config['PRODUCT']}")
                print(f"Product Variant: {variant}")
                print(f"Full Product Title: {product_title}")
                print(f"Full Price: {product_price}")

                # Save to database
                # print(f"\n--- Saving to Database ---")
                save_to_database(
                    config["STORE"],
                    config["COUNTRY"],
                    config["PRODUCT"],
                    variant,
                    product_title,
                    product_price,
                    config["CURRENCY_MAP"],
                )

                print("-" * 50)
            else:
                print(f"No URL provided for {variant}")

    print(f"\nScraping completed. Data saved to '{DATABASE_FILE}'.")


if __name__ == "__main__":
    main()
    sys.exit()
