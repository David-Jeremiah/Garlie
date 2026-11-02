from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin

from .models import (
    Category,
    ContactMessage,
    Coupon,
    Order,
    Page,
    Profile,
    OrderItem,
    Product,
    Review,
    SiteSettings,
    Subscriber,
    Variant,
)


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ("Store", {"fields": ("store_name", "tagline", "logo", "favicon")}),
        ("Front page: photo and Whisper of Luxury box", {"fields": ("hero_image", "hero_title", "hero_text", "hero_button_text")}),
        ("Front page: perfume display", {"fields": ("display_title", "display_text")}),
        ("Banner and footer", {"fields": ("announcement_text", "footer_text", "free_shipping_threshold", "welcome_coupon")}),
        ("Contact and orders", {"fields": ("whatsapp_number", "phone", "email", "location", "delivery_text")}),
    )

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
    readonly_fields = ("number", "user", "subtotal", "discount", "shipping", "total", "coupon_code", "created", "updated")
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


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ("title", "slug")
    prepopulated_fields = {"slug": ("title",)}
    fields = ("title", "slug", "intro", "body", "image")


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False


admin.site.unregister(get_user_model())


@admin.register(get_user_model())
class CustomerUserAdmin(UserAdmin):
    inlines = [ProfileInline]
    list_display = ("username", "first_name", "email", "is_staff", "date_joined")
