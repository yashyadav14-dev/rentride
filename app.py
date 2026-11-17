import os
import uuid
from datetime import datetime, date
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, session, g, jsonify
)
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config
from db import query_db, execute_db

app = Flask(__name__)
app.config.from_object(Config)

# ----------------------------------------------------
# Authentication Helpers & Middleware
# ----------------------------------------------------

@app.before_request
def load_logged_in_user():
    user_id = session.get('user_id')
    if user_id is None:
        g.user = None
    else:
        g.user = query_db(
            "SELECT user_id, name, email, phone, address, license_no, role FROM users WHERE user_id = %s",
            (user_id,),
            one=True
        )

@app.context_processor
def inject_user_and_types():
    types = []
    try:
        types = query_db("SELECT * FROM vehicle_types ORDER BY type_name ASC")
    except Exception:
        pass
    return dict(current_user=g.user, vehicle_types=types)

# ----------------------------------------------------
# Indian Date & Time Formatting Filters
# ----------------------------------------------------

@app.template_filter('indian_date')
def indian_date_filter(val):
    if not val:
        return ""
    if isinstance(val, (datetime, date)):
        return val.strftime('%d/%m/%Y')
    try:
        dt = datetime.strptime(str(val)[:10], '%Y-%m-%d')
        return dt.strftime('%d/%m/%Y')
    except Exception:
        return str(val)

@app.template_filter('indian_datetime')
def indian_datetime_filter(val):
    if not val:
        return ""
    if isinstance(val, (datetime, date)):
        return val.strftime('%d/%m/%Y %I:%M %p')
    try:
        dt = datetime.strptime(str(val)[:19], '%Y-%m-%d %H:%M:%S')
        return dt.strftime('%d/%m/%Y %I:%M %p')
    except Exception:
        return str(val)

def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            flash("Please sign in to access this page.", "warning")
            return redirect(url_for('login', next=request.url))
        return view(**kwargs)
    return wrapped_view

def admin_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None or g.user.get('role') != 'admin':
            flash("Administrator privilege required.", "danger")
            return redirect(url_for('index'))
        return view(**kwargs)
    return wrapped_view

# ----------------------------------------------------
# Public Routes: Home & Catalog
# ----------------------------------------------------

@app.route('/')
def index():
    # Featured cars and bikes
    featured_vehicles = query_db("""
        SELECT v.*, vt.type_name,
               (SELECT image_url FROM vehicle_images vi WHERE vi.vehicle_id = v.vehicle_id LIMIT 1) AS primary_image,
               COALESCE(AVG(r.rating), 5.0) as avg_rating,
               COUNT(r.review_id) as review_count
        FROM vehicles v
        JOIN vehicle_types vt ON v.type_id = vt.type_id
        LEFT JOIN reviews r ON v.vehicle_id = r.vehicle_id
        WHERE v.status = 'Available'
        GROUP BY v.vehicle_id
        ORDER BY v.vehicle_id DESC
        LIMIT 6
    """)

    latest_reviews = query_db("""
        SELECT r.*, u.name as user_name, v.brand, v.model, v.vehicle_type
        FROM reviews r
        JOIN users u ON r.user_id = u.user_id
        JOIN vehicles v ON r.vehicle_id = v.vehicle_id
        ORDER BY r.review_date DESC
        LIMIT 3
    """)

    return render_template('index.html', featured_vehicles=featured_vehicles, latest_reviews=latest_reviews)

