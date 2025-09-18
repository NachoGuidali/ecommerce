# store/services/cart.py

"""
Module for managing the shopping cart stored in Django sessions.
"""

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List

from django.http import HttpRequest

from store.models import Product

logger = logging.getLogger(__name__)


class CartError(Exception):
    """Custom exception for cart operations."""
    pass


@dataclass
class CartItem:
    """
    Represents an item in the shopping cart.

    Attributes:
        product (Product): The product instance.
        quantity (int): The quantity of the product.
        price (Decimal): Unit price of the product.
        subtotal (Decimal): Total price for this item (quantity * price).
    """
    product: Product
    quantity: int
    price: Decimal
    subtotal: Decimal


class Cart:
    """
    Service class for handling shopping cart operations using Django sessions.

    Stores cart data in `request.session['cart']` as a dict of
    { product_id (str) : quantity (int) }.
    """

    SESSION_KEY = 'cart'

    def __init__(self, request: HttpRequest) -> None:
        """
        Initialize the Cart service.

        Args:
            request (HttpRequest): Django HTTP request with session.
        """
        self.request = request
        self.session = request.session
        cart = self.session.get(self.SESSION_KEY)
        if not isinstance(cart, dict):
            cart = {}
            self.session[self.SESSION_KEY] = cart
        self.cart: Dict[str, int] = cart
        logger.debug("Initialized cart with contents: %s", self.cart)

    def add(self, product_id: int, quantity: int) -> None:
        """
        Add a product to the cart or update its quantity.

        Args:
            product_id (int): ID of the product to add.
            quantity (int): Quantity to add.

        Raises:
            CartError: If quantity is not positive or product does not exist.
        """
        if quantity <= 0:
            logger.error("Invalid quantity %d for product %d", quantity, product_id)
            raise CartError("Quantity must be a positive integer")

        try:
            product = Product.objects.get(pk=product_id)
        except Product.DoesNotExist:
            logger.exception("Product with id %d does not exist", product_id)
            raise CartError(f"Product with id {product_id} does not exist")

        prod_key = str(product_id)
        original_qty = self.cart.get(prod_key, 0)
        self.cart[prod_key] = original_qty + quantity
        self._save()
        logger.info(
            "Added product %d (qty: %d) to cart. New qty: %d",
            product_id, quantity, self.cart[prod_key]
        )

    def remove(self, product_id: int) -> None:
        """
        Remove a product from the cart.

        Args:
            product_id (int): ID of the product to remove.

        Raises:
            CartError: If the product is not in the cart.
        """
        prod_key = str(product_id)
        if prod_key not in self.cart:
            logger.error("Attempted to remove product %d not in cart", product_id)
            raise CartError(f"Product with id {product_id} not in cart")

        del self.cart[prod_key]
        self._save()
        logger.info("Removed product %d from cart", product_id)

    def clear(self) -> None:
        """
        Clear the entire cart.
        """
        self.session[self.SESSION_KEY] = {}
        self.session.modified = True
        logger.info("Cleared the cart")

    def get_items(self) -> List[CartItem]:
        """
        Get list of items in the cart.

        Returns:
            List[CartItem]: List of cart items with product, quantity, price, and subtotal.
        """
        items: List[CartItem] = []
        for prod_key, qty in self.cart.items():
            try:
                product = Product.objects.get(pk=int(prod_key))
                price = product.precio
                subtotal = price * qty
                items.append(
                    CartItem(
                        product=product,
                        quantity=qty,
                        price=price,
                        subtotal=subtotal
                    )
                )
            except Product.DoesNotExist:
                logger.warning(
                    "Product with id %s in session cart not found in database",
                    prod_key
                )
                continue
        return items

    def get_total(self) -> Decimal:
        """
        Calculate the total cost of all items in the cart.

        Returns:
            Decimal: Total cost.
        """
        total = Decimal('0.00')
        for item in self.get_items():
            total += item.subtotal
        logger.debug("Cart total calculated: %s", total)
        return total

    def _save(self) -> None:
        """
        Mark the session as modified to ensure it is saved.
        """
        self.session[self.SESSION_KEY] = self.cart
        self.session.modified = True
