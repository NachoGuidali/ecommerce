# store/views.py

from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_http_methods

import mercadopago

from .models import (
    Categoria,
    Producto,
    Pedido,
    ItemPedido,
    # 👇 necesarios para leer stock por variante (talle+color)
    TalleProducto,
    ColorStock,
)
from store.services.shipping import AndreaniClient, ShippingError

# Inicializa Mercado Pago con tu token
mp = mercadopago.SDK(settings.MP_ACCESS_TOKEN)


@require_http_methods(["GET"])
def home(request):
    """Página de inicio con sliders y destacados."""
    banners = [
        '/static/images/banner1.jpg',
        '/static/images/banner2.jpg',
        '/static/images/banner3.jpg',
    ]
    categorias = Categoria.objects.all()
    destacados = (
        Producto.objects
        .filter(destacado=True, talles__colores__stock__gt=0)
        .distinct()[:8]
    )
    return render(request, 'store/index.html', {
        'banners': banners,
        'categorias': categorias,
        'productos': destacados,
    })


@require_http_methods(["GET"])
def categories(request):
    """Listado de categorías."""
    cats = Categoria.objects.all()
    return render(request, 'store/categories.html', {'categorias': cats})


@require_http_methods(["GET"])
def product_list(request):
    """Listado de todos los productos con stock > 0."""
    productos = (
        Producto.objects
        .filter(talles__colores__stock__gt=0)
        .distinct()
    )
    categorias = Categoria.objects.all()
    return render(request, 'store/products.html', {
        'productos': productos,
        'categorias': categorias,
    })


@require_http_methods(["GET"])
def product_detail(request, pk):
    """Detalle de producto, filtrando talles/colores con stock."""
    producto = get_object_or_404(Producto, pk=pk)
    talles = []
    for t in producto.talles.all():
        colors = t.colores.filter(stock__gt=0)
        if colors.exists():
            talles.append((t.talle, colors))
    return render(request, 'store/product_detail.html', {
        'producto': producto,
        'talles': talles,
    })


# ----------------- helper de stock -----------------
def _variant_stock(pid, talle, color) -> int:
    """
    Devuelve el stock disponible para la combinación (producto, talle, color).
    Si no existe, retorna 0.
    """
    try:
        tp = TalleProducto.objects.get(producto_id=int(pid), talle=talle)
    except TalleProducto.DoesNotExist:
        return 0
    cs = ColorStock.objects.filter(
        talle_producto=tp,
        color__iexact=color  # tolerante a mayúsc/minúsc
    ).first()
    return cs.stock if cs else 0
# ---------------------------------------------------


@require_http_methods(["POST"])
def add_to_cart(request, pk):
    """Añade un producto variante al carrito de sesión, respetando stock."""
    try:
        quantity = int(request.POST.get('quantity', '1'))
        if quantity < 1:
            raise ValueError
    except ValueError:
        messages.error(request, "Cantidad inválida.")
        return redirect('store:product_detail', pk=pk)

    talle = request.POST.get('talle')
    color = request.POST.get('color')
    if not (talle and color):
        messages.error(request, "Debes seleccionar talle y color.")
        return redirect('store:product_detail', pk=pk)

    key = f"{pk}:{talle}:{color}"
    cart = request.session.get('cart', {})
    en_carrito = cart.get(key, 0)

    # 👉 tope por stock real
    stock = _variant_stock(pk, talle, color)
    if stock <= 0:
        messages.warning(request, "Sin stock para esa combinación.")
        return redirect('store:cart')

    nuevo_total = en_carrito + quantity
    if nuevo_total > stock:
        nuevo_total = stock

    agregado = nuevo_total - en_carrito
    if agregado <= 0:
        messages.warning(request, f"Stock máximo alcanzado ({stock}).")
        return redirect('store:cart')

    cart[key] = nuevo_total
    request.session['cart'] = cart

    if agregado < quantity:
        messages.info(request, f"Se agregaron {agregado} (limitado por stock: {stock}).")
    else:
        messages.success(request, f"Se agregaron {agregado} unidad(es) al carrito.")
    return redirect('store:cart')


