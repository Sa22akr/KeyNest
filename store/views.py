import json
import stripe
from django.conf import settings
from django.core.mail import send_mail
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

stripe.api_key = settings.STRIPE_SECRET_KEY

PRODUCT = {
    "name": "ChatGPT Plus - 1 Month Activation Service",
    "platform": "ChatGPT",
    "price": 10,
    "description": (
        "Independent activation support service for 1 month access. "
        "After payment, complete the order form and we will process your order manually."
    ),
}


def home(request):
    return render(request, 'store/index.html')

def cart(request):
    return render(request, 'store/cart.html')

def order_form(request):
    return render(request, 'store/order-form.html')

def thank_you(request):
    return render(request, 'store/thank-you.html')


@csrf_exempt
def create_checkout_session(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method."}, status=405)

    try:
        data = json.loads(request.body)
        cart = data.get("cart", [])

        if not cart:
            return JsonResponse({"error": "Cart is empty."}, status=400)

        session = stripe.checkout.Session.create(
            mode="payment",
            line_items=[
                {
                    "price_data": {
                        "currency": "gbp",
                        "product_data": {
                            "name": f"{item['name']} ({item['platform']})"
                        },
                        "unit_amount": int(float(item["price"]) * 100),
                    },
                    "quantity": item["quantity"],
                }
                for item in cart
            ],
            success_url=f"{settings.BASE_URL}/order-form/?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{settings.BASE_URL}/cart/",
        )

        return JsonResponse({"url": session.url})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def verify_session(request):
    session_id = request.GET.get("session_id")

    if not session_id:
        return JsonResponse({"paid": False, "error": "Missing session ID."}, status=400)

    try:
        session = stripe.checkout.Session.retrieve(
            session_id,
            expand=["line_items.data.price.product"]
        )

        paid = session.payment_status == "paid"
        items_summary = "\n".join(
            [f"{item.description} x {item.quantity}" for item in session.line_items.data]
        )

        return JsonResponse({
            "paid": paid,
            "sessionId": session.id,
            "amountTotal": f"{(session.amount_total or 0) / 100:.2f}",
            "itemsSummary": items_summary
        })

    except Exception as e:
        return JsonResponse({"paid": False, "error": str(e)}, status=500)


@csrf_exempt
def submit_order_form(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Invalid request method."}, status=405)

    try:
        data = json.loads(request.body)

        full_name = data.get("fullName", "")
        email = data.get("email", "")
        product_summary = data.get("productSummary", "")
        amount_paid = data.get("amountPaid", "")
        payment_ref = data.get("paymentRef", "")
        activation_method = data.get("activationMethod", "")
        account_email = data.get("accountEmail", "")
        notes = data.get("notes", "")

        subject = f"New Order: {full_name}"

        message = f"""
NEW ORDER RECEIVED

Customer Name: {full_name}
Customer Email: {email}

Product:
{product_summary}

Amount Paid: £{amount_paid}
Stripe Session ID: {payment_ref}

Preferred Activation Method:
{activation_method}

ChatGPT Account Email:
{account_email}

Additional Notes:
{notes}
"""

        send_mail(
            subject,
            message,
            settings.EMAIL_HOST_USER,
            [settings.ORDER_NOTIFICATION_EMAIL],
            fail_silently=False,
        )

        return JsonResponse({"success": True})

    except Exception as e:
        print("EMAIL ERROR:", e)
        return JsonResponse({"success": False, "error": str(e)}, status=500)