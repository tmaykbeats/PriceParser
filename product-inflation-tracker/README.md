# Product Inflation Tracker

A web scraping system for monitoring real-world product inflation by tracking prices across multiple international grocery store websites.

## Acknowledgments

This project was developed as a response to the gap between official inflation statistics and real-world price changes experienced by consumers. It demonstrates advanced web scraping techniques, proper database design, and thoughtful error handling strategies.

The system's modular design and configuration-driven approach ensure adaptability to changing requirements and expanding monitoring scope without requiring significant architectural modifications.

---

*"In a world where prices are treated like state secrets, this tracker brings transparency to everyday inflation."*

## Overview

This project emerged from the observation that official inflation rates often don't reflect the real price changes experienced by consumers in their daily shopping. While central banks might report 3% inflation, the actual prices of everyday items like bread, milk, and eggs can vary significantly from this average.

The Product Inflation Tracker solves this by:
- Automatically collecting price data from grocery store websites
- Tracking the cheapest products in each category to reflect real consumer behavior
- Calculating actual inflation rates based on price changes over time
- Supporting multiple stores across different countries

## The Challenge: HTML Chaos

Building a price tracker in 2025 turned out to be far more complex than expected. Modern e-commerce websites present several challenges:

### 1. CAPTCHA Walls
Almost every store now requires CAPTCHA verification just to view product prices, treating basic price information like state secrets.

### 2. Duplicated CSS Selectors
Websites often use the same CSS classes for different data types:
```html
<span class="w_iUH7">Freshness Guaranteed Garlic Herb French Bread, 14 oz</span>
<span class="w_iUH7">current price $1.82</span>
```

### 3. Variable Content Selectors
CSS selectors with unique IDs per product make generic parsing nearly impossible:
```html
<h3 class="chakra-heading css-6qrhwc" id="21616092_EA" data-testid="product-title">Classic White Bistro</h3>
```

### 4. Nested Price Tags
Prices split across multiple nested HTML elements requiring complex parsing:
```html
<div class="product-price">
  <data class="product-price__top">
    <span>20<span class="product-price__coin">90</span></span> 
  </data>
</div>
```

## System Architecture

### Core Components

1. **Template-Based HTML Parser**: Flexible extraction system using HTML templates with "FFF" placeholders
2. **Selenium WebDriver Integration**: Real browser automation to bypass anti-bot measures. GeckoDriver is usehttps://github.com/mozilla/geckodriver/releasesd
3. **Multi-Store Configuration**: Support for different store layouts through configuration files
4. **Database Management**: SQLite-based storage with proper normalization
5. **Inflation Calculator**: Automated calculation of price change rates over time

### Workflow

```
Parse Configuration -> Initialize Database -> Process Each Store -> Extract Both Variants -> Save Results
```

## Configuration System

Each store is defined in a configuration file with the following structure:

```
STORE = SomeStore
COUNTRY = USA
PRODUCT = Bread

TITLE = [
<span data-automation-id="product-title" class="normal dark-gray mb0 mt1 lh-title f6 f5-l lh-copy">FFF</span>
]

PRICE = [
<span class="w_iUH7">current price FFF</span>
]

CURRENCY_MAP = ["$": "USD"]

URLS = [
cheapest: https://www.store.com/search?q=bread&sort=price_low
most_expensive: 
]
```

The "FFF" placeholder indicates where actual product data should be extracted from the webpage.

## Database Schema

The system uses a normalized SQLite database with three main tables:

### Store Table
- `store_id` (Primary Key)
- `name` (Unique)
- `country`

### ProductType Table
- `product_type_id` (Primary Key)
- `name` (Unique)

### PriceSample Table
- `sample_id` (Primary Key)
- `store_id` (Foreign Key)
- `product_type_id` (Foreign Key)
- `date`
- `variant` (cheapest/most_expensive)
- `full_name`
- `full_price_string`
- `price_number`
- `price_currency`
- `package_size_string`
- `package_size_number`
- `package_unit`
- `price_per_unit_string`
- `price_per_unit_number`
- `inflation_rate`