@app.route('/vehicles')
def vehicles_list():
    v_type = request.args.get('type', '').strip()
    brand = request.args.get('brand', '').strip()
    fuel = request.args.get('fuel', '').strip()
    search = request.args.get('q', '').strip()
    max_price = request.args.get('max_price', '').strip()

    sql = """
        SELECT v.*, vt.type_name,
               (SELECT image_url FROM vehicle_images vi WHERE vi.vehicle_id = v.vehicle_id LIMIT 1) AS primary_image,
               COALESCE(AVG(r.rating), 0) as avg_rating,
               COUNT(r.review_id) as review_count
        FROM vehicles v
        JOIN vehicle_types vt ON v.type_id = vt.type_id
        LEFT JOIN reviews r ON v.vehicle_id = r.vehicle_id
        WHERE 1=1
    """
    params = []

    if v_type:
        sql += " AND v.vehicle_type = %s"
        params.append(v_type)
    if brand:
        sql += " AND v.brand LIKE %s"
        params.append(f"%{brand}%")
    if fuel:
        sql += " AND v.fuel_type = %s"
        params.append(fuel)
    if search:
        sql += " AND (v.brand LIKE %s OR v.model LIKE %s)"
        params.extend([f"%{search}%", f"%{search}%"])
    if max_price:
        try:
            sql += " AND v.price_per_day <= %s"
            params.append(float(max_price))
        except ValueError:
            pass

    sql += " GROUP BY v.vehicle_id ORDER BY v.vehicle_id DESC"
    vehicles = query_db(sql, params)

    # Distinct brands for filter dropdown
    brands = query_db("SELECT DISTINCT brand FROM vehicles ORDER BY brand ASC")

    return render_template(
        'vehicles.html',
        vehicles=vehicles,
        brands=brands,
        selected_type=v_type,
        selected_brand=brand,
        selected_fuel=fuel,
        search_query=search,
        selected_max_price=max_price
    )

@app.route('/vehicles/<int:vehicle_id>')
def vehicle_detail(vehicle_id):
    vehicle = query_db("""
        SELECT v.*, vt.type_name,
               COALESCE(AVG(r.rating), 0) as avg_rating,
               COUNT(r.review_id) as review_count
        FROM vehicles v
        JOIN vehicle_types vt ON v.type_id = vt.type_id
        LEFT JOIN reviews r ON v.vehicle_id = r.vehicle_id
        WHERE v.vehicle_id = %s
        GROUP BY v.vehicle_id
    """, (vehicle_id,), one=True)

    if not vehicle:
        flash("Vehicle not found.", "danger")
        return redirect(url_for('vehicles_list'))

    # All images for this vehicle
    images = query_db("SELECT * FROM vehicle_images WHERE vehicle_id = %s", (vehicle_id,))
    
    # Reviews
    reviews = query_db("""
        SELECT r.*, u.name as user_name
        FROM reviews r
        JOIN users u ON r.user_id = u.user_id
        WHERE r.vehicle_id = %s
        ORDER BY r.review_date DESC
    """, (vehicle_id,))

    return render_template('vehicle_detail.html', vehicle=vehicle, images=images, reviews=reviews)

# ----------------------------------------------------
# Authentication: Login, Register, Profile, Logout
# ----------------------------------------------------

