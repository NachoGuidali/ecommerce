# store/urls.py

from django.urls import path
from . import views

app_name = 'store'

urlpatterns = [
    path('', views.home, name='home'),
    path('categorias/', views.categories, name='categories'),
    path('products/', views.product_list, name='products'),
    path('product/<int:pk>/', views.product_detail, name='product_detail'),

    # Carrito
    path('cart/', views.cart, name='cart'),
    path('cart/add/<int:pk>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<str:key>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/increment/<str:key>/', views.increment_cart_item, name='increment_cart_item'),
    path('cart/decrement/<str:key>/', views.decrement_cart_item, name='decrement_cart_item'),

    # Checkout
    path('checkout/', views.checkout, name='checkout'),

    # Órdenes
    path('orders/', views.orders, name='orders'),
    path('order/<int:pk>/', views.order_detail, name='order_detail'),

    # ... tus rutas existentes ...
    path('panel/orders/', views.admin_orders, name='admin_orders'),
    path('panel/orders/<int:pk>/', views.admin_order_detail, name='admin_order_detail'),
]


