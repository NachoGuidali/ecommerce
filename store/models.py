
# store/models.py
from __future__ import annotations

from decimal import Decimal
from typing import Optional

from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Categoria(models.Model):
    """Categoría de productos."""
    nombre = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    imagen = models.ImageField(upload_to='categorias/', blank=True, null=True)

    def __str__(self) -> str:
        return self.nombre


class Producto(models.Model):
    """Un producto vendible."""
    categoria = models.ForeignKey(Categoria, related_name='productos', on_delete=models.CASCADE)
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField()
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    destacado = models.BooleanField(default=False)
    GENEROS = [('hombre', 'Hombre'), ('mujer', 'Mujer'), ('ambos', 'Ambos')]
    genero = models.CharField(max_length=10, choices=GENEROS, default='ambos')
    imagen = models.ImageField(upload_to='productos/', blank=True, null=True)

    def __str__(self) -> str:
        return self.nombre

    @property
    def stock_total(self) -> int:
        """Suma el stock de todos los talles y colores."""
        total = 0
        for talle in self.talles.all():
            total += sum(color.stock for color in talle.colores.all())
        return total


class ImagenProducto(models.Model):
    """Galería de imágenes por producto (máx. 5)."""
    producto = models.ForeignKey(Producto, related_name='imagenes', on_delete=models.CASCADE)
    imagen = models.ImageField(upload_to='productos/galeria/')
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['orden']

    def __str__(self) -> str:
        return f"{self.producto.nombre} – Imagen {self.orden}"


class TalleProducto(models.Model):
    """Talles disponibles por producto."""
    producto = models.ForeignKey(Producto, related_name='talles', on_delete=models.CASCADE)
    talle = models.CharField(max_length=10)

    class Meta:
        unique_together = [('producto', 'talle')]

    def __str__(self) -> str:
        return f"{self.producto.nombre} – {self.talle}"

    @property
    def stock_total(self) -> int:
        return sum(color.stock for color in self.colores.all())


class ColorStock(models.Model):
    """Stock por combinación (talle, color)."""
    talle_producto = models.ForeignKey(TalleProducto, related_name='colores', on_delete=models.CASCADE)
    color = models.CharField(max_length=50)
    stock = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = [('talle_producto', 'color')]

    def __str__(self) -> str:
        return f"{self.color}: {self.stock}"


# ---------------- Pedidos ----------------

ESTADOS = [
    ('pendiente', 'Pendiente'),
    ('realizado', 'Pago Realizado'),
    ('rechazado', 'Rechazado'),
]

METODOS_PAGO = [
    ('mp', 'Mercado Pago'),
    ('transferencia', 'Transferencia'),
]


class Pedido(models.Model):
    """
    Pedido generado en el checkout (sin login).
    - Estado inicial: 'pendiente'
    - Cuando pasa a 'realizado' debe tener tracking_number
    """
    # Datos de compra/envío (usados por tu views.py actual)
    buyer_name = models.CharField(max_length=150)
    buyer_dni = models.CharField(max_length=30)
    provincia = models.CharField(max_length=100)
    localidad = models.CharField(max_length=100)
    calle = models.CharField(max_length=120)
    numero = models.CharField(max_length=20)
    entre_calles = models.CharField(max_length=200, blank=True)
    telefono = models.CharField(max_length=50)

    payment_method = models.CharField(max_length=20, choices=METODOS_PAGO)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total = models.DecimalField(max_digits=10, decimal_places=2)
    fecha = models.DateTimeField(auto_now_add=True)

    # Gestión
    estado = models.CharField(max_length=12, choices=ESTADOS, default='pendiente')
    tracking_number = models.CharField(max_length=100, null=True, blank=True)

    # (Opcional) Si más adelante querés asociar a un usuario staff que lo gestionó
    #managed_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self) -> str:
        return f"Pedido #{self.id} - {self.buyer_name} - {self.get_estado_display()}"

    def add_log(self, action: str, note: str = "") -> None:
        """Crea una entrada en el log del pedido."""
        OrderLog.objects.create(pedido=self, action=action, note=note)

    def descontar_stock_si_realizado(self) -> None:
        """
        Descuenta stock de cada ItemPedido si el pedido pasa a 'realizado'.
        No hace nada si ya estaba realizado (idempotente a nivel de negocio si lo controlás desde la vista).
        """
        for it in self.items.all():
            try:
                tp = TalleProducto.objects.get(producto=it.producto, talle=it.talle)
                cs = ColorStock.objects.filter(talle_producto=tp, color__iexact=it.color).first()
                if cs:
                    nuevo = cs.stock - it.cantidad
                    cs.stock = nuevo if nuevo > 0 else 0
                    cs.save(update_fields=['stock'])
            except TalleProducto.DoesNotExist:
                continue


