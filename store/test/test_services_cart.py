# tests/test_services_cart.py

import pytest
from decimal import Decimal

from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory

from store.models import Product
from store.services.cart import Cart, CartError, CartItem


@pytest.fixture
def rf():
    """Django RequestFactory."""
    return RequestFactory()


@pytest.fixture
def session_request(rf):
    """
    Create a request instance with session middleware applied.
    """
    request = rf.get('/')
    SessionMiddleware().process_request(request)
    request.session.save()
    return request


@pytest.fixture
def product(db):
    """
    Create and return a sample product.
    """
    return Product.objects.create(
        nombre='Test Product',
        precio=Decimal('10.00'),
        stock=100
    )


@pytest.fixture
def cart(session_request):
    """
    Initialize and return a Cart instance.
    """
    return Cart(session_request)


def test_add_new_item(cart, product):
    cart.add(product.id, 2)
    items = cart.get_items()
    assert len(items) == 1
    item = items[0]
    assert isinstance(item, CartItem)
    assert item.product.id == product.id
    assert item.quantity == 2
    assert item.price == product.precio
    assert item.subtotal == product.precio * 2


def test_add_increment_quantity(cart, product):
    cart.add(product.id, 1)
    cart.add(product.id, 3)
    items = cart.get_items()
    assert items[0].quantity == 4


def test_remove_item(cart, product):
    cart.add(product.id, 1)
    cart.remove(product.id)
    assert cart.get_items() == []


def test_remove_nonexistent_raises(cart):
    with pytest.raises(CartError):
        cart.remove(999)


def test_clear_cart(cart, product):
    cart.add(product.id, 5)
    cart.clear()
    assert cart.get_items() == []
    assert cart.session['cart'] == {}


@pytest.mark.parametrize("quantity", [0, -1])
def test_add_invalid_quantity_raises(cart, product, quantity):
    with pytest.raises(CartError):
        cart.add(product.id, quantity)


def test_add_nonexistent_product_raises(cart):
    with pytest.raises(CartError):
        cart.add(999, 1)


def test_get_total_multiple_items(cart, product):
    # Create another product
    product2 = Product.objects.create(
        nombre='Another Product',
        precio=Decimal('5.50'),
        stock=50
    )
    cart.add(product.id, 2)   # 2 * 10.00 = 20.00
    cart.add(product2.id, 3)  # 3 * 5.50  = 16.50
    total = cart.get_total()
    assert total == Decimal('36.50')
