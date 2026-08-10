-- Extremeclean Carwash Nairobi - Database Schema
CREATE DATABASE IF NOT EXISTS extremeclean_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE extremeclean_db;

-- Customers Table
CREATE TABLE IF NOT EXISTS customers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(20) NOT NULL UNIQUE,
    email VARCHAR(100),
    vehicle_reg VARCHAR(20),
    vehicle_type VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_visits INT DEFAULT 0
);

-- Services Table
CREATE TABLE IF NOT EXISTS services (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    price DECIMAL(10,2) NOT NULL,
    duration_minutes INT NOT NULL,
    category VARCHAR(50) DEFAULT 'standard',
    is_active BOOLEAN DEFAULT TRUE
);

-- Employees Table
CREATE TABLE IF NOT EXISTS employees (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    role VARCHAR(50) NOT NULL,
    status ENUM('active','off_duty','on_leave') DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Bookings Table
CREATE TABLE IF NOT EXISTS bookings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    service_id INT NOT NULL,
    employee_id INT,
    booking_date DATE NOT NULL,
    booking_time TIME NOT NULL,
    status ENUM('pending','confirmed','in_progress','completed','cancelled') DEFAULT 'pending',
    vehicle_reg VARCHAR(20),
    notes TEXT,
    total_price DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    FOREIGN KEY (service_id) REFERENCES services(id),
    FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE SET NULL
);

-- Notifications Table
CREATE TABLE IF NOT EXISTS notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT,
    booking_id INT,
    type ENUM('booking_confirmed','service_started','service_completed','reminder','promotional') NOT NULL,
    message TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
    FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE CASCADE
);

-- Tasks Table
CREATE TABLE IF NOT EXISTS tasks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    booking_id INT,
    employee_id INT,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    status ENUM('pending','in_progress','completed') DEFAULT 'pending',
    priority ENUM('low','medium','high') DEFAULT 'medium',
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE CASCADE,
    FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE SET NULL
);

-- Users/Admin Table
-- Uses user_id (not id) to avoid any MySQL reserved word conflicts
DROP TABLE IF EXISTS users;
CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('admin','manager','staff') DEFAULT 'staff',
    employee_id INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE SET NULL
);

-- Seed Services
INSERT IGNORE INTO services (name, description, price, duration_minutes, category) VALUES
('Basic Wash', 'Exterior rinse and hand wash', 500, 20, 'basic'),
('Full Wash', 'Exterior + interior vacuum and wipe', 900, 40, 'standard'),
('Premium Detail', 'Full wash + polish + wax coating', 1800, 90, 'premium'),
('Engine Clean', 'Engine bay degreasing and rinse', 1200, 45, 'specialty'),
('Interior Deep Clean', 'Full interior steam clean and shampoo', 1500, 60, 'premium'),
('Quick Rinse', 'Fast exterior spray rinse', 300, 10, 'basic');

-- Seed Employees
INSERT IGNORE INTO employees (name, phone, role, status) VALUES
('James Mwangi', '0712345678', 'Senior Washer', 'active'),
('Grace Wanjiru', '0723456789', 'Detailer', 'active'),
('Peter Kamau', '0734567890', 'Washer', 'active'),
('Alice Njeri', '0745678901', 'Manager', 'active');

-- Seed Admin User (password: admin123)
-- password_hash is SHA256 of "admin123" + secret key fallback handled in app.py
INSERT INTO users (username, password_hash, role) VALUES
('admin', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQyCgRXFNSXMDkr5bnxFn6QhW', 'admin');

-- Seed sample customers
INSERT IGNORE INTO customers (name, phone, email, vehicle_reg, vehicle_type) VALUES
('John Doe', '0700111222', 'john@example.com', 'KCA 123A', 'Sedan'),
('Mary Wambui', '0700333444', 'mary@example.com', 'KDB 456B', 'SUV'),
('David Otieno', '0700555666', 'david@example.com', 'KBC 789C', 'Pickup');
