# KeyNest Django Version

This is your game key store converted to Django.

## What is included
- Homepage with product cards
- Add to cart using localStorage
- Cart page
- Checkout page
- Stripe Checkout session creation in Django
- Payment verification before the order form is shown
- Order form submission endpoint
- Submitted order details saved into `order_submissions.jsonl`

## Project structure
- `keynest_project/` = Django project settings
- `store/` = app containing views, URLs, templates, and static files

## Setup
1. Create a virtual environment
2. Install requirements
3. Copy `.env.example` to `.env`
4. Add your Stripe keys to `.env`
5. Run migrations
6. Start the server

## Commands
```bash
python -m venv venv
```

### Windows
```bash
venv\Scripts\activate
```

### macOS/Linux
```bash
source venv/bin/activate
```

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Open:
```bash
http://127.0.0.1:8000/
```

## Important note
For a real live store, you should later add:
- Stripe webhook handling
- Email sending or database order storage
- Proper CSRF handling on AJAX endpoints
- Real product storage in the database
