import json
import resend
from datetime import datetime

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
    return render(request, "store/index.html")


def cart(request):
    return render(request, "store/cart.html")


def order_form(request):
    return render(request, "store/order-form.html")


def thank_you(request):
    return render(request, "store/thank-you.html")


@csrf_exempt
def create_checkout_session(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method."}, status=405)

    try:
        if not request.body:
            return JsonResponse({"error": "Empty request body."}, status=400)

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON format."}, status=400)

        cart = data.get("cart", [])

        if not cart:
            return JsonResponse({"error": "Cart is empty."}, status=400)

        session = stripe.checkout.Session.create(
            mode="payment",
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": "gbp",
                        "product_data": {
                            "name": f"{item['name']} ({item['platform']})"
                        },
                        "unit_amount": int(float(item["price"]) * 10),
                    },
                    "quantity": int(item["quantity"]),
                }
                for item in cart
            ],
            success_url=f"{settings.BASE_URL}/order-form/?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{settings.BASE_URL}/cart/",
        )

        return JsonResponse({"url": session.url})

    except Exception as e:
        print("🔥 CHECKOUT ERROR:", repr(e))
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
            "itemsSummary": items_summary,
        })

    except Exception as e:
        print("🔥 VERIFY SESSION ERROR:", repr(e))
        return JsonResponse({"paid": False, "error": str(e)}, status=500)


@csrf_exempt
def submit_order_form(request):
    if request.method != "POST":
        return JsonResponse(
            {"success": False, "error": "Invalid request method."},
            status=405
        )

    try:
        if request.content_type and "application/json" in request.content_type:
            data = json.loads(request.body or "{}")
            full_name = data.get("full_name", "").strip()
            email = data.get("email", "").strip()
            product_summary = data.get("product_summary", "").strip()
            amount_paid = data.get("amount_paid", "").strip()
            payment_ref = data.get("payment_ref", "").strip()
            notes = data.get("notes", "").strip()
        else:
            full_name = request.POST.get("full_name", "").strip()
            email = request.POST.get("email", "").strip()
            product_summary = request.POST.get("product_summary", "").strip()
            amount_paid = request.POST.get("amount_paid", "").strip()
            payment_ref = request.POST.get("payment_ref", "").strip()
            notes = request.POST.get("notes", "").strip()

        if not full_name or not email or not notes:
            return JsonResponse(
                {"success": False, "error": "Full name, email, and notes are required."},
                status=400
            )

        order_data = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "full_name": full_name,
            "email": email,
            "product_summary": product_summary,
            "amount_paid": amount_paid,
            "payment_ref": payment_ref,
            "notes": notes,
        }

        try:
            with open(settings.ORDER_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(order_data) + "\n")
            print("✅ Order saved to file")
        except Exception as e:
            print("❌ Could not save order to file:", str(e))

        if settings.RESEND_API_KEY:
            resend.api_key = settings.RESEND_API_KEY

            html_content = f"""
            <h2>New KeyNest Order Received</h2>
            <p><strong>Date:</strong> {order_data['date']}</p>
            <p><strong>Customer Name:</strong> {full_name}</p>
            <p><strong>Customer Email:</strong> {email}</p>
            <p><strong>Purchased Service:</strong><br>{product_summary}</p>
            <p><strong>Amount Paid:</strong> £{amount_paid}</p>
            <p><strong>Stripe Session ID:</strong> {payment_ref}</p>
            <p><strong>Submitted Code / Notes:</strong><br>{notes}</p>
            """

            try:
                response = resend.Emails.send({
                    "from": settings.DEFAULT_FROM_EMAIL,
                    "to": [settings.ORDER_NOTIFICATION_EMAIL],
                    "subject": "New KeyNest Order Submission",
                    "html": html_content,
                })
                print("✅ Resend email sent successfully:", response)
            except Exception as e:
                print("❌ Resend email failed:", str(e))
        else:
            print("⚠️ RESEND_API_KEY is not set, skipping email send")

        return JsonResponse(
            {"success": True, "message": "Order submitted successfully."}
        )

    except Exception as e:
        print("🔥 SUBMIT ORDER FORM ERROR:", repr(e))
        return JsonResponse(
            {"success": False, "error": repr(e)},
            status=500
        )