from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, session
from fpdf import FPDF
import io
import sqlite3
from datetime import datetime
import hashlib

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Change this to a strong secret key

# Initialize database
def init_db():
    conn = sqlite3.connect('restaurant.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS menu 
                 (id INTEGER PRIMARY KEY, name TEXT, price REAL, category TEXT, image TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS orders 
                 (id INTEGER PRIMARY KEY, table_number TEXT, item_id INTEGER, 
                  name TEXT, price REAL, quantity INTEGER, status TEXT, 
                  total REAL, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (id INTEGER PRIMARY KEY, first_name TEXT, last_name TEXT, 
                  restaurant_name TEXT, email TEXT, username TEXT, password TEXT)''')
    conn.commit()
    conn.close()

init_db()

# Sample Menu Data
menu_items = [
    {"id": 1, "name": "Pizza", "price": 12.99, "image": "static/images/pizza.jpg", "category": "Main"},
    {"id": 2, "name": "Burger", "price": 8.99, "image": "static/images/burger.jpg", "category": "Main"},
    {"id": 3, "name": "Salad", "price": 6.49, "image": "static/images/salad.jpg", "category": "Starters"},
    {"id": 4, "name": "Lemonade", "price": 3.99, "image": "static/images/lemonade.jpg", "category": "Drinks"},
    {"id": 5, "name": "Cake", "price": 4.99, "image": "static/images/cake.jpg", "category": "Desserts"},
]

# Populate menu if empty
def populate_menu():
    conn = sqlite3.connect('restaurant.db')
    c = conn.cursor()
    for item in menu_items:
        c.execute("INSERT OR IGNORE INTO menu VALUES (?, ?, ?, ?, ?)", 
                 (item['id'], item['name'], item['price'], item['category'], item['image']))
    conn.commit()
    conn.close()

populate_menu()

# Helper function to hash passwords
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Login route
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        conn = sqlite3.connect('restaurant.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = c.fetchone()
        conn.close()
        
        if user and user[6] == hash_password(password):
            session['user_id'] = user[0]
            session['username'] = user[5]
            session['restaurant_name'] = user[3]
            return redirect(url_for('admin_dashboard'))
        else:
            return render_template("login.html", error="Invalid username or password")
    
    return render_template("login.html")

# Signup route
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        first_name = request.form.get("firstName")
        last_name = request.form.get("lastName")
        restaurant_name = request.form.get("restaurantName")
        email = request.form.get("email")
        username = request.form.get("username")
        password = request.form.get("password")
        confirm_password = request.form.get("confirmPassword")
        
        if password != confirm_password:
            return render_template("signup.html", error="Passwords do not match")
        
        conn = sqlite3.connect('restaurant.db')
        c = conn.cursor()
        
        # Check if username exists
        c.execute("SELECT * FROM users WHERE username = ?", (username,))
        if c.fetchone():
            conn.close()
            return render_template("signup.html", error="Username already exists")
        
        # Check if email exists
        c.execute("SELECT * FROM users WHERE email = ?", (email,))
        if c.fetchone():
            conn.close()
            return render_template("signup.html", error="Email already registered")
        
        # Create user
        hashed_password = hash_password(password)
        c.execute('''INSERT INTO users (first_name, last_name, restaurant_name, email, username, password)
                     VALUES (?, ?, ?, ?, ?, ?)''', 
                 (first_name, last_name, restaurant_name, email, username, hashed_password))
        conn.commit()
        conn.close()
        
        return render_template("signup.html", success="Account created successfully! Please login.")
    
    return render_template("signup.html")

# Logout route
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('index'))

# Login required decorator
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

@app.route("/")
def index():
    return render_template("index.html", menu_items=menu_items)

@app.route("/add_to_cart", methods=["POST"])
def add_to_cart():
    data = request.json
    table = data["table_number"]
    item_id = data["item_id"]
    quantity = data["quantity"]
    
    # Get item details from database
    conn = sqlite3.connect('restaurant.db')
    c = conn.cursor()
    c.execute("SELECT * FROM menu WHERE id = ?", (item_id,))
    item = c.fetchone()
    conn.close()
    
    if not item:
        return jsonify({"success": False, "message": "Item not found"})
    
    # Calculate total
    total = item[2] * quantity
    
    # Save to orders table
    conn = sqlite3.connect('restaurant.db')
    c = conn.cursor()
    c.execute('''INSERT INTO orders (table_number, item_id, name, price, quantity, status, total)
                 VALUES (?, ?, ?, ?, ?, ?, ?)''', 
             (table, item[0], item[1], item[2], quantity, "Pending", total))
    conn.commit()
    conn.close()
    
    return jsonify({"success": True})

@app.route("/get_cart", methods=["POST"])
def get_cart():
    table = request.json["table_number"]
    
    conn = sqlite3.connect('restaurant.db')
    c = conn.cursor()
    c.execute('''SELECT * FROM orders WHERE table_number = ? AND status != 'Served' 
                 ORDER BY timestamp DESC''', (table,))
    items = c.fetchall()
    conn.close()
    
    cart = []
    total = 0
    for item in items:
        cart_item = {
            "id": item[2],
            "name": item[3],
            "price": item[4],
            "qty": item[5],
            "status": item[6],
            "total": item[7]
        }
        cart.append(cart_item)
        total += item[7]
    
    return jsonify({"cart": cart, "total": total})

@app.route("/remove_item", methods=["POST"])
def remove_item():
    data = request.json
    table = data["table_number"]
    item_id = data["item_id"]
    
    conn = sqlite3.connect('restaurant.db')
    c = conn.cursor()
    c.execute("DELETE FROM orders WHERE table_number = ? AND item_id = ?", (table, item_id))
    conn.commit()
    conn.close()
    
    return jsonify({"success": True})

@app.route("/generate_bill", methods=["POST"])
def generate_bill():
    data = request.get_json()
    table_number = data["table_number"]
    
    conn = sqlite3.connect('restaurant.db')
    c = conn.cursor()
    c.execute('''SELECT * FROM orders WHERE table_number = ? AND status != 'Served' 
                 ORDER BY timestamp DESC''', (table_number,))
    items = c.fetchall()
    conn.close()
    
    if not items:
        return jsonify({"success": False, "message": "No items found for this table"})
    
    # Create PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Receipt for Table {table_number}", ln=True, align="C")
    pdf.ln(10)
    
    total = 0
    for item in items:
        line = f"{item[3]} x{item[5]} - ${item[4] * item[5]:.2f}"
        pdf.cell(200, 10, txt=line, ln=True)
        total += item[7]
    
    pdf.ln(10)
    pdf.cell(200, 10, txt=f"Total: ${total:.2f}", ln=True)
    
    # Add date and time
    pdf.ln(10)
    pdf.cell(200, 10, txt=f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
    
    # Add restaurant info
    pdf.ln(10)
    pdf.cell(200, 10, txt="SID's Restaurant", ln=True, align="C")
    pdf.cell(200, 10, txt="Thank you for your visit!", ln=True, align="C")
    
    pdf_bytes = pdf.output(dest='S').encode('latin1')
    pdf_stream = io.BytesIO(pdf_bytes)
    
    return send_file(
        pdf_stream,
        mimetype='application/pdf',
        as_attachment=False,
        download_name=f"receipt_table_{table_number}.pdf"
    )

@app.route("/checkout", methods=["POST"])
def checkout():
    table_number = request.get_json()["table_number"]
    
    conn = sqlite3.connect('restaurant.db')
    c = conn.cursor()
    # Update all items for this table to "Served" status
    c.execute("UPDATE orders SET status = 'Served' WHERE table_number = ?", (table_number,))
    conn.commit()
    conn.close()
    
    return jsonify({"success": True})
# Add this new route to clean up old served orders
@app.route("/cleanup_old_orders", methods=["POST"])
@login_required
def cleanup_old_orders():
    days = request.json.get("days", 7)  # Default to 7 days
    
    conn = sqlite3.connect('restaurant.db')
    c = conn.cursor()
    # Remove orders older than X days that are already served
    c.execute("DELETE FROM orders WHERE status = 'Served' AND timestamp < datetime('now', ?)", 
              (f'-{days} days',))
    conn.commit()
    conn.close()
    
    return jsonify({"success": True, "message": f"Cleaned up orders older than {days} days"})

@app.route("/admin")
@login_required
def admin_dashboard():
    conn = sqlite3.connect('restaurant.db')
    c = conn.cursor()
    
    # Get all active orders (excluding served orders)
    c.execute('''SELECT table_number, item_id, name, price, quantity, status, total 
                 FROM orders WHERE status != 'Served' 
                 ORDER BY table_number, timestamp DESC''')
    orders_data = c.fetchall()
    
    # Calculate total sales (including served orders)
    c.execute("SELECT SUM(total) FROM orders")
    total_sales = c.fetchone()[0] or 0
    
    # Group orders by table
    orders = {}
    for item in orders_data:
        table = item[0]
        if table not in orders:
            orders[table] = []
        orders[table].append({
            "id": item[1],
            "name": item[2],
            "price": item[3],
            "qty": item[4],
            "status": item[5],
            "total": item[6]
        })
    
    conn.close()
    
    return render_template("admin.html", orders=orders, total_sales=total_sales)

@app.route("/update_status", methods=["POST"])
@login_required
def update_status():
    data = request.json
    table = data["table_number"]
    item_id = data["item_id"]
    new_status = data["status"]
    
    conn = sqlite3.connect('restaurant.db')
    c = conn.cursor()
    c.execute('''UPDATE orders SET status = ? 
                 WHERE table_number = ? AND item_id = ?''', 
             (new_status, table, item_id))
    conn.commit()
    conn.close()
    
    return jsonify({"success": True})

@app.route("/remove_order", methods=["POST"])
@login_required
def remove_order():
    data = request.json
    table = data["table_number"]
    
    conn = sqlite3.connect('restaurant.db')
    c = conn.cursor()
    c.execute("DELETE FROM orders WHERE table_number = ?", (table,))
    conn.commit()
    conn.close()
    
    return jsonify({"success": True})

@app.route("/mark_all_served", methods=["POST"])
@login_required
def mark_all_served():
    table_number = request.json["table_number"]
    
    conn = sqlite3.connect('restaurant.db')
    c = conn.cursor()
    c.execute("UPDATE orders SET status = 'Served' WHERE table_number = ?", (table_number,))
    conn.commit()
    conn.close()
    
    return jsonify({"success": True})

if __name__ == "__main__":
    app.run(debug=True)