@require_http_methods(["GET"])
def cart(request):
    """Muestra el contenido del carrito (ajustando si quedó por encima del stock)."""
    raw = request.session.get('cart', {})
    items = []
    total = Decimal('0.00')

    session_changed = False

    for key, qty in list(raw.items()):
        pid, talle, color = key.split(':')
        prod = get_object_or_404(Producto, pk=pid)

        # 👉 lee stock y corrige inconsistencias
        max_stock = _variant_stock(pid, talle, color)
        if max_stock <= 0:
            del raw[key]
            session_changed = True
            continue
        if qty > max_stock:
            qty = max_stock
            raw[key] = qty
            session_changed = True

        subtotal = prod.precio * qty
        items.append({
            'key': key,
            'producto': prod,
            'talle': talle,
            'color': color,
            'cantidad': qty,
            'subtotal': subtotal,
            # (opcional para el template si querés deshabilitar el "+")
            'max': max_stock,
        })
        total += subtotal

    if session_changed:
        request.session['cart'] = raw

    return render(request, 'store/cart.html', {
        'items': items,
        'total': total,
        'cart_count': sum(i['cantidad'] for i in items),
    })


@require_http_methods(["POST"])
def remove_from_cart(request, key):
    """Elimina una línea entera del carrito."""
    cart = request.session.get('cart', {})
    if key in cart:
        del cart[key]
        request.session['cart'] = cart
        messages.success(request, "Producto eliminado del carrito.")
    else:
        messages.error(request, "El producto no estaba en el carrito.")
    return redirect('store:cart')


@require_http_methods(["POST"])
def increment_cart_item(request, key):
    """Aumenta en 1 la cantidad de un item del carrito, sin superar el stock."""
    cart = request.session.get('cart', {})
    if key in cart:
        pid, talle, color = key.split(':')
        stock = _variant_stock(pid, talle, color)
        if cart[key] >= stock:
            messages.warning(request, "No hay más stock para esa combinación.")
        else:
            cart[key] += 1
            request.session['cart'] = cart
            messages.success(request, "Se incrementó la cantidad en 1.")
    else:
        messages.error(request, "El producto no existe en el carrito.")
    return redirect('store:cart')


@require_http_methods(["POST"])
def decrement_cart_item(request, key):
    """Disminuye en 1 la cantidad; si llega a 0, elimina el item."""
    cart = request.session.get('cart', {})
    if key in cart:
        if cart[key] > 1:
            cart[key] -= 1
            messages.success(request, "Se decrementó la cantidad en 1.")
        else:
            del cart[key]
            messages.success(request, "Producto eliminado del carrito.")
        request.session['cart'] = cart
    else:
        messages.error(request, "El producto no existe en el carrito.")
    return redirect('store:cart')


@require_http_methods(["GET", "POST"])
def checkout(request):
    """
    Checkout sin login:
     - GET: muestra items + subtotal, calcula envío (Andreani)
     - POST: crea Pedido + ItemPedido, limpia carrito y redirige
    """
    raw_cart = request.session.get('cart', {})
    items = []
    subtotal = Decimal('0.00')

    # 1) Prepara items y subtotal
    for key, qty in raw_cart.items():
        pid, talle, color = key.split(':')
        prod = get_object_or_404(Producto, pk=pid)
        item_sub = prod.precio * qty
        items.append({
            'producto': prod,
            'talle': talle,
            'color': color,
            'qty': qty,
            'subtotal': item_sub,
        })
        subtotal += item_sub

    # 2) Inicializa siempre shipping_cost
    shipping_cost = Decimal('0.00')

    # 3) GET → intento de cálculo de envío
    if request.method == "GET":
        try:
            sc = AndreaniClient().calculate_shipping(
                provincia=request.GET.get('provincia', ''),
                localidad=request.GET.get('localidad', ''),
                calle=request.GET.get('calle', ''),
                numero=request.GET.get('numero', ''),
            )
            shipping_cost = sc or Decimal('0.00')
        except ShippingError:
            messages.warning(
                request,
                "No se pudo calcular envío automáticamente; se ajustará tras llenar la dirección."
            )
            shipping_cost = Decimal('0.00')

    total = subtotal + shipping_cost

    # 4) POST → crea el pedido
    if request.method == "POST":
        buyer_name   = request.POST.get('nombre')
        buyer_dni    = request.POST.get('dni')
        provincia    = request.POST.get('provincia')
        localidad    = request.POST.get('localidad')
        calle        = request.POST.get('calle')
        numero       = request.POST.get('numero')
        entre_calles = request.POST.get('entre_calles', '')
        telefono     = request.POST.get('telefono')
        metodo_pago  = request.POST.get('metodo_pago')

        try:
            sc = AndreaniClient().calculate_shipping(
                provincia=provincia,
                localidad=localidad,
                calle=calle,
                numero=numero,
            )
            shipping_cost = sc or Decimal('0.00')
        except ShippingError:
            shipping_cost = Decimal('0.00')

        pedido = Pedido.objects.create(
            buyer_name=buyer_name,
            buyer_dni=buyer_dni,
            provincia=provincia,
            localidad=localidad,
            calle=calle,
            numero=numero,
            entre_calles=entre_calles,
            telefono=telefono,
            payment_method=metodo_pago,
            shipping_cost=shipping_cost,
            total=subtotal + shipping_cost,
        )

        for it in items:
            ItemPedido.objects.create(
                pedido=pedido,
                producto=it['producto'],
                talle=it['talle'],
                color=it['color'],
                cantidad=it['qty'],
                precio_unitario=it['producto'].precio,
            )

        request.session['cart'] = {}
        return redirect('store:order_detail', pk=pedido.id)

    # 5) Render final
    return render(request, 'store/checkout.html', {
        'items': items,
        'subtotal': subtotal,
        'shipping_cost': shipping_cost,
        'total': total,
    })