class ItemPedido(models.Model):
    """Ítems de un Pedido."""
    pedido = models.ForeignKey(Pedido, related_name='items', on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    talle = models.CharField(max_length=10)
    color = models.CharField(max_length=50)
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self) -> str:
        return f"{self.producto.nombre} x{self.cantidad}"


class OrderLog(models.Model):
    """Registro de cambios de un Pedido."""
    pedido = models.ForeignKey(Pedido, related_name='logs', on_delete=models.CASCADE)
    action = models.CharField(max_length=100)
    note = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self) -> str:
        return f"[{self.timestamp:%Y-%m-%d %H:%M}] {self.action}"









#---------------------------------------------------------------------------------------------------
# # store/models.py

# from decimal import Decimal
# from django.db import models
# from django.contrib.auth import get_user_model

# User = get_user_model()


# class Categoria(models.Model):
#     """
#     Categoría de productos.
#     """
#     nombre = models.CharField(max_length=100)
#     slug = models.SlugField(unique=True)
#     imagen = models.ImageField(upload_to='categorias/', blank=True, null=True)

#     def __str__(self) -> str:
#         return self.nombre


# class Producto(models.Model):
#     """
#     Un producto vendible.
#     """
#     categoria = models.ForeignKey(
#         Categoria, related_name='productos', on_delete=models.CASCADE
#     )
#     nombre = models.CharField(max_length=150)
#     descripcion = models.TextField()
#     precio = models.DecimalField(max_digits=10, decimal_places=2)
#     destacado = models.BooleanField(default=False)
#     GENEROS = [
#         ('hombre', 'Hombre'),
#         ('mujer',  'Mujer'),
#         ('ambos',  'Ambos'),
#     ]
#     genero = models.CharField(
#         max_length=10,
#         choices=GENEROS,
#         default='ambos',
#         help_text="Define si el producto es de hombre, mujer o ambos."
#     )
#     imagen = models.ImageField(upload_to='productos/', blank=True, null=True)

#     def __str__(self) -> str:
#         return self.nombre

#     @property
#     def stock_total(self) -> int:
#         """
#         Retorna el stock total sumando todos los colores de todos los talles.
#         """
#         total = 0
#         for talle in self.talles.all():
#             total += sum(color.stock for color in talle.colores.all())
#         return total


# class ImagenProducto(models.Model):
#     """
#     Galería de imágenes para cada producto.
#     Hasta 5 imágenes por producto.
#     """
#     producto = models.ForeignKey(
#         Producto, related_name='imagenes', on_delete=models.CASCADE
#     )
#     imagen = models.ImageField(upload_to='productos/galeria/')
#     orden = models.PositiveSmallIntegerField(default=0)

#     class Meta:
#         ordering = ['orden']

#     def __str__(self) -> str:
#         return f"{self.producto.nombre} – Imagen {self.orden}"


# class TalleProducto(models.Model):
#     """
#     El stock de un producto para cada talle.
#     """
#     producto = models.ForeignKey(
#         Producto, related_name='talles', on_delete=models.CASCADE
#     )
#     talle = models.CharField(max_length=10)

#     class Meta:
#         unique_together = [('producto', 'talle')]

#     def __str__(self) -> str:
#         return f"{self.producto.nombre} – {self.talle}"

#     @property
#     def stock_total(self) -> int:
#         """
#         Retorna el stock total para este talle sumando todos los colores.
#         """
#         return sum(color.stock for color in self.colores.all())


# class ColorStock(models.Model):
#     """
#     Para cada talle, los distintos colores y su stock.
#     """
#     talle_producto = models.ForeignKey(
#         TalleProducto, related_name='colores', on_delete=models.CASCADE
#     )
#     color = models.CharField(max_length=50)
#     stock = models.PositiveIntegerField(default=0)

