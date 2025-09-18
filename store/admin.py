# store/admin.py
"""
Admin site configuration for the store application (alineado con el nuevo Pedido).
- Quita 'user' del list_display.
- Valida tracking_number cuando estado = 'realizado'.
- Registra logs y descuenta stock al pasar a 'realizado'.
"""
from __future__ import annotations

import logging
from django import forms
from django.contrib import admin

from .models import (
    Categoria,
    Producto,
    ImagenProducto,
    TalleProducto,
    ColorStock,
    Pedido,
    ItemPedido,
    OrderLog,
)

logger = logging.getLogger(__name__)


# ---------------- Inlines de catálogo ----------------
class ImagenProductoInline(admin.TabularInline):
    model = ImagenProducto
    extra = 1
    max_num = 5
    verbose_name = "Imagen de Galería"
    verbose_name_plural = "Imágenes de Galería"


class ColorInline(admin.TabularInline):
    model = ColorStock
    extra = 1
    verbose_name = "Color / Stock"
    verbose_name_plural = "Colores / Stock"


class TalleInline(admin.TabularInline):
    model = TalleProducto
    extra = 1
    verbose_name = "Talle"
    verbose_name_plural = "Talles"


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "categoria", "precio", "destacado", "genero", "stock_total")
    list_filter = ("categoria", "destacado", "genero")
    search_fields = ("nombre",)
    inlines = [ImagenProductoInline, TalleInline]

    def save_model(self, request, obj, form, change):
        action = "Updated" if change else "Created"
        logger.info("%s Producto(id=%s, nombre=%s)", action, obj.id, obj.nombre)
        super().save_model(request, obj, form, change)


@admin.register(TalleProducto)
class TalleProductoAdmin(admin.ModelAdmin):
    list_display = ("producto", "talle")
    inlines = [ColorInline]


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "slug")
    prepopulated_fields = {"slug": ("nombre",)}


# ---------------- Inlines de Pedido ----------------
class ItemPedidoInline(admin.TabularInline):
    model = ItemPedido
    extra = 0
    readonly_fields = ("producto", "talle", "color", "cantidad", "precio_unitario")
    can_delete = False
    verbose_name = "Artículo de Pedido"
    verbose_name_plural = "Artículos de Pedido"


class OrderLogInline(admin.TabularInline):
    model = OrderLog
    extra = 0
    readonly_fields = ("action", "note", "timestamp")
    can_delete = False
    verbose_name = "Registro de Pedido"
    verbose_name_plural = "Logs de Pedido"


# ---------------- Form de Pedido con validación ----------------
class PedidoForm(forms.ModelForm):
    class Meta:
        model = Pedido
        fields = "__all__"

    def clean(self):
        cleaned = super().clean()
        estado = cleaned.get("estado")
        tracking = cleaned.get("tracking_number")
        if estado == "realizado" and not tracking:
            raise forms.ValidationError(
                "Para marcar como 'Pago Realizado' debe informar el número de seguimiento."
            )
        return cleaned


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    form = PedidoForm

    list_display = (
        "id",
        "buyer_name",
        "fecha",
        "payment_method",
        "shipping_cost",
        "total",
        "estado",
        "tracking_number",
    )
    list_filter = ("estado", "payment_method", "fecha")
    search_fields = ("buyer_name", "buyer_dni", "tracking_number", "telefono", "localidad")
    readonly_fields = ("fecha",)
    inlines = [ItemPedidoInline, OrderLogInline]
    ordering = ("-fecha",)

    fieldsets = (
        (
            "Datos del Comprador y Envío",
            {
                "fields": (
                    "buyer_name",
                    "buyer_dni",
                    ("provincia", "localidad"),
                    ("calle", "numero"),
                    "entre_calles",
                    "telefono",
                )
            },
        ),
        (
            "Pago y Estado",
            {
                "fields": (
                    "payment_method",
                    "shipping_cost",
                    "total",
                    "estado",
                    "tracking_number",
                    "fecha",
                )
            },
        ),
    )

    def save_model(self, request, obj: Pedido, form, change):
        """
        - Valida en el form que 'realizado' tenga tracking_number.
        - Si cambia el estado, escribe un log.
        - Si pasa a 'realizado' por primera vez: descuenta stock y loguea.
        - Si cambia tracking_number, loguea el cambio.
        """
        estado_anterior = None
        tracking_anterior = None
        if change:
            prev = Pedido.objects.get(pk=obj.pk)
            estado_anterior = prev.estado
            tracking_anterior = prev.tracking_number

        super().save_model(request, obj, form, change)

        # Log de cambios de estado
        if change and estado_anterior != obj.estado:
            obj.add_log(f"Estado cambiado: {estado_anterior} → {obj.estado}")

        # Si pasa a 'realizado' (y antes no lo estaba), descuenta stock
        if (not change and obj.estado == "realizado") or (
            change and estado_anterior != "realizado" and obj.estado == "realizado"
        ):
            obj.descontar_stock_si_realizado()
            obj.add_log("Stock descontado por estado 'realizado'")

        # Log por cambio de tracking
        if change and tracking_anterior != obj.tracking_number:
            obj.add_log(f"Tracking actualizado: {tracking_anterior} → {obj.tracking_number}")


@admin.register(ItemPedido)
class ItemPedidoAdmin(admin.ModelAdmin):
    list_display = ("pedido", "producto", "talle", "color", "cantidad", "precio_unitario")
    list_filter = ("talle", "color")
    readonly_fields = ("pedido", "producto", "talle", "color", "cantidad", "precio_unitario")
    can_delete = False


@admin.register(OrderLog)
class OrderLogAdmin(admin.ModelAdmin):
    list_display = ("pedido", "action", "timestamp")
    readonly_fields = ("pedido", "action", "note", "timestamp")
    ordering = ("-timestamp",)
