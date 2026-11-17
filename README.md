# RentRide - Car & Bike Rental Service Web Application

A full-stack vehicle rental management web application built with **Python Flask**, **MySQL**, and modern **HTML5 / CSS3 / JavaScript**, strictly matching the provided **ER Diagram**.

---

## 📌 ER Diagram Mapping to Database Schema

| Entity | Attributes | Role / Relations |
| :--- | :--- | :--- |
| **`USERS`** | `user_id` (PK), `name`, `email`, `password`, `phone`, `address`, `license_no`, `role` | Makes Bookings (1:M), Writes Reviews (1:M) |
| **`VEHICLE_TYPES`** | `type_id` (PK), `type_name` (Car/Bike), `description` | Belongs to Vehicles (1:M) |
| **`VEHICLES`** | `vehicle_id` (PK), `type_id` (FK), `brand`, `model`, `vehicle_type`, `fuel_type`, `seating_capacity`, `price_per_day`, `status` | Booked in Bookings (1:M), Has Images (1:M), Receives Reviews (1:M) |
| **`VEHICLE_IMAGES`** | `image_id` (PK), `vehicle_id` (FK), `image_url` | Vehicle Gallery Images |
| **`BOOKINGS`** | `booking_id` (PK), `user_id` (FK), `vehicle_id` (FK), `pickup_date`, `return_date`, `pickup_location`, `return_location`, `booking_status`, `total_price` | Generates Payments (1:M / 1:1) |
| **`PAYMENTS`** | `payment_id` (PK), `booking_id` (FK), `amount`, `payment_method`, `payment_status`, `payment_date`, `transaction_id` | Receives checkout payment for bookings |
| **`REVIEWS`** | `review_id` (PK), `user_id` (FK), `vehicle_id` (FK), `rating` (1-5), `comment`, `review_date` | Customer vehicle reviews & ratings |

---

## 🚀 Key Features

### 👤 Customer Features
1. **User Authentication & Profile**: Register, Login, Profile with Driving License verification.
2. **Fixed Pickup Hub (`Sanghvi`)**: All vehicle handovers and initial inspection happen at the dedicated **Sanghvi** center.
3. **Refundable Security Deposit**: Standard refundable deposit (₹3,000 for Cars, ₹1,500 for Bikes) added to reservation and refunded after safe handover inspection.
4. **Damage Liability Agreement**: Legal damage responsibility clause agreed by customer during booking, declaring customer accountability for any damage or repairs.
5. **Indian Localization**: Dates formatted in Indian standard (`DD/MM/YYYY`), and pricing in Indian Rupees (`₹ INR`).
6. **Catalog & Filtering**: Browse Cars and Bikes, live filter by category, brand, fuel type, and price range.
7. **Vehicle Details & Image Gallery**: High-res gallery preview, detailed specs, customer reviews.
8. **Reservation & Calculator**: Live calculation of rental duration (days), rental subtotal, security deposit, and total cost in ₹.
9. **Secure Payment Checkout**: Simulated payment gateway with Credit Card, Debit Card, UPI, and Net Banking options.
10. **My Bookings Dashboard**: Track reservation statuses (`Pending`, `Confirmed`, `Completed`, `Cancelled`), printable official PDF/invoice receipt with damage clause and signature line.
11. **Customer Reviews**: Leave star ratings (1 to 5) and feedback on rented vehicles.

### 🛡️ Admin Command Dashboard (`/admin`)
1. **Insights & Visual Analytics**:
   - Total Gross Revenue, Net Rental Earnings vs Refundable Security Deposits held.
   - Total Bookings breakdown (Pending, Confirmed, Completed, Cancelled).
   - Real-time Fleet Utilization ratio (% ready vs % rented), Cars vs Bikes mix.
   - Customer Satisfaction Score (average stars out of 5) and review volume.
   - Top 5 Most Rented Vehicles leaderboard.
2. **Edit & Manage Vehicles**:
   - View, search, and edit any vehicle (`brand`, `model`, `type`, `fuel_type`, `seats`, `price_per_day`, `status`, image URL).
   - Add new vehicle and delete records with instant database synchronization.
3. **Bookings Management**:
   - Track all customer reservations, contact info, driving license numbers, and Sanghvi fixed pickup compliance.
   - Real-time lifecycle status updater (`Pending` &rarr; `Confirmed` &rarr; `Completed` &rarr; `Cancelled`).
   - Automatically releases vehicle back to `Available` upon completion/cancellation.
4. **Payments Ledger**:
   - Audit all financial transactions, transaction IDs, payment methods (Card, UPI, Debit, Net Banking), and timestamps.
5. **Customer Reviews Moderation**:
   - Read verified user feedback, rating stars, and moderate/delete inappropriate reviews.

---

## 📁 Project Structure

```
car_bike_rental/
├── app.py                     # Main Flask routes and controllers
├── config.py                  # Database & session configuration
├── db.py                      # MySQL connection and query helpers
├── schema.sql                 # MySQL DDL table schema
├── seed.sql                   # Sample seed data
├── init_db.py                 # Automatic DB creator and data seeder
├── requirements.txt           # Python library dependencies
├── .env.example               # Environment variables template
├── static/
│   ├── css/
│   │   └── style.css          # Modern, responsive stylesheet
│   └── js/
│       └── main.js           # Dynamic date & total price calculator, gallery & invoice logic
└── templates/
    ├── base.html              # Layout shell with navigation & footer
    ├── index.html             # Landing page
    ├── vehicles.html          # Vehicle catalog with search & filters
    ├── vehicle_detail.html    # Vehicle specs, gallery & reviews
    ├── book.html              # Booking reservation form
    ├── payment.html           # Payment checkout page
    ├── my_bookings.html       # Customer bookings & invoice print
    ├── profile.html           # User profile & driving license
    ├── login.html             # Sign in
    ├── register.html          # Registration
    └── admin/
        ├── dashboard.html     # Admin stats & recent activity
        ├── vehicles.html      # Manage vehicles
        ├── vehicle_form.html  # Add / Edit vehicle
        ├── bookings.html      # Manage all customer bookings
        └── payments.html      # Payment transaction records
```

---

## ⚙️ Installation & Setup

### 1. Prerequisites
- Python 3.8+
- MySQL Server (Local MySQL, XAMPP, WampServer, or Docker)

### 2. Configure Database Credentials
Create a `.env` file in the project folder (or copy from `.env.example`):
```ini
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password_here
MYSQL_DB=rental_db
SECRET_KEY=car-bike-rental-super-secret-key-2026
```

### 3. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 4. Initialize Database
Run the automated initialization script:
```bash
python init_db.py
```
*This creates the `rental_db` database, generates all tables from `schema.sql`, and populates sample cars, motorbikes, users, images, and reviews.*

### 5. Run the Application
```bash
python app.py
```
Open your web browser and visit:
👉 **`http://localhost:5000`**

---

## 🔑 Default Accounts

| Role | Email | Password |
| :--- | :--- | :--- |
| **Admin** | `admin@rental.com` | `admin123` |
| **Customer** | `john@example.com` | `customer123` |
