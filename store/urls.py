from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("cart/", views.cart, name="cart"),
    path("order-form/", views.order_form, name="order_form"),
    path("thank-you/", views.thank_you, name="thank_you"),

    path("create-checkout-session/", views.create_checkout_session, name="create_checkout_session"),
    path("verify-session/", views.verify_session, name="verify_session"),
    path("submit-order-form/", views.submit_order_form, name="submit_order_form"),
]