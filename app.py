from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, Response, jsonify
from config import Config
from models import db, Product, Order, OrderItem
import razorpay
from werkzeug.security import check_password_hash, generate_password_hash
from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, IntegerField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, NumberRange
import csv
import io
from datetime import datetime

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

# Razorpay client
razorpay_client = razorpay.Client(auth=(app.config.get("RAZORPAY_KEY_ID"), app.config.get("RAZORPAY_KEY_SECRET")))

def is_admin():
    return session.get("admin") == True

@app.before_first_request
def create_tables():
    db.create_all()

# Forms
class ProductForm(FlaskForm):
    sku = StringField('SKU', validators=[DataRequired()])
    name = StringField('Name', validators=[DataRequired()])
    description = TextAreaField('Description')
    price = FloatField('Price', validators=[DataRequired(), NumberRange(min=0)])
    stock = IntegerField('Stock', validators=[DataRequired(), NumberRange(min=0)])
    submit = SubmitField('Save')

def get_cart():
    return session.setdefault("cart", {})

# Public routes
@app.route("/")
def index():
    products = Product.query.order_by(Product.name).all()
    return render_template("index.html", products=products)

@app.route("/product/<int:pid>")
def product_detail(pid):
    p = Product.query.get_or_404(pid)
    return render_template("product_detail.html", product=p)

@app.route("/cart")
def cart():
    cart = get_cart()
    items = []
    total = 0.0
    for pid, qty in cart.items():
        p = Product.query.get(int(pid))
        if p:
            subtotal = p.price * qty
            items.append({"product": p, "qty": qty, "subtotal": subtotal})
            total += subtotal
    return render_template("cart.html", items=items, total=total)

@app.route("/cart/add/<int:pid>", methods=["POST"])
def add_to_cart(pid):
    qty = int(request.form.get("qty", 1))
    p = Product.query.get_or_404(pid)
    cart = get_cart()
    current = cart.get(str(pid), 0)
    cart[str(pid)] = current + qty
    session["cart"] = cart
    flash(f"Added {qty} x {p.name} to cart.")
    return redirect(request.referrer or url_for("index"))

@app.route("/cart/update", methods=["POST"])
def update_cart():
    cart = {}
    for key, value in request.form.items():
        if key.startswith("qty_"):
            pid = key.split("_",1)[1]
            try:
                q = int(value)
            except:
                q = 0
            if q > 0:
                cart[pid] = q
    session["cart"] = cart
    flash("Cart updated.")
    return redirect(url_for("cart"))

@app.route("/cart/clear")
def clear_cart():
    session["cart"] = {}
    flash("Cart cleared.")
    return redirect(url_for("index"))

# Checkout (GET) - show cart, pickup points, razorpay key id
@app.route("/checkout", methods=["GET"])
def checkout():
    cart = get_cart()
    if not cart:
        flash("Your cart is empty.")
        return redirect(url_for("index"))

    items = []
    total = 0.0
    for pid, qty in cart.items():
        p = Product.query.get(int(pid))
        if p:
            subtotal = p.price * qty
            items.append({"product": p, "qty": qty, "subtotal": subtotal})
            total += subtotal

    return render_template("checkout.html", items=items, total=total, razorpay_key_id=app.config.get("RAZORPAY_KEY_ID"), pickup_points=app.config.get("PICKUP_LOCATIONS"))

# Create razorpay order and local Order (Pending Payment)
@app.route("/create_razorpay_order", methods=["POST"])
def create_razorpay_order():
    data = request.json or request.form
    name = data.get("name")
    phone = data.get("phone")
    address = data.get("address")
    pickup = data.get("pickup_point")
    cart = session.get("cart", {})

    if not cart:
        return jsonify({"error":"Cart empty"}), 400

    # Calculate total
    total = 0.0
    for pid, qty in cart.items():
        p = Product.query.get(int(pid))
        if not p:
            continue
        if p.stock < int(qty):
            return jsonify({"error": f"Not enough stock for {p.name}. Available {p.stock}"}), 400
        total += p.price * int(qty)

    amount_paise = int(round(total * 100))
    currency = "INR"

    # create Razorpay order
    razorpay_order = razorpay_client.order.create({
        "amount": amount_paise,
        "currency": currency,
        "receipt": f"rcpt_{int(datetime.utcnow().timestamp())}",
        "payment_capture": 1
    })

    # create local order with Pending Payment
    order = Order(customer_name=name, customer_phone=phone, customer_address=address, pickup_point=pickup, total=total, status="Pending Payment")
    db.session.add(order)
    db.session.flush()

    for pid, qty in cart.items():
        p = Product.query.get(int(pid))
        if not p:
            continue
        item = OrderItem(order_id=order.id, product_id=p.id, quantity=int(qty), price=p.price)
        db.session.add(item)

    db.session.commit()

    return jsonify({
        "razorpay_order_id": razorpay_order.get("id"),
        "amount": amount_paise,
        "currency": currency,
        "order_id": order.id,
        "razorpay_key_id": app.config.get("RAZORPAY_KEY_ID")
    })

# Verify payment signature and finalize order
@app.route("/payment/verify", methods=["POST"])
def payment_verify():
    payload = request.json or request.form
    razorpay_order_id = payload.get("razorpay_order_id")
    razorpay_payment_id = payload.get("razorpay_payment_id")
    razorpay_signature = payload.get("razorpay_signature")
    internal_order_id = payload.get("order_id")

    if not (razorpay_order_id and razorpay_payment_id and razorpay_signature and internal_order_id):
        return jsonify({"error":"Missing payment data"}), 400

    params_dict = {
        'razorpay_order_id': razorpay_order_id,
        'razorpay_payment_id': razorpay_payment_id,
        'razorpay_signature': razorpay_signature
    }

    try:
        razorpay_client.utility.verify_payment_signature(params_dict)
    except Exception:
        order = Order.query.get(int(internal_order_id))
        if order:
            order.status = "Payment Failed"
            db.session.commit()
        return jsonify({"status":"failure","reason":"signature verification failed"}), 400

    order = Order.query.get(int(internal_order_id))
    if not order:
        return jsonify({"error":"Internal order not found"}), 404

    # reduce stock
    for it in order.items:
        p = Product.query.get(it.product_id)
        if p:
            if p.stock < it.quantity:
                order.status = "Failed - insufficient stock"
                db.session.commit()
                return jsonify({"status":"failure","reason":"insufficient stock"}), 400
            p.stock -= it.quantity

    order.status = "Completed"
    db.session.commit()

    # clear cart
    session["cart"] = {}

    return jsonify({"status":"success", "order_id": order.id})

# Order receipt
@app.route("/order/<int:oid>/receipt")
def order_receipt(oid):
    order = Order.query.get_or_404(oid)
    return render_template("orders.html", orders=[order], single=True)

# Admin routes
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == app.config["ADMIN_USERNAME"] and password == app.config["ADMIN_PASSWORD"]:
            session["admin"] = True
            flash("Logged in as admin.")
            return redirect(url_for("admin_products"))
        else:
            flash("Bad credentials.")
    return render_template("login.html")

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    flash("Logged out.")
    return redirect(url_for("index"))

@app.route("/admin/products")
def admin_products():
    if not is_admin():
        return redirect(url_for("admin_login"))
    products = Product.query.order_by(Product.created_at.desc()).all()
    return render_template("index.html", products=products, admin=True)

@app.route("/admin/product/new", methods=["GET","POST"])
@app.route("/admin/product/<int:pid>/edit", methods=["GET","POST"])
def admin_product_form(pid=None):
    if not is_admin():
        return redirect(url_for("admin_login"))
    form = ProductForm()
    product = None
    if pid:
        product = Product.query.get_or_404(pid)
        if request.method == "GET":
            form.sku.data = product.sku
            form.name.data = product.name
            form.description.data = product.description
            form.price.data = product.price
            form.stock.data = product.stock
    if form.validate_on_submit():
        if product is None:
            product = Product()
            db.session.add(product)
        product.sku = form.sku.data
        product.name = form.name.data
        product.description = form.description.data
        product.price = form.price.data
        product.stock = form.stock.data
        db.session.commit()
        flash("Product saved.")
        return redirect(url_for("admin_products"))
    return render_template("product_form.html", form=form, product=product)

@app.route("/admin/product/<int:pid>/delete", methods=["POST"])
def admin_product_delete(pid):
    if not is_admin():
        return redirect(url_for("admin_login"))
    p = Product.query.get_or_404(pid)
    db.session.delete(p)
    db.session.commit()
    flash("Product deleted.")
    return redirect(url_for("admin_products"))

@app.route("/admin/orders")
def admin_orders():
    if not is_admin():
        return redirect(url_for("admin_login"))
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template("orders.html", orders=orders)

@app.route("/admin/orders/export")
def admin_export_orders():
    if not is_admin():
        return redirect(url_for("admin_login"))
    orders = Order.query.order_by(Order.created_at.desc()).all()
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(["order_id","date","customer_name","phone","address","pickup_point","total","status","items"])
    for o in orders:
        items_summary = "; ".join([f"{it.product.name} x{it.quantity} @ {it.price}" for it in o.items])
        cw.writerow([o.id, o.created_at.isoformat(), o.customer_name, o.customer_phone, o.customer_address, o.pickup_point, o.total, o.status, items_summary])
    output = Response(si.getvalue(), mimetype="text/csv")
    output.headers["Content-Disposition"] = "attachment; filename=orders.csv"
    return output

if __name__ == "__main__":
    app.run(debug=True)
