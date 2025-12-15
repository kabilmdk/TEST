import os
from dotenv import load_dotenv
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.getenv("DB_PATH", os.path.join(BASE_DIR, "store.db"))

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "change-me-123")
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{DB_PATH}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "password")
    # Razorpay
    RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
    RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")
    # Pickup locations (configure as you need)
    PICKUP_LOCATIONS = [
        "Main Shop - Anna Nagar",
        "Warehouse Pickup - Tambaram",
        "Self Pickup - T Nagar",
        "Delivery Hub - Chrompet",
    ]
