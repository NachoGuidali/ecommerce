#!/usr/bin/env python3
import os

dirs = [
    "config",
    "store",
    "store/templates/store",
    "static/css",
    "static/js",
    "static/images",
]
files = [
    "manage.py",
    "requirements.txt",
    "config/__init__.py",
    "config/settings.py",
    "config/urls.py",
    "config/wsgi.py",
    "store/__init__.py",
    "store/admin.py",
    "store/apps.py",
    "store/models.py",
    "store/views.py",
    "store/urls.py",
    "store/templates/store/base.html",
    "store/templates/store/index.html",
    "store/templates/store/categories.html",
    "store/templates/store/products.html",
    "store/templates/store/product_detail.html",
    "store/templates/store/cart.html",
    "store/templates/store/checkout.html",
    "store/templates/store/orders.html",
    "store/templates/store/order_detail.html",
    "static/css/tailwind.css",
    "static/js/swiper-bundle.min.js",
]

for d in dirs:
    os.makedirs(d, exist_ok=True)
for f in files:
    open(f, "a").close()

print("¡Scaffold generado con éxito!")
