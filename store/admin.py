from django.contrib import admin

from .models import (
    Category,
    ContactMessage,
    Coupon,
    Order,
    OrderItem,
    Product,
    Review,
    SiteSettings,
    Subscriber,
    Variant,
)


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    fields = ("store_name", "tagline", "free_shipping_threshold", "welcome_coupon", "whatsapp_number")

    def has_add_permission(self, request):
        # Only one row ever exists.
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        # Skip the list page and go straight to the single settings row.
        from django.shortcuts import redirect
        from django.urls import reverse

        obj = SiteSettings.load()
        return redirect(reverse("admin:store_sitesettings_change", args=[obj.pk]))


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "position")
    list_editable = ("position",)
    prepopulated_fields = {"slug": ("name",)}


class VariantInline(admin.TabularInline):
    model = Variant
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "gender", "is_bestseller", "is_new", "is_active", "total_stock")
    list_filter = ("category", "gender", "is_bestseller", "is_new", "is_active")
    list_editable = ("is_bestseller", "is_new", "is_active")
    search_fields = ("name", "top_notes", "heart_notes", "base_notes")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [VariantInline]
    fieldsets = (
        (None, {"fields": ("name", "slug", "category", "tagline", "description", "is_active")}),
        ("Scent", {"fields": ("top_notes", "heart_notes", "base_notes", "gender", "concentration")}),
        ("Look", {"fields": ("image", "color", "bottle_shape")}),
        ("Merchandising", {"fields": ("is_bestseller", "is_new", "created")}),
    )

    @admin.display(description="Stock")
    def total_stock(self, obj):
        return sum(v.stock for v in obj.variants.all())


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("variant", "product_name", "size_ml", "unit_price", "quantity")
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("number", "full_name", "status", "payment_method", "total", "created")
    list_filter = ("status", "payment_method", "created")
    search_fields = ("number", "full_name", "email", "phone")
    readonly_fields = ("number", "subtotal", "discount", "shipping", "total", "coupon_code", "created", "updated")
    inlines = [OrderItemInline]
    actions = ["mark_paid", "mark_shipped", "mark_delivered"]

    @admin.action(description="Mark selected orders as paid")
    def mark_paid(self, request, queryset):
        queryset.update(status=Order.Status.PAID)

    @admin.action(description="Mark selected orders as shipped")
    def mark_shipped(self, request, queryset):
        queryset.update(status=Order.Status.SHIPPED)

    @admin.action(description="Mark selected orders as delivered")
    def mark_delivered(self, request, queryset):
        queryset.update(status=Order.Status.DELIVERED)


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ("code", "percent_off", "min_subtotal", "active", "expires_at")
    list_editable = ("active",)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("product", "rating", "name", "is_approved", "created")
    list_filter = ("is_approved", "rating")
    list_editable = ("is_approved",)


@admin.register(Subscriber)
class SubscriberAdmin(admin.ModelAdmin):
    list_display = ("email", "created")


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "created", "handled")
    list_filter = ("handled",)
    list_editable = ("handled",)