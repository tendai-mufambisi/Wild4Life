# w4l_donations

Online donation system for **Wild4Life Organisation** (Zimbabwe PVO).  
Integrates with [Paynow Zimbabwe](https://www.paynow.co.zw/) using the Web / Hosted-Page (redirect) flow.

Built with Python 3.11+, Django 5.x, and the official `paynow` PyPI package.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Environment Variables](#environment-variables)
3. [Running Tests](#running-tests)
4. [Paynow: Test Mode vs Live](#paynow-test-mode-vs-live)
5. [Project Structure](#project-structure)
6. [Payment Flow](#payment-flow)
7. [Admin Dashboard](#admin-dashboard)
8. [Client Checklist](#client-checklist-what-the-client-must-supply)

---

## Quick Start

```bash
# 1. Clone and enter the project
git clone <repo-url>
cd Wild4Life

# 2. Create and activate a virtual environment
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Open .env and fill in real values (see Environment Variables below)

# 5. Apply migrations
python manage.py migrate

# 6. Create the admin superuser (reads from .env — no interactive prompt)
python manage.py createadmin

# 7. Collect static files (production) or run dev server directly
python manage.py runserver
```

The donation form is at **http://localhost:8000/donate/**  
The admin dashboard is at **http://localhost:8000/admin/**

---

## Environment Variables

Copy `.env.example` to `.env` and set every variable. The application will
**refuse to start** (`ImproperlyConfigured`) if a required variable is absent.

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | Yes | Django secret key. Generate with `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` |
| `DEBUG` | Yes | `True` for development, `False` for production |
| `ALLOWED_HOSTS` | Yes | Comma-separated hostnames, e.g. `localhost,127.0.0.1,yourdomain.com` |
| `DATABASE_URL` | Yes | SQLite: `sqlite:///db.sqlite3` — Postgres: `postgres://USER:PASS@HOST:PORT/DBNAME` |
| `PAYNOW_INTEGRATION_ID` | Yes | From your Paynow merchant portal |
| `PAYNOW_INTEGRATION_KEY` | Yes | From your Paynow merchant portal |
| `PAYNOW_RETURN_URL` | Yes | Browser redirect after payment. Must be publicly reachable, e.g. `https://yourdomain.com/donation/return/` |
| `PAYNOW_RESULT_URL` | Yes | Server-to-server IPN callback. Must be publicly reachable, e.g. `https://yourdomain.com/paynow/result/` |
| `SITE_BASE_URL` | Yes | Base URL of the site, e.g. `https://yourdomain.com` |
| `DEFAULT_CURRENCY` | Yes | `USD` or `ZWG` |
| `EMAIL_HOST` | Prod | SMTP host, e.g. `smtp.gmail.com` |
| `EMAIL_PORT` | Prod | SMTP port, e.g. `587` |
| `EMAIL_USE_TLS` | Prod | `True` or `False` |
| `EMAIL_HOST_USER` | Prod | SMTP username / email address |
| `EMAIL_HOST_PASSWORD` | Prod | SMTP password or app password |
| `DEFAULT_FROM_EMAIL` | Prod | Sender address shown to donors |
| `DJANGO_SUPERUSER_USERNAME` | Yes | Admin username created by `createadmin` |
| `DJANGO_SUPERUSER_EMAIL` | Yes | Admin email |
| `DJANGO_SUPERUSER_PASSWORD` | Yes | Admin password — change immediately after first login |

> **Note on email in development:** When `DEBUG=True`, the console email backend
> is used automatically. Confirmation emails are printed to the terminal instead
> of being sent. No SMTP configuration is needed in development.

### Local dev with ngrok (for Paynow callbacks)

Paynow must be able to POST to your `PAYNOW_RESULT_URL`. In development,
expose your local server with [ngrok](https://ngrok.com/):

```bash
ngrok http 8000
```

Then update `.env`:

```
PAYNOW_RETURN_URL=https://xxxx.ngrok.io/donation/return/
PAYNOW_RESULT_URL=https://xxxx.ngrok.io/paynow/result/
```

---

## Running Tests

```bash
# Run the full test suite
pytest

# Run with verbose output
pytest -v

# Run a specific test module
pytest tests/test_models.py
pytest tests/test_utils.py
pytest tests/test_paynow_service.py
pytest tests/test_views.py
```

Tests use `pytest-django` with a mocked Paynow SDK — no real Paynow credentials
are required. Coverage includes:

- Donor deduplication (phone-primary, email-secondary)
- Reference generation uniqueness under concurrency
- Donation state-machine guard (no double-paid)
- Form validation (phone normalization, amount > 0)
- Phone normalization utility (all Zimbabwean formats)
- Paynow service with mocked SDK responses

---

## Paynow: Test Mode vs Live

### How Paynow test mode works

Paynow provides separate test credentials that simulate the payment flow without
real money moving. The application code is identical — only the credentials change.

### Switching from test to live

1. Log in to your Paynow merchant account at https://www.paynow.co.zw/
2. Navigate to **Payment** → **Get Integration Details**
3. Copy your **live** Integration ID and Integration Key
4. Update `.env`:

```
PAYNOW_INTEGRATION_ID=<live-id>
PAYNOW_INTEGRATION_KEY=<live-key>
```

5. Ensure `PAYNOW_RETURN_URL` and `PAYNOW_RESULT_URL` point to your **public
   production domain** (not localhost or ngrok)
6. Register those URLs in the Paynow merchant portal under
   **Payment** → **Integration Settings** → Result URL / Return URL
7. Set `DEBUG=False` in production

> There is no code change — the toggle is 100% in environment variables.

### Test card / mobile number

Paynow's sandbox provides test mobile wallet numbers. Check the
[Paynow documentation](https://developers.paynow.co.zw/) for the current test
credentials for Ecocash, OneMoney, and Innbucks.

---

## Project Structure

```
Wild4Life/
├── manage.py
├── requirements.txt
├── pytest.ini
├── .env.example            # copy to .env, fill in values
├── .gitignore
│
├── w4l_donations/          # Django project settings
│   ├── settings.py         # all config via django-environ
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
│
├── donations/              # main app
│   ├── models.py           # Donor, Donation, ReferenceCounter
│   ├── forms.py            # DonationForm
│   ├── views.py            # donate, donation_return, paynow_result
│   ├── urls.py
│   ├── admin.py            # DonorAdmin, DonationAdmin
│   ├── utils.py            # normalize_phone()
│   ├── paynow_service.py   # ONLY file that imports the paynow SDK
│   └── management/
│       └── commands/
│           └── createadmin.py
│
├── templates/
│   ├── base.html
│   └── donations/
│       ├── donate.html
│       ├── thank_you.html
│       └── error.html
│
├── static/
│   └── css/
│       └── w4l.css         # single CSS file, no frameworks
│
└── tests/
    ├── conftest.py
    ├── test_models.py
    ├── test_paynow_service.py
    ├── test_utils.py
    └── test_views.py
```

### Key design decisions

- **`donations/paynow_service.py` is the only file that imports the `paynow` SDK.**
  If the SDK changes its API, only this one file needs updating.
- Money is stored as `DecimalField`, never `float`.
- Donor identity is keyed on **phone number** (normalized to `+263XXXXXXXXX`),
  with email as a secondary fallback.
- Donation references (`W4L-YYYY-NNNNNN`) are generated atomically with
  `SELECT FOR UPDATE` to handle concurrent requests safely.
- The IPN result URL (`/paynow/result/`) is idempotent — calling it twice for
  the same donation will not send two emails or corrupt the status.

---

## Payment Flow

```
Donor fills form (/donate/)
        │
        ▼
POST /donate/ — validate, create Donor + Donation (PENDING),
                call paynow_service.initiate_payment()
        │
        ▼
Redirect to Paynow hosted page
        │
        ├─── Server-to-server IPN ──► POST /paynow/result/
        │                              verify_payment() polls Paynow,
        │                              updates status + paid_at,
        │                              sends confirmation email (once)
        │
        └─── Browser return ────────► GET /donation/return/
                                       verify_payment() called again (idempotent)
                                       Renders thank_you.html with reference code
```

---

## Admin Dashboard

Access at `/admin/` with the superuser created by `createadmin`.

**Donation list** shows: reference, donor name, phone, amount, currency,
status, created, paid at. Filterable by status / currency / date. Searchable
by reference, name, phone, email.

**Donor list** shows: name, email, total donated, donation count.
Each donor record includes an inline list of all their donations.

All financial fields (amount, reference, timestamps, Paynow fields) are
**read-only in admin** — money records cannot be hand-edited.

---

## Client Checklist — What the Client Must Supply

Before going live, the client (Wild4Life) must:

- [ ] Create a Paynow merchant account at https://www.paynow.co.zw/
- [ ] Obtain live **Integration ID** and **Integration Key** from the Paynow portal
- [ ] Register the production **Return URL** in the Paynow portal
      (e.g. `https://donate.wild4life.org.zw/donation/return/`)
- [ ] Register the production **Result URL** in the Paynow portal
      (e.g. `https://donate.wild4life.org.zw/paynow/result/`)
- [ ] Confirm the merchant account currency matches `DEFAULT_CURRENCY` in `.env`
      (USD accounts cannot accept ZWG payments and vice versa)
- [ ] Provide SMTP credentials for outgoing donor confirmation emails
- [ ] Set `DEBUG=False` and a strong `SECRET_KEY` in production `.env`
- [ ] Place the production server behind HTTPS (required by Paynow for result URLs)
- [ ] Change the admin password after first login (`createadmin` sets a temporary one)

---

*Wild4Life Organisation — Protecting Zimbabwe's wildlife.*
