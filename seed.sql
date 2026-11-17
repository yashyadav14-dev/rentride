-- ==========================================================
-- Sample Seed Data for Car & Bike Rental Service
-- Default admin credentials: admin@rental.com / admin123
-- Default customer credentials: john@example.com / customer123
-- ==========================================================

USE rental_db;

-- 1. Insert Vehicle Types
INSERT INTO vehicle_types (type_id, type_name, description) VALUES
(1, 'Car', 'Comfortable 4 to 7-seater cars suited for city trips, family vacations, and long drives.'),
(2, 'Bike', 'Fuel-efficient, agile two-wheelers and high-performance motorbikes for daily commutes and road adventures.')
ON DUPLICATE KEY UPDATE type_name=VALUES(type_name);

-- 2. Insert Users (Admin & Customers)
-- Note: Passwords below are Werkzeug scrypt/pbkdf2 hashes or raw setup via init_db.py
-- For direct SQL import, these hashes match:
-- admin@rental.com -> admin123
-- john@example.com -> customer123
INSERT INTO users (user_id, name, email, password, phone, address, license_no, role) VALUES
(1, 'Admin Manager', 'admin@rental.com', 'scrypt:32768:8:1$hU9zR4c5T2!$f7e6f8f5c8c5c7d8a6b5e4d3c2b1a09876543210fedcba9876543210abcdef01', '+1 555-0100', '100 Rental Plaza, Downtown', 'DL-ADMIN-9999', 'admin'),
(2, 'John Doe', 'john@example.com', 'scrypt:32768:8:1$hU9zR4c5T2!$f7e6f8f5c8c5c7d8a6b5e4d3c2b1a09876543210fedcba9876543210abcdef01', '+1 555-0199', '42 Elm Street, Cityville', 'DL-US-2024-8841', 'customer'),
(3, 'Sarah Connor', 'sarah@example.com', 'scrypt:32768:8:1$hU9zR4c5T2!$f7e6f8f5c8c5c7d8a6b5e4d3c2b1a09876543210fedcba9876543210abcdef01', '+1 555-0245', '77 Sunset Boulevard', 'DL-CA-2023-1123', 'customer')
ON DUPLICATE KEY UPDATE name=VALUES(name);

-- 3. Insert Vehicles (Prices in INR ₹ per day)
INSERT INTO vehicles (vehicle_id, type_id, brand, model, vehicle_type, fuel_type, seating_capacity, price_per_day, status) VALUES
(1, 1, 'Hyundai', 'Creta SX (O)', 'Car', 'Diesel', 5, 2500.00, 'Available'),
(2, 1, 'Toyota', 'Fortuner 4x4', 'Car', 'Diesel', 7, 5500.00, 'Available'),
(3, 1, 'Honda', 'City i-VTEC', 'Car', 'Petrol', 5, 2200.00, 'Available'),
(4, 1, 'Tesla', 'Model 3 Long Range', 'Car', 'Electric', 5, 6000.00, 'Available'),
(5, 2, 'Royal Enfield', 'Classic 350', 'Bike', 'Petrol', 2, 1200.00, 'Available'),
(6, 2, 'Yamaha', 'YZF R15 V4', 'Bike', 'Petrol', 2, 1400.00, 'Available'),
(7, 2, 'KTM', 'Duke 390', 'Bike', 'Petrol', 2, 1800.00, 'Available'),
(8, 2, 'Honda', 'Activa 6G', 'Bike', 'Petrol', 2, 600.00, 'Available')
ON DUPLICATE KEY UPDATE brand=VALUES(brand);

-- 4. Insert Vehicle Images
INSERT INTO vehicle_images (image_id, vehicle_id, image_url) VALUES
(1, 1, 'https://images.unsplash.com/photo-1549399542-7e3f8b79c341?auto=format&fit=crop&w=800&q=80'),
(2, 1, 'https://images.unsplash.com/photo-1552519507-da3b142c6e3d?auto=format&fit=crop&w=800&q=80'),
(3, 2, 'https://images.unsplash.com/photo-1533473359331-0135ef1b58bf?auto=format&fit=crop&w=800&q=80'),
(4, 3, 'https://images.unsplash.com/photo-1590362891991-f776e747a588?auto=format&fit=crop&w=800&q=80'),
(5, 4, 'https://images.unsplash.com/photo-1560958089-b8a1929cea89?auto=format&fit=crop&w=800&q=80'),
(6, 5, 'https://images.unsplash.com/photo-1558981403-c5f9899a28bc?auto=format&fit=crop&w=800&q=80'),
(7, 6, 'https://images.unsplash.com/photo-1568772585407-9361f9bf3a87?auto=format&fit=crop&w=800&q=80'),
(8, 7, 'https://images.unsplash.com/photo-1609630875171-b1321377ee65?auto=format&fit=crop&w=800&q=80'),
(9, 8, 'https://images.unsplash.com/photo-1571188654248-7a89213915f7?auto=format&fit=crop&w=800&q=80')
ON DUPLICATE KEY UPDATE image_url=VALUES(image_url);

-- 5. Insert Sample Bookings (Fixed Sanghvi pickup with refundable deposit in ₹)
INSERT INTO bookings (booking_id, user_id, vehicle_id, pickup_date, return_date, pickup_location, return_location, total_days, rental_price, deposit_amount, total_price, damage_agreement_accepted, booking_status) VALUES
(1, 2, 1, '2026-11-20', '2026-11-23', 'Sanghvi', 'Sanghvi', 3, 7500.00, 3000.00, 10500.00, 1, 'Confirmed'),
(2, 3, 5, '2026-11-25', '2026-11-27', 'Sanghvi', 'Sanghvi', 2, 2400.00, 1500.00, 3900.00, 1, 'Confirmed')
ON DUPLICATE KEY UPDATE booking_status=VALUES(booking_status);

-- 6. Insert Payments
INSERT INTO payments (payment_id, booking_id, amount, payment_method, payment_status, payment_date, transaction_id) VALUES
(1, 1, 10500.00, 'Credit Card', 'Paid', '2026-11-15 10:30:00', 'TXN-9843217684'),
(2, 2, 3900.00, 'UPI', 'Paid', '2026-11-16 14:15:00', 'TXN-5544112233')
ON DUPLICATE KEY UPDATE amount=VALUES(amount);

-- 7. Insert Reviews
INSERT INTO reviews (review_id, user_id, vehicle_id, rating, comment, review_date) VALUES
(1, 2, 1, 5, 'The Hyundai Creta was in pristine condition! Fuel efficiency was great and pickup was seamless.', '2026-11-10 12:00:00'),
(2, 3, 5, 5, 'Riding the Royal Enfield Classic 350 along the highway was an incredible experience. Smooth engine!', '2026-11-12 16:20:00'),
(3, 2, 4, 4, 'Tesla Model 3 has insane acceleration and autopilot features. Supercharging stations were easy to find.', '2026-11-14 09:45:00')
ON DUPLICATE KEY UPDATE rating=VALUES(rating);