## Key Features

### Advanced Web Scraping
- **Selenium WebDriver**: Handles JavaScript-heavy sites and anti-bot detection
- **Template Matching**: Flexible HTML parsing using configuration templates
- **Error Handling**: Comprehensive error handling for network failures and parsing errors

### Data Processing Pipeline
- **Price Extraction**: Handles various decimal formats and currency symbols
- **Package Size Processing**: Extracts and standardizes product sizes and units
- **Unit Conversion**: Converts between different measurement systems (oz, g, kg, ml, l)
- **Price Per Unit Calculation**: Enables meaningful price comparisons across different package sizes

### Inflation Rate Calculation
```python
def calculate_inflation_rate(current_price, previous_price):
    if previous_price is None or previous_price == 0:
        return 0.0
    inflation_rate = ((current_price - previous_price) / previous_price) * 100
    return inflation_rate
```

## Technical Implementation

### Selenium Configuration
The system uses Firefox WebDriver with extensive customization to handle modern web security:

```python
def fetch_page_selenium(url):
    firefox_options = FirefoxOptions()
    firefox_options.binary_location = r"d:\...firefox.exe"
    firefox_options.set_capability("moz:webdriverClick", False)
    firefox_options.set_preference("dom.webdriver.enabled", False)
    firefox_options.set_preference("webdriver_accept_untrusted_certs", True)
```

### Template-Based Extraction
The core extraction mechanism compares HTML elements from configuration templates with actual webpage content:

```python
def extract_data_from_template(template_lines, page_html):
    """Extract data from page using template"""
    template_html = '\n'.join(template_lines)
    template_soup = BeautifulSoup(template_html, 'html.parser')
    page_soup = BeautifulSoup(page_html, 'html.parser')
    
    # Process each template element containing FFF
    for template_element in template_soup.find_all():
        if 'FFF' not in template_element.decode():
            continue
        
        matching_element = find_matching_element(page_soup, template_element)
        # Extract and process data...
```

### Unit Conversion Support
The system handles different measurement systems:

```python
UNIT_PATTERNS = {
    "oz": 0.0283495,
    "fl oz": 0.0295735,
    "lb": 0.453592,
    "kg": 1.0,
    "g": 0.001,
    "l": 1.0,
    "ml": 0.001,
    "Рі": 0.001,    # Cyrillic gram
    "РјР»": 0.001,   # Cyrillic milliliter
    "Р»": 1.0       # Cyrillic liter
}
```

## Installation and Setup

1. **Install Dependencies**:
   ```bash
   pip install selenium beautifulsoup4 sqlite3
   ```

2. **Configure Firefox**:
   - Install Firefox browser
   - Set up a dedicated Firefox profile for Selenium
   - Update the Firefox path in the configuration

3. **Configure Stores**:
   - Edit `store_config.txt` to add target stores
   - Define HTML templates for each store
   - Set up product URLs for price tracking

4. **Run the Tracker**:
   ```bash
   python store_productscraper.py
   ```

## Data Validation and Error Handling

The system implements validation:

- **Empty Data Checking**: Validates extracted content before database insertion
- **Database Constraints**: Maintains referential integrity
- **Exception Handling**: Protects against network failures and parsing errors
- **Selenium Timeout Management**: Handles dynamic content loading

## Performance Optimizations

- **Connection Pooling**: Efficient database connection management
- **Batch Processing**: Optimized configuration parsing and database operations
- **Memory Management**: Proper object lifecycle management
- **Selenium Lifecycle**: Efficient WebDriver initialization and cleanup

## Limitations

- **Anti-Bot Detection**: Modern websites employ sophisticated detection systems
- **Layout Changes**: Website updates require configuration template updates
- **Network Dependencies**: Requires stable internet connection for scraping

## Extensibility

The system is designed for easy extension:

### Adding New Stores
1. Add store configuration to `store_config.txt`
2. Define HTML templates for product title and price
3. Specify product search URLs
4. No code changes required

### Adding New Products
1. Update configuration with new product types
2. Add appropriate search URLs
3. System automatically handles new categories
