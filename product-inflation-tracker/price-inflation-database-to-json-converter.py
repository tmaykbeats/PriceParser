import json
import os
import sqlite3


def extract_product_inflation():
    # Define file paths (assuming script and DB are in the same folder)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(script_dir, "product_inflation.db")
    json_path = os.path.join(script_dir, "product_inflation-db.json")

    # Connect to the SQLite database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # SQL query to join tables and extract required fields
    query = """
    SELECT
        ps.date,
        ps.variant,
        pt.name AS product_type_name,
        s.name AS store_name,
        s.country AS store_country,
        ps.price_per_unit_string
    FROM PriceSample ps
    JOIN ProductType pt ON ps.product_type_id = pt.product_type_id
    JOIN Store s ON ps.store_id = s.store_id

    """
    ##Extract only specified pruduct type (bread) and variant (cheapest)
    ##WHERE ps.variant = 'cheapest' AND ps.product_type_id = 1

    # Execute the query and fetch results
    cursor.execute(query)
    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    data = [dict(zip(columns, row)) for row in rows]

    # Save data to JSON
    with open(json_path, "w", encoding="utf-8") as json_file:
        json.dump(data, json_file, indent=2, ensure_ascii=False)

    # Cleanup
    conn.close()
    print(f"Exported {len(data)} records to {json_path}")


if __name__ == "__main__":
    extract_product_inflation()
