# Crackers Store (Full Project)

This is a full-stack Flask project for a crackers (fireworks) retail store with:
- Product catalog (admin CRUD)
- Cart & Checkout
- Razorpay payment integration (test keys)
- Pickup point selection stored with orders
- Admin order export (CSV)
- Simple session-based admin login

## Quick start (Linux/macOS / WSL)
1. Unzip the project and `cd` into it:
   ```bash
   unzip crackers_store_full.zip -d crackers_store_full
   cd crackers_store_full
   ```

2. (Optional) create a Python virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file (copy from `.env.example`) and set values:
   ```bash
   cp .env.example .env
   # edit .env to add your Razorpay test keys and optionally change ADMIN_PASSWORD
   ```

5. Seed sample data (optional):
   ```bash
   python seed_db.py
   ```

6. Run the app:
   ```bash
   python app.py
   ```

7. Open in browser:
   ```
   http://127.0.0.1:5000
   ```

## Admin
- Default admin username / password: from `.env` (see `.env.example`)
- Admin area: `/admin/login` and `/admin/products`

## Razorpay
- Use test keys in `.env` (`RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET`)
- The checkout flow uses client-side Razorpay Checkout and server-side signature verification.

## Notes
- This project stores the admin password plainly for demo purposes — **do not use in production**.
- For production use, add secure auth (Flask-Login), HTTPS, proper secret management, and webhooks.

