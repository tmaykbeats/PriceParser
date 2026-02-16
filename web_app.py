# /PriceParser/web_app.py

import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from peewee import fn

from models import Product
from services.history import get_price_history, plot_price_history

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/favicon.ico")
def favicon():
    return HTMLResponse(content="", status_code=204)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    # Берём последние цены по каждому товару (с самым новым timestamp)
    subquery = Product.select(
        Product.name, fn.MAX(Product.timestamp).alias("max_time")
    ).group_by(Product.name)

    query = (
        Product.select()
        .join(
            subquery,
            on=(
                (Product.name == subquery.c.name)
                & (Product.timestamp == subquery.c.max_time)
            ),
        )
        .order_by(Product.category, Product.name)
    )

    # Группируем по категориям
    categories = {}
    for product in query:
        categories.setdefault(product.category, []).append(product)

    return templates.TemplateResponse(
        "index.html", {"request": request, "categories": categories}
    )


@app.get("/history/{product_name}", response_class=HTMLResponse)
async def history(request: Request, product_name: str):
    history = get_price_history(product_name=product_name, days=7)
    if not history:
        raise HTTPException(status_code=404, detail="No history found")

    img_path = plot_price_history(history, product_name)
    return templates.TemplateResponse(
        "history.html",
        {
            "request": request,
            "product_name": product_name,
            "image_url": f"/static/{os.path.basename(img_path)}",
        },
    )


@app.get("/api/products")
def api_products(request: Request):
    category = request.query_params.get("category")
    sort_by = request.query_params.get("sort", "name")  # default: name

    query = Product.select()

    if category:
        query = query.where(Product.category.ilike(category))

    if sort_by == "price":
        query = query.order_by(Product.price)
    else:
        query = query.order_by(Product.name)

    products = query

    data = [
        {
            "name": p.name,
            "price": p.price,
            "category": p.category,
            "timestamp": p.timestamp.isoformat(),
        }
        for p in products
    ]
    return JSONResponse(content=data)


@app.get("/api/products/{name}")
def get_product_by_name(name: str):
    try:
        product = (
            Product.select()
            .where(Product.name == name)
            .order_by(Product.timestamp.desc())
            .get()
        )
        return {
            "name": product.name,
            "price": product.price,
            "category": product.category,
            "timestamp": product.timestamp.isoformat(),
        }
    except Product.DoesNotExist:
        raise HTTPException(status_code=404, detail="Product not found")


@app.get("/api/products")
def api_products(request: Request):
    category = request.query_params.get("category")

    query = Product.select()
    if category:
        query = query.where(Product.category == category)

    products = query.order_by(Product.name)

    data = [
        {
            "name": p.name,
            "price": p.price,
            "category": p.category,
            "timestamp": p.timestamp.isoformat(),
        }
        for p in products
    ]
    return JSONResponse(content=data)


@app.get("/products", response_class=HTMLResponse)
def products_page(request: Request):
    products = Product.select().order_by(Product.name)
    return templates.TemplateResponse(
        "products.html", {"request": request, "products": products}
    )
