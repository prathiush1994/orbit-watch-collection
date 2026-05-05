# 🕐 Orbit Watch Collection

A full-featured e-commerce web application for a premium watch brand, built with **Django 6** and **Python 3.13**.

---

## 🚀 Features

- **User Authentication** — Email-based login, Google OAuth via django-allauth
- **Product Catalog** — Categories, brands, variants (color/size), product images
- **Shopping Cart** — Session-based cart with quantity management
- **Wishlist** — Save products for later
- **Checkout** — Address selection, multiple payment methods
- **Payments** — Razorpay integration (online) + Cash on Delivery
- **Wallet System** — Store credit, debit, referral rewards
- **Coupons & Referrals** — Discount codes, referral program
- **Offers** — Product-level and category-level discount offers
- **Order Management** — Order tracking, cancel, return (item-level and order-level)
- **Invoice** — Downloadable PDF invoice per order
- **Reviews** — Product reviews and ratings
- **Inventory** — Stock tracking with deduction on order
- **Admin Panel** — Custom admin dashboard
- **Dashboard** — Sales analytics

---

## 🗂️ Project Structure

```
ORBIT/
├── accounts/        # User auth, profiles, addresses, Google OAuth
├── adminpanel/      # Custom admin dashboard
├── brands/          # Watch brands
├── carts/           # Shopping cart logic
├── category/        # Product categories + context processor
├── dashboard/       # Sales analytics
├── inventory/       # Stock management
├── offers/          # Product/category offers, referral codes
├── orders/          # Checkout, payments, order management
│   └── views/
│       ├── checkout.py      # Checkout page
│       ├── place_order.py   # COD + Razorpay order creation
│       ├── payment.py       # Razorpay callback + success/fail pages
│       ├── helpers.py       # Shared utilities (totals, order builder)
│       ├── coupon.py        # Coupon apply/remove
│       ├── referral.py      # Referral apply/remove
│       ├── order_views.py   # My orders, order detail
│       ├── item_actions.py  # Cancel/return item
│       └── invoice.py       # PDF invoice download
├── reviews/         # Product reviews
├── store/           # Product listing and detail pages
├── wallet/          # Wallet balance, transactions
├── wishlist/        # Wishlist
├── orbit/           # Project settings and main URLs
├── templates/       # All HTML templates
├── static/          # CSS, JS, images
└── media/           # Uploaded product images
```

---

## ⚙️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django 6, Python 3.13 |
| Database | PostgreSQL |
| Payments | Razorpay |
| Auth | django-allauth (Email + Google OAuth) |
| Frontend | Bootstrap 4, HTML5, CSS3, JavaScript |
| Storage | Local media (Django MEDIA_ROOT) |
| Email | Gmail SMTP |

---

## 🛠️ Local Setup

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/orbit-watch.git
cd orbit-watch
```

### 2. Create virtual environment

```bash
python -m venv env
source env/bin/activate        # Mac/Linux
env\Scripts\activate           # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Create `.env` file

Create a `.env` file in the root folder:

```env
SECRET_KEY=your_django_secret_key

DEBUG=True

DB_NAME=your_db_name
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=localhost
DB_PORT=5432

EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_app_password

GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

RAZORPAY_KEY_ID=rzp_test_xxxxxxxxxxxx
RAZORPAY_KEY_SECRET=xxxxxxxxxxxxxxxxxxxx
RAZORPAY_WEBHOOK_SECRET=your_webhook_secret
```

### 5. Run migrations

```bash
python manage.py migrate
```

### 6. Create superuser

```bash
python manage.py createsuperuser
```

### 7. Run the development server

```bash
python manage.py runserver
```

Visit: `http://localhost:8000`

---

## 💳 Razorpay Payment Flow

```
1. User selects Razorpay at checkout
2. Django creates a Razorpay order with user/address/discount info stored in order notes
3. Razorpay payment page opens
4. User completes payment
5. Razorpay POSTs to /orders/razorpay/callback/
6. Django verifies signature, reads order notes, creates order in database
7. User redirected to payment success page
```

> **Note:** For local development, use [ngrok](https://ngrok.com) to expose localhost and add the ngrok URL to `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` in `settings.py`.

---

## 🌐 Razorpay Webhook Setup (Optional)

1. Run ngrok: `ngrok http 8000`
2. Go to Razorpay Dashboard → Settings → Webhooks
3. Add webhook URL: `https://your-ngrok-url.ngrok-free.dev/orders/razorpay/webhook/`
4. Select event: `payment.captured`
5. Set secret: same value as `RAZORPAY_WEBHOOK_SECRET` in `.env`

---

## 📦 Requirements

See `requirements.txt`. Key packages:

```
django
psycopg2-binary
razorpay
django-allauth
python-dotenv
python-decouple
Pillow
```

---

## 📄 Environment Variables Reference

| Variable | Description |
|---|---|
| `SECRET_KEY` | Django secret key |
| `DEBUG` | `True` for development, `False` for production |
| `DB_NAME` | PostgreSQL database name |
| `DB_USER` | PostgreSQL username |
| `DB_PASSWORD` | PostgreSQL password |
| `DB_HOST` | Database host (default: localhost) |
| `DB_PORT` | Database port (default: 5432) |
| `EMAIL_HOST_USER` | Gmail address for sending emails |
| `EMAIL_HOST_PASSWORD` | Gmail app password |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret |
| `RAZORPAY_KEY_ID` | Razorpay API key ID |
| `RAZORPAY_KEY_SECRET` | Razorpay API secret |
| `RAZORPAY_WEBHOOK_SECRET` | Razorpay webhook secret |

---

## 👨‍💻 Developer

Built by **Prathiush** as a full-stack Django e-commerce project.

---

## 📝 License

This project is for educational purposes.