@app.route('/login', methods=['GET', 'POST'])
def login():
    if g.user:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        user = query_db("SELECT * FROM users WHERE email = %s", (email,), one=True)
        if user and check_password_hash(user['password'], password):
            session.clear()
            session['user_id'] = user['user_id']
            session['user_name'] = user['name']
            session['role'] = user['role']
            flash(f"Welcome back, {user['name']}!", "success")
            
            next_page = request.args.get('next')
            if user['role'] == 'admin':
                return redirect(next_page or url_for('admin_dashboard'))
            return redirect(next_page or url_for('index'))
        else:
            flash("Invalid email or password. Please try again.", "danger")

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if g.user:
        return redirect(url_for('index'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        license_no = request.form.get('license_no', '').strip()

        if not name or not email or not password or not license_no:
            flash("All mandatory fields (Name, Email, Password, Driving License) are required.", "danger")
            return render_template('register.html')

        existing = query_db("SELECT user_id FROM users WHERE email = %s", (email,), one=True)
        if existing:
            flash("An account with this email already exists. Please log in.", "warning")
            return redirect(url_for('login'))

        hashed_password = generate_password_hash(password)
        try:
            user_id = execute_db(
                """
                INSERT INTO users (name, email, password, phone, address, license_no, role)
                VALUES (%s, %s, %s, %s, %s, %s, 'customer')
                """,
                (name, email, hashed_password, phone, address, license_no)
            )
            session.clear()
            session['user_id'] = user_id
            session['user_name'] = name
            session['role'] = 'customer'
            flash("Account registered successfully! Welcome to RentRide.", "success")
            return redirect(url_for('index'))
        except Exception as e:
            flash(f"Registration error: {e}", "danger")

    return render_template('register.html')

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        license_no = request.form.get('license_no', '').strip()

        execute_db(
            "UPDATE users SET name = %s, phone = %s, address = %s, license_no = %s WHERE user_id = %s",
            (name, phone, address, license_no, g.user['user_id'])
        )
        flash("Profile updated successfully!", "success")
        return redirect(url_for('profile'))

    return render_template('profile.html', user=g.user)

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been signed out.", "info")
    return redirect(url_for('index'))

# ----------------------------------------------------
# Booking & Payment Flows
# ----------------------------------------------------

@app.route('/book/<int:vehicle_id>', methods=['GET', 'POST'])
@login_required
def book(vehicle_id):
    vehicle = query_db("""
        SELECT v.*, vt.type_name,
               (SELECT image_url FROM vehicle_images vi WHERE vi.vehicle_id = v.vehicle_id LIMIT 1) AS primary_image
        FROM vehicles v
        JOIN vehicle_types vt ON v.type_id = vt.type_id
        WHERE v.vehicle_id = %s
    """, (vehicle_id,), one=True)

    if not vehicle:
        flash("Vehicle not found.", "danger")
        return redirect(url_for('vehicles_list'))

    if vehicle['status'] != 'Available':
        flash("This vehicle is currently not available for booking.", "warning")
        return redirect(url_for('vehicle_detail', vehicle_id=vehicle_id))

    fixed_pickup_location = "Sanghvi"
    # Security deposit in INR: ₹3,000 for Cars, ₹1,500 for Bikes (refundable upon safe return)
    deposit_amount = 3000.00 if vehicle['vehicle_type'] == 'Car' else 1500.00

    if request.method == 'POST':
        pickup_date_str = request.form.get('pickup_date')
        return_date_str = request.form.get('return_date')
        pickup_location = fixed_pickup_location
        return_location = request.form.get('return_location', fixed_pickup_location).strip() or fixed_pickup_location
        damage_agreement = request.form.get('damage_agreement')

        if not damage_agreement:
            flash("You must review and accept the Vehicle Damage & Liability Policy before proceeding.", "danger")
            today_str = date.today().strftime('%Y-%m-%d')
            return render_template('book.html', vehicle=vehicle, today=today_str, fixed_pickup=fixed_pickup_location, deposit_amount=deposit_amount)

        if not pickup_date_str or not return_date_str:
            flash("All booking date fields are required.", "danger")
            today_str = date.today().strftime('%Y-%m-%d')
            return render_template('book.html', vehicle=vehicle, today=today_str, fixed_pickup=fixed_pickup_location, deposit_amount=deposit_amount)

        try:
            pickup_date = datetime.strptime(pickup_date_str, '%Y-%m-%d').date()
            return_date = datetime.strptime(return_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash("Invalid date format provided.", "danger")
            today_str = date.today().strftime('%Y-%m-%d')
            return render_template('book.html', vehicle=vehicle, today=today_str, fixed_pickup=fixed_pickup_location, deposit_amount=deposit_amount)

        if pickup_date < date.today():
            flash("Pickup date cannot be in the past.", "danger")
            today_str = date.today().strftime('%Y-%m-%d')
            return render_template('book.html', vehicle=vehicle, today=today_str, fixed_pickup=fixed_pickup_location, deposit_amount=deposit_amount)

        if return_date <= pickup_date:
            flash("Return date must be after pickup date (minimum 1 day rental).", "danger")
            today_str = date.today().strftime('%Y-%m-%d')
            return render_template('book.html', vehicle=vehicle, today=today_str, fixed_pickup=fixed_pickup_location, deposit_amount=deposit_amount)

        total_days = (return_date - pickup_date).days
        rental_price = total_days * float(vehicle['price_per_day'])
        total_price = rental_price + deposit_amount

        # Create Booking with fixed Sanghvi pickup, deposit amount, and damage liability agreement
        booking_id = execute_db(
            """
            INSERT INTO bookings (user_id, vehicle_id, pickup_date, return_date, pickup_location, return_location, total_days, rental_price, deposit_amount, total_price, damage_agreement_accepted, booking_status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1, 'Pending')
            """,
            (g.user['user_id'], vehicle_id, pickup_date, return_date, pickup_location, return_location, total_days, rental_price, deposit_amount, total_price)
        )

        return redirect(url_for('payment', booking_id=booking_id))

    today_str = date.today().strftime('%Y-%m-%d')
    return render_template('book.html', vehicle=vehicle, today=today_str, fixed_pickup=fixed_pickup_location, deposit_amount=deposit_amount)

@app.route('/payment/<int:booking_id>', methods=['GET', 'POST'])
@login_required
def payment(booking_id):
    booking = query_db("""
        SELECT b.*, v.brand, v.model, v.vehicle_type, v.price_per_day,
               (SELECT image_url FROM vehicle_images vi WHERE vi.vehicle_id = v.vehicle_id LIMIT 1) AS primary_image
        FROM bookings b
        JOIN vehicles v ON b.vehicle_id = v.vehicle_id
        WHERE b.booking_id = %s AND b.user_id = %s
    """, (booking_id, g.user['user_id']), one=True)

    if not booking:
        flash("Booking not found or unauthorized.", "danger")
        return redirect(url_for('my_bookings'))

    if booking['booking_status'] == 'Confirmed':
        flash("This booking is already paid and confirmed.", "info")
        return redirect(url_for('my_bookings'))

    if request.method == 'POST':
        payment_method = request.form.get('payment_method', 'Credit Card')
        amount = booking['total_price']
        transaction_id = f"TXN-{uuid.uuid4().hex[:10].upper()}"

        # Insert Payment
        execute_db(
            """
            INSERT INTO payments (booking_id, amount, payment_method, payment_status, transaction_id)
            VALUES (%s, %s, %s, 'Paid', %s)
            """,
            (booking_id, amount, payment_method, transaction_id)
        )

        # Update Booking Status to Confirmed
        execute_db(
            "UPDATE bookings SET booking_status = 'Confirmed' WHERE booking_id = %s",
            (booking_id,)
        )

        # Update vehicle status to 'Rented'
        execute_db(
            "UPDATE vehicles SET status = 'Rented' WHERE vehicle_id = %s",
            (booking['vehicle_id'],)
        )

        flash(f"Payment successful! Transaction ID: {transaction_id}. Your rental is confirmed.", "success")
        return redirect(url_for('my_bookings'))

    return render_template('payment.html', booking=booking)

@app.route('/my-bookings')
@login_required
def my_bookings():
    bookings = query_db("""
        SELECT b.*, v.brand, v.model, v.vehicle_type,
               (SELECT image_url FROM vehicle_images vi WHERE vi.vehicle_id = v.vehicle_id LIMIT 1) AS primary_image,
               p.payment_id, p.payment_method, p.payment_status, p.transaction_id, p.payment_date
        FROM bookings b
        JOIN vehicles v ON b.vehicle_id = v.vehicle_id
        LEFT JOIN payments p ON b.booking_id = p.booking_id
        WHERE b.user_id = %s
        ORDER BY b.booking_id DESC
    """, (g.user['user_id'],))

    return render_template('my_bookings.html', bookings=bookings)

@app.route('/cancel-booking/<int:booking_id>', methods=['POST'])
@login_required
def cancel_booking(booking_id):
    booking = query_db(
        "SELECT * FROM bookings WHERE booking_id = %s AND user_id = %s",
        (booking_id, g.user['user_id']),
        one=True
    )

    if not booking:
        flash("Booking not found.", "danger")
        return redirect(url_for('my_bookings'))

    if booking['booking_status'] in ['Completed', 'Cancelled']:
        flash("Cannot cancel a completed or already cancelled booking.", "warning")
        return redirect(url_for('my_bookings'))

    # Mark booking cancelled
    execute_db("UPDATE bookings SET booking_status = 'Cancelled' WHERE booking_id = %s", (booking_id,))

    # Make vehicle available again
    execute_db("UPDATE vehicles SET status = 'Available' WHERE vehicle_id = %s", (booking['vehicle_id'],))

    # If paid, update payment status to Refunded
    execute_db("UPDATE payments SET payment_status = 'Refunded' WHERE booking_id = %s", (booking_id,))

    flash("Booking has been successfully cancelled and refund initiated.", "info")
    return redirect(url_for('my_bookings'))

# ----------------------------------------------------
# Reviews Route
# ----------------------------------------------------

@app.route('/vehicles/<int:vehicle_id>/review', methods=['POST'])
@login_required
def add_review(vehicle_id):
    rating = request.form.get('rating', type=int)
    comment = request.form.get('comment', '').strip()

    if not rating or rating < 1 or rating > 5:
        flash("Please provide a valid rating between 1 and 5 stars.", "danger")
        return redirect(url_for('vehicle_detail', vehicle_id=vehicle_id))

    execute_db(
        "INSERT INTO reviews (user_id, vehicle_id, rating, comment) VALUES (%s, %s, %s, %s)",
        (g.user['user_id'], vehicle_id, rating, comment)
    )

    flash("Thank you! Your review has been submitted.", "success")
    return redirect(url_for('vehicle_detail', vehicle_id=vehicle_id))

# ----------------------------------------------------
# Admin Portal Routes
# ----------------------------------------------------

@app.route('/admin')
@admin_required
def admin_dashboard():
    # 1. User & Vehicle Insights
    total_users = query_db("SELECT COUNT(*) as count FROM users WHERE role = 'customer'", one=True)['count']
    total_vehicles = query_db("SELECT COUNT(*) as count FROM vehicles", one=True)['count']
    cars_count = query_db("SELECT COUNT(*) as count FROM vehicles WHERE vehicle_type = 'Car'", one=True)['count']
    bikes_count = query_db("SELECT COUNT(*) as count FROM vehicles WHERE vehicle_type = 'Bike'", one=True)['count']
    available_count = query_db("SELECT COUNT(*) as count FROM vehicles WHERE status = 'Available'", one=True)['count']
    rented_count = query_db("SELECT COUNT(*) as count FROM vehicles WHERE status = 'Rented'", one=True)['count']
    maintenance_count = query_db("SELECT COUNT(*) as count FROM vehicles WHERE status = 'Maintenance'", one=True)['count']

    # 2. Bookings Insights
    total_bookings = query_db("SELECT COUNT(*) as count FROM bookings", one=True)['count']
    pending_bookings = query_db("SELECT COUNT(*) as count FROM bookings WHERE booking_status = 'Pending'", one=True)['count']
    confirmed_bookings = query_db("SELECT COUNT(*) as count FROM bookings WHERE booking_status = 'Confirmed'", one=True)['count']
    completed_bookings = query_db("SELECT COUNT(*) as count FROM bookings WHERE booking_status = 'Completed'", one=True)['count']
    cancelled_bookings = query_db("SELECT COUNT(*) as count FROM bookings WHERE booking_status = 'Cancelled'", one=True)['count']

    # 3. Financial Insights
    total_revenue = query_db("SELECT COALESCE(SUM(amount), 0) as total FROM payments WHERE payment_status = 'Paid'", one=True)['total']
    total_deposits = query_db("SELECT COALESCE(SUM(deposit_amount), 0) as total FROM bookings WHERE booking_status IN ('Confirmed', 'Completed')", one=True)['total']
    net_rental_earnings = float(total_revenue) - float(total_deposits)
    if net_rental_earnings < 0:
        net_rental_earnings = float(total_revenue)

    # 4. Reviews & Rating Insights
    reviews_stat = query_db("SELECT COUNT(*) as cnt, COALESCE(AVG(rating), 0) as avg_rating FROM reviews", one=True)
    total_reviews = reviews_stat['cnt']
    avg_rating = round(float(reviews_stat['avg_rating']), 1)

    # Top Rented Vehicles
    top_vehicles = query_db("""
        SELECT v.vehicle_id, v.brand, v.model, v.vehicle_type, v.price_per_day,
               COUNT(b.booking_id) as booking_count,
               (SELECT image_url FROM vehicle_images vi WHERE vi.vehicle_id = v.vehicle_id LIMIT 1) AS primary_image
        FROM vehicles v
        LEFT JOIN bookings b ON v.vehicle_id = b.vehicle_id
        GROUP BY v.vehicle_id
        ORDER BY booking_count DESC, v.vehicle_id DESC
        LIMIT 5
    """)

    # 5. Full Lists for Dashboard Tabs
    vehicles = query_db("""
        SELECT v.*, vt.type_name,
               (SELECT image_url FROM vehicle_images vi WHERE vi.vehicle_id = v.vehicle_id LIMIT 1) AS primary_image,
               COALESCE(AVG(r.rating), 0) as avg_rating,
               COUNT(r.review_id) as review_count
        FROM vehicles v
        JOIN vehicle_types vt ON v.type_id = vt.type_id
        LEFT JOIN reviews r ON v.vehicle_id = r.vehicle_id
        GROUP BY v.vehicle_id
        ORDER BY v.vehicle_id DESC
    """)

    bookings = query_db("""
        SELECT b.*, u.name as customer_name, u.phone, u.email, u.license_no, v.brand, v.model, v.vehicle_type,
               p.payment_status, p.payment_method, p.transaction_id
        FROM bookings b
        JOIN users u ON b.user_id = u.user_id
        JOIN vehicles v ON b.vehicle_id = v.vehicle_id
        LEFT JOIN payments p ON b.booking_id = p.booking_id
        ORDER BY b.booking_id DESC
    """)

    payments = query_db("""
        SELECT p.*, b.user_id, u.name as customer_name, u.email, v.brand, v.model, v.vehicle_type
        FROM payments p
        JOIN bookings b ON p.booking_id = b.booking_id
        JOIN users u ON b.user_id = u.user_id
        JOIN vehicles v ON b.vehicle_id = v.vehicle_id
        ORDER BY p.payment_id DESC
    """)

    reviews = query_db("""
        SELECT r.*, u.name as customer_name, u.email as customer_email,
               v.brand, v.model, v.vehicle_type
        FROM reviews r
        JOIN users u ON r.user_id = u.user_id
        JOIN vehicles v ON r.vehicle_id = v.vehicle_id
        ORDER BY r.review_id DESC
    """)

    return render_template(
        'admin/dashboard.html',
        insights={
            'total_users': total_users,
            'total_vehicles': total_vehicles,
            'cars_count': cars_count,
            'bikes_count': bikes_count,
            'available_count': available_count,
            'rented_count': rented_count,
            'maintenance_count': maintenance_count,
            'total_bookings': total_bookings,
            'pending_bookings': pending_bookings,
            'confirmed_bookings': confirmed_bookings,
            'completed_bookings': completed_bookings,
            'cancelled_bookings': cancelled_bookings,
            'total_revenue': total_revenue,
            'total_deposits': total_deposits,
            'net_rental_earnings': net_rental_earnings,
            'total_reviews': total_reviews,
            'avg_rating': avg_rating,
            'top_vehicles': top_vehicles
        },
        vehicles=vehicles,
        bookings=bookings,
        payments=payments,
        reviews=reviews
    )

@app.route('/admin/vehicles')
@admin_required
def admin_vehicles():
    vehicles = query_db("""
        SELECT v.*, vt.type_name,
               (SELECT image_url FROM vehicle_images vi WHERE vi.vehicle_id = v.vehicle_id LIMIT 1) AS primary_image
        FROM vehicles v
        JOIN vehicle_types vt ON v.type_id = vt.type_id
        ORDER BY v.vehicle_id DESC
    """)
    return render_template('admin/vehicles.html', vehicles=vehicles)

@app.route('/admin/vehicles/add', methods=['GET', 'POST'])
@admin_required
def admin_add_vehicle():
    if request.method == 'POST':
        brand = request.form.get('brand', '').strip()
        model = request.form.get('model', '').strip()
        type_id = request.form.get('type_id', type=int)
        fuel_type = request.form.get('fuel_type', '').strip()
        seating_capacity = request.form.get('seating_capacity', type=int) or 2
        price_per_day = request.form.get('price_per_day', type=float)
        status = request.form.get('status', 'Available')
        image_url = request.form.get('image_url', '').strip()

        vt = query_db("SELECT type_name FROM vehicle_types WHERE type_id = %s", (type_id,), one=True)
        vehicle_type = vt['type_name'] if vt else 'Car'

        vehicle_id = execute_db(
            """
            INSERT INTO vehicles (type_id, brand, model, vehicle_type, fuel_type, seating_capacity, price_per_day, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (type_id, brand, model, vehicle_type, fuel_type, seating_capacity, price_per_day, status)
        )

        if image_url:
            execute_db("INSERT INTO vehicle_images (vehicle_id, image_url) VALUES (%s, %s)", (vehicle_id, image_url))
        else:
            default_img = "https://images.unsplash.com/photo-1549399542-7e3f8b79c341?auto=format&fit=crop&w=800&q=80"
            execute_db("INSERT INTO vehicle_images (vehicle_id, image_url) VALUES (%s, %s)", (vehicle_id, default_img))

        flash(f"Vehicle '{brand} {model}' added successfully!", "success")
        return redirect(url_for('admin_vehicles'))

    return render_template('admin/vehicle_form.html', vehicle=None)

@app.route('/admin/vehicles/edit/<int:vehicle_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_vehicle(vehicle_id):
    vehicle = query_db("SELECT * FROM vehicles WHERE vehicle_id = %s", (vehicle_id,), one=True)
    if not vehicle:
        flash("Vehicle not found.", "danger")
        return redirect(url_for('admin_vehicles'))

    primary_image = query_db("SELECT image_url FROM vehicle_images WHERE vehicle_id = %s LIMIT 1", (vehicle_id,), one=True)
    current_image_url = primary_image['image_url'] if primary_image else ""

    if request.method == 'POST':
        brand = request.form.get('brand', '').strip()
        model = request.form.get('model', '').strip()
        type_id = request.form.get('type_id', type=int)
        fuel_type = request.form.get('fuel_type', '').strip()
        seating_capacity = request.form.get('seating_capacity', type=int) or 2
        price_per_day = request.form.get('price_per_day', type=float)
        status = request.form.get('status', 'Available')
        image_url = request.form.get('image_url', '').strip()

        vt = query_db("SELECT type_name FROM vehicle_types WHERE type_id = %s", (type_id,), one=True)
        vehicle_type = vt['type_name'] if vt else 'Car'

        execute_db(
            """
            UPDATE vehicles
            SET type_id = %s, brand = %s, model = %s, vehicle_type = %s,
                fuel_type = %s, seating_capacity = %s, price_per_day = %s, status = %s
            WHERE vehicle_id = %s
            """,
            (type_id, brand, model, vehicle_type, fuel_type, seating_capacity, price_per_day, status, vehicle_id)
        )

        if image_url:
            if primary_image:
                execute_db("UPDATE vehicle_images SET image_url = %s WHERE vehicle_id = %s LIMIT 1", (image_url, vehicle_id))
            else:
                execute_db("INSERT INTO vehicle_images (vehicle_id, image_url) VALUES (%s, %s)", (vehicle_id, image_url))

        flash(f"Vehicle '{brand} {model}' updated successfully!", "success")
        return redirect(url_for('admin_vehicles'))

    return render_template('admin/vehicle_form.html', vehicle=vehicle, current_image_url=current_image_url)

@app.route('/admin/vehicles/delete/<int:vehicle_id>', methods=['POST'])
@admin_required
def admin_delete_vehicle(vehicle_id):
    execute_db("DELETE FROM vehicles WHERE vehicle_id = %s", (vehicle_id,))
    flash("Vehicle deleted successfully.", "info")
    return redirect(url_for('admin_vehicles'))

@app.route('/admin/bookings')
@admin_required
def admin_bookings():
    bookings = query_db("""
        SELECT b.*, u.name as customer_name, u.phone, u.email, v.brand, v.model, v.vehicle_type,
               p.payment_status, p.payment_method, p.transaction_id
        FROM bookings b
        JOIN users u ON b.user_id = u.user_id
        JOIN vehicles v ON b.vehicle_id = v.vehicle_id
        LEFT JOIN payments p ON b.booking_id = p.booking_id
        ORDER BY b.booking_id DESC
    """)
    return render_template('admin/bookings.html', bookings=bookings)

@app.route('/admin/bookings/update-status/<int:booking_id>', methods=['POST'])
@admin_required
def admin_update_booking_status(booking_id):
    new_status = request.form.get('booking_status')
    if new_status in ['Pending', 'Confirmed', 'Completed', 'Cancelled']:
        execute_db("UPDATE bookings SET booking_status = %s WHERE booking_id = %s", (new_status, booking_id))
        
        # If completed or cancelled, free the vehicle
        if new_status in ['Completed', 'Cancelled']:
            booking = query_db("SELECT vehicle_id FROM bookings WHERE booking_id = %s", (booking_id,), one=True)
            if booking:
                execute_db("UPDATE vehicles SET status = 'Available' WHERE vehicle_id = %s", (booking['vehicle_id'],))
        elif new_status == 'Confirmed':
            booking = query_db("SELECT vehicle_id FROM bookings WHERE booking_id = %s", (booking_id,), one=True)
            if booking:
                execute_db("UPDATE vehicles SET status = 'Rented' WHERE vehicle_id = %s", (booking['vehicle_id'],))

        flash(f"Booking #{booking_id} status updated to {new_status}.", "success")
    return redirect(url_for('admin_bookings'))

@app.route('/admin/payments')
@admin_required
def admin_payments():
    payments = query_db("""
        SELECT p.*, b.user_id, u.name as customer_name, u.email, v.brand, v.model
        FROM payments p
        JOIN bookings b ON p.booking_id = b.booking_id
        JOIN users u ON b.user_id = u.user_id
        JOIN vehicles v ON b.vehicle_id = v.vehicle_id
        ORDER BY p.payment_id DESC
    """)
    return render_template('admin/payments.html', payments=payments)

@app.route('/admin/reviews')
@admin_required
def admin_reviews():
    reviews = query_db("""
        SELECT r.*, u.name as customer_name, u.email as customer_email,
               v.brand, v.model, v.vehicle_type
        FROM reviews r
        JOIN users u ON r.user_id = u.user_id
        JOIN vehicles v ON r.vehicle_id = v.vehicle_id
        ORDER BY r.review_id DESC
    """)
    return render_template('admin/reviews.html', reviews=reviews)

@app.route('/admin/reviews/delete/<int:review_id>', methods=['POST'])
@admin_required
def admin_delete_review(review_id):
    execute_db("DELETE FROM reviews WHERE review_id = %s", (review_id,))
    flash(f"Review #{review_id} has been removed successfully.", "info")
    return redirect(request.referrer or url_for('admin_dashboard'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