@require_http_methods(["GET"])
def orders(request):
    """Listado de todos los pedidos."""
    qs = Pedido.objects.all().order_by('-fecha')
    return render(request, 'store/orders.html', {'pedidos': qs})


@require_http_methods(["GET"])
def order_detail(request, pk):
    """Detalle de un pedido."""
    pedido = get_object_or_404(Pedido, pk=pk)
    return render(request, 'store/order_detail.html', {'pedido': pedido})
def admin_orders(request):
    """
    Listado de pedidos para el empleado:
    - Filtros por estado (?estado=pendiente/realizado/rechazado)
    - Búsqueda por nombre/dni/tracking/localidad (?q=texto)
    """
    estado = request.GET.get("estado", "").strip()
    q = request.GET.get("q", "").strip()

    pedidos = Pedido.objects.all().order_by("-fecha")

    if estado in {"pendiente", "realizado", "rechazado"}:
        pedidos = pedidos.filter(estado=estado)

    if q:
        pedidos = pedidos.filter(
            Q(buyer_name__icontains=q)
            | Q(buyer_dni__icontains=q)
            | Q(tracking_number__icontains=q)
            | Q(localidad__icontains=q)
        )

    ctx = {
        "pedidos": pedidos,
        "f_estado": estado,
        "f_q": q,
    }
    return render(request, "store/admin_orders.html", ctx)


@require_http_methods(["GET", "POST"])
def admin_order_detail(request, pk: int):
    """
    Detalle de un pedido + edición de estado y tracking.
    Reglas:
    - Para marcar como 'realizado' es obligatorio 'tracking_number'.
    - Al pasar de NO-realizado -> 'realizado' se descuenta stock (idempotente por diseño).
    - Se registran logs por cada cambio de estado / tracking.
    """
    pedido = get_object_or_404(Pedido, pk=pk)

    if request.method == "POST":
        nuevo_estado = request.POST.get("estado", pedido.estado)
        nuevo_tracking = request.POST.get("tracking_number", "").strip()

        # Validación: si se marca como realizado, tracking obligatorio
        if nuevo_estado == "realizado" and not nuevo_tracking:
            messages.error(
                request,
                "Para marcar como 'Pago Realizado' debés informar el número de seguimiento."
            )
            return redirect("store:panel_order_detail", pk=pedido.id)

        estado_anterior = pedido.estado
        tracking_anterior = pedido.tracking_number

        # Persistir cambios
        pedido.estado = nuevo_estado
        pedido.tracking_number = nuevo_tracking if nuevo_tracking else None
        pedido.save(update_fields=["estado", "tracking_number"])

        # Logs
        if estado_anterior != pedido.estado:
            pedido.add_log(f"Estado cambiado: {estado_anterior} → {pedido.estado}")

        if tracking_anterior != pedido.tracking_number:
            pedido.add_log(
                f"Tracking actualizado: {tracking_anterior} → {pedido.tracking_number}"
            )

        # Si pasa a 'realizado' (y antes no lo estaba), descuenta stock
        if estado_anterior != "realizado" and pedido.estado == "realizado":
            pedido.descontar_stock_si_realizado()
            pedido.add_log("Stock descontado por estado 'realizado'")

        messages.success(request, "Pedido actualizado correctamente.")
        return redirect("store:panel_order_detail", pk=pedido.id)

    # GET
    items = pedido.items.select_related("producto").all()
    logs = pedido.logs.all()

    return render(
        request,
        "store/panel_order_detail.html",
        {"pedido": pedido, "items": items, "logs": logs},
    )