from app import app
from models import db, Product

sample = [
    {"sku":"FIRE-001", "name":"Sparkler 12 inch (pack of 10)", "description":"Bright sparklers for celebrations.", "price":40.0, "stock":100},
    {"sku":"FIRE-002", "name":"Ground Spinner (pack of 5)", "description":"Spinning ground firework effect.", "price":60.0, "stock":50},
    {"sku":"FIRE-003", "name":"Aerial Multi-shot 20", "description":"20 shots aerial battery with colorful bursts.", "price":450.0, "stock":20},
    {"sku":"FIRE-004", "name":"Flower Pot", "description":"Fountain style flower effect.", "price":120.0, "stock":30}
]

with app.app_context():
    db.create_all()
    for p in sample:
        exists = Product.query.filter_by(sku=p["sku"]).first()
        if not exists:
            prod = Product(sku=p["sku"], name=p["name"], description=p["description"], price=p["price"], stock=p["stock"])
            db.session.add(prod)
    db.session.commit()
    print("Seeded database.")
