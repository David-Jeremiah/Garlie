from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("shop/", views.shop, name="shop"),
    path("product/<slug:slug>/", views.product_detail, name="product"),
    path("product/<slug:slug>/review/", views.add_review, name="add_review"),
    path("bag/", views.cart_detail, name="cart"),
    path("bag/add/", views.cart_add, name="cart_add"),
    path("bag/update/", views.cart_update, name="cart_update"),
    path("bag/remove/", views.cart_remove, name="cart_remove"),
    path("bag/coupon/", views.cart_coupon, name="cart_coupon"),
    path("checkout/", views.checkout, name="checkout"),
    path("order/<str:number>/", views.order_success, name="order_success"),
    path("track/", views.track_order, name="track"),
    path("newsletter/", views.newsletter, name="newsletter"),
    path("contact/", views.contact, name="contact"),
    path("<slug:slug>/", views.page, name="page"),
]
