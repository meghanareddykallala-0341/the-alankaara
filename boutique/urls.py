from django.urls import path
from . import views, auth_views


urlpatterns = [
    path("", views.home, name="home"),

    path("collections/", views.all_collections, name="all_collections"),
    path("collections/anarkalis/", views.anarkalis, name="anarkalis"),
    path("collections/<slug:category>/", views.collection, name="collection"),

    path("product/<int:product_id>/", views.product_detail, name="product_detail"),

    path("cart/", views.cart, name="cart"),
    path("cart/add/<int:product_id>/", views.add_to_cart, name="add_to_cart"),
    path("cart/update/<int:product_id>/", views.update_cart, name="update_cart"),
    path("cart/remove/<int:product_id>/", views.remove_from_cart, name="remove_from_cart"),

    path("checkout/", views.checkout, name="checkout"),
    path("payment/", views.payment, name="payment"),

    path(
        "order-confirmation/<int:order_id>/",
        views.order_confirmation,
        name="order_confirmation",
    ),
    path("my-orders/", views.my_orders, name="my_orders"),

    path("style-studio/", views.style_studio, name="style_studio"),

    path("register/", auth_views.register_view, name="register"),
    path("login/", auth_views.login_view, name="login"),
    path("logout/", auth_views.logout_view, name="logout"),
]