#     class Meta:
#         unique_together = [('talle_producto', 'color')]

#     def __str__(self) -> str:
#         return f"{self.color}: {self.stock}"


# class Pedido(models.Model):
#     """
#     Una orden de compra, con datos del comprador, envío, estado y tracking.
#     """
#     # Estados del pedido
#     PENDING = 'PENDING'
#     PAID = 'PAID'
#     REJECTED = 'REJECTED'
#     SHIPPED = 'SHIPPED'
#     ESTADOS = [
#         (PENDING, 'Pendiente'),
#         (PAID, 'Pago realizado'),
#         (REJECTED, 'Rechazado'),
#         (SHIPPED, 'Enviado'),
#     ]

#     # Métodos de pago
#     MP = 'mp'
#     TRANSFER = 'transferencia'
#     PAYMENT_METHODS = [
#         (MP, 'Mercado Pago'),
#         (TRANSFER, 'Transferencia bancaria'),
#     ]

#     user = models.ForeignKey(
#         User,
#         on_delete=models.CASCADE,
#         null=True,
#         blank=True,
#         help_text="Usuario que realizó el pedido (opcional; checkout sin login)."
#     )
#     fecha = models.DateTimeField(auto_now_add=True)
#     buyer_name = models.CharField(
#         max_length=150,
#         default='',
#         help_text="Nombre completo del comprador"
#     )
#     buyer_dni = models.CharField(
#         max_length=50,
#         default='',
#         help_text="DNI del comprador"
#     )
#     provincia = models.CharField(
#         max_length=100,
#         default='',
#         help_text="Provincia de envío"
#     )
#     localidad = models.CharField(
#         max_length=100,
#         default='',
#         help_text="Localidad de envío"
#     )
#     calle = models.CharField(
#         max_length=150,
#         default='',
#         help_text="Calle de envío"
#     )
#     numero = models.CharField(
#         max_length=20,
#         default='',
#         help_text="Número de la dirección"
#     )
#     entre_calles = models.CharField(
#         max_length=150,
#         blank=True,
#         null=True,
#         default='',
#         help_text="Referencia entre calles (opcional)."
#     )
#     telefono = models.CharField(
#         max_length=50,
#         default='',
#         help_text="Teléfono de contacto"
#     )
#     payment_method = models.CharField(
#         max_length=20,
#         choices=PAYMENT_METHODS,
#         default=MP,
#         help_text="Método de pago seleccionado."
#     )
#     shipping_cost = models.DecimalField(
#         max_digits=10,
#         decimal_places=2,
#         default=Decimal('0.00'),
#         help_text="Costo de envío calculado."
#     )
#     total = models.DecimalField(
#         max_digits=10,
#         decimal_places=2,
#         help_text="Suma de subtotales más envío."
#     )
#     estado = models.CharField(
#         max_length=20,
#         choices=ESTADOS,
#         default=PENDING,
#         help_text="Estado actual del pedido."
#     )
#     tracking_number = models.CharField(
#         max_length=100,
#         blank=True,
#         null=True,
#         help_text="Número de seguimiento (cuando el pedido es enviado)."
#     )

#     def __str__(self) -> str:
#         return f"Pedido #{self.id} — {self.buyer_name} — {self.estado}"


# class ItemPedido(models.Model):
#     """
#     Artículos dentro de un Pedido.
#     """
#     pedido = models.ForeignKey(
#         Pedido, related_name='items', on_delete=models.CASCADE
#     )
#     producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
#     talle = models.CharField(max_length=10)
#     color = models.CharField(max_length=50)
#     cantidad = models.PositiveIntegerField(default=1)
#     precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)

#     def __str__(self) -> str:
#         return f"{self.producto.nombre} x{self.cantidad}"


# class OrderLog(models.Model):
#     """
#     Registro de cambios de estado o acciones sobre un Pedido.
#     """
#     pedido = models.ForeignKey(
#         Pedido, related_name='logs', on_delete=models.CASCADE
#     )
#     action = models.CharField(max_length=100)
#     timestamp = models.DateTimeField(auto_now_add=True)

#     def __str__(self) -> str:
#         return f"Pedido #{self.pedido.id}: {self.action} @ {self.timestamp}"
