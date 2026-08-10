#!/usr/bin/env python3
"""
Extremeclean Carwash Nairobi - Management System
Pure Python + MySQL, no frameworks
"""

import json
import hashlib
import hmac
import os
import re
import uuid
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, unquote
from datetime import datetime, date, timedelta
from db import execute_query, execute_many
from sms import (sms_booking_received, sms_booking_confirmed,
                 sms_service_started, sms_service_completed,
                 sms_booking_cancelled, sms_booking_reminder)
import traceback

# Simple session store (in-memory for demo; use Redis in production)
SESSIONS = {}
SECRET_KEY = os.environ.get('SECRET_KEY', 'extremeclean-secret-2024')


def hash_password(password):
    return hashlib.sha256((password + SECRET_KEY).encode()).hexdigest()

def verify_password(password, hashed):
    return hash_password(password) == hashed

def create_session(user_id, role):
    token = str(uuid.uuid4())
    SESSIONS[token] = {'user_id': user_id, 'role': role, 'created': datetime.now().isoformat()}
    return token

def get_session(token):
    return SESSIONS.get(token)

def destroy_session(token):
    SESSIONS.pop(token, None)


def json_response(data, status=200):
    body = json.dumps(data, default=str).encode('utf-8')
    return status, body, 'application/json'

def error_response(message, status=400):
    return json_response({'success': False, 'error': message}, status)

def success_response(data=None, message='OK'):
    resp = {'success': True, 'message': message}
    if data is not None:
        resp['data'] = data
    return json_response(resp)


# ── API Handlers ──────────────────────────────────────────────────────────────

def handle_login(body, headers):
    try:
        data = json.loads(body)
        username = data.get('username', '').strip()
        password = data.get('password', '')
        if not username or not password:
            return error_response('Username and password required')

        user = execute_query(
            "SELECT user_id, username, password_hash, role FROM users WHERE username=%s",
            (username,), fetchone=True
        )
        if not user:
            return error_response('Invalid credentials', 401)

        # Support sha256 hash OR the hardcoded bcrypt placeholder from SQL seed
        pwd_hash = hash_password(password)
        is_bcrypt_placeholder = user['password_hash'].startswith('$2b$')
        valid = (pwd_hash == user['password_hash']) or \
                (is_bcrypt_placeholder and password == 'admin123' and username == 'admin')
        if not valid:
            return error_response('Invalid credentials', 401)

        token = create_session(user['user_id'], user['role'])
        return success_response({'token': token, 'role': user['role'], 'username': user['username']}, 'Login successful')
    except Exception as e:
        return error_response(str(e), 500)



def handle_change_password(body, session):
    try:
        if not session:
            return error_response('Not authenticated', 401)
        data = json.loads(body)
        old_pass = data.get('old_password', '')
        new_pass = data.get('new_password', '')
        if not old_pass or not new_pass:
            return error_response('Both old and new password required')
        if len(new_pass) < 6:
            return error_response('Password must be at least 6 characters')

        user = execute_query(
            "SELECT user_id, password_hash FROM users WHERE user_id=%s",
            (session['user_id'],), fetchone=True)
        if not user:
            return error_response('User not found', 404)

        # Verify old password
        old_hash = hash_password(old_pass)
        is_bcrypt = user['password_hash'].startswith('$2b$')
        valid = (old_hash == user['password_hash']) or (is_bcrypt and old_pass == 'admin123')
        if not valid:
            return error_response('Current password is incorrect', 401)

        new_hash = hash_password(new_pass)
        execute_query(
            "UPDATE users SET password_hash=%s WHERE user_id=%s",
            (new_hash, session['user_id']), commit=True)
        return success_response(message='Password changed successfully')
    except Exception as e:
        return error_response(str(e), 500)


def handle_test_sms(body):
    try:
        from sms import send_sms
        data = json.loads(body)
        phone = data.get('phone', '')
        if not phone:
            return error_response('Phone number required')
        result = send_sms(phone,
            'Test SMS from Extremeclean Carwash Management System. Your SMS integration is working!')
        if result.get('success'):
            return success_response(message='Test SMS sent successfully')
        else:
            return error_response(result.get('error', 'SMS failed — check AT credentials in env vars'))
    except Exception as e:
        return error_response(str(e), 500)

def handle_logout(body, headers, session):
    token = headers.get('Authorization', '').replace('Bearer ', '')
    destroy_session(token)
    return success_response(message='Logged out')


# ── Dashboard ─────────────────────────────────────────────────────────────────

def handle_dashboard_stats(session):
    try:
        today = date.today().isoformat()
        stats = {}

        stats['total_bookings_today'] = (execute_query(
            "SELECT COUNT(*) as c FROM bookings WHERE booking_date=%s", (today,), fetchone=True) or {}).get('c', 0)

        stats['completed_today'] = (execute_query(
            "SELECT COUNT(*) as c FROM bookings WHERE booking_date=%s AND status='completed'", (today,), fetchone=True) or {}).get('c', 0)

        stats['in_progress'] = (execute_query(
            "SELECT COUNT(*) as c FROM bookings WHERE status='in_progress'", fetchone=True) or {}).get('c', 0)

        stats['pending'] = (execute_query(
            "SELECT COUNT(*) as c FROM bookings WHERE status='pending'", fetchone=True) or {}).get('c', 0)

        stats['total_customers'] = (execute_query(
            "SELECT COUNT(*) as c FROM customers", fetchone=True) or {}).get('c', 0)

        stats['active_employees'] = (execute_query(
            "SELECT COUNT(*) as c FROM employees WHERE status='active'", fetchone=True) or {}).get('c', 0)

        revenue = execute_query(
            "SELECT COALESCE(SUM(total_price),0) as rev FROM bookings WHERE booking_date=%s AND status='completed'",
            (today,), fetchone=True)
        stats['revenue_today'] = float(revenue['rev']) if revenue else 0

        # Recent bookings
        recent = execute_query("""
            SELECT b.id, c.name as customer, s.name as service, b.booking_time,
                   b.status, b.vehicle_reg, b.total_price,
                   COALESCE(e.name,'Unassigned') as employee
            FROM bookings b
            JOIN customers c ON b.customer_id=c.id
            JOIN services s ON b.service_id=s.id
            LEFT JOIN employees e ON b.employee_id=e.id
            WHERE b.booking_date=%s
            ORDER BY b.booking_time ASC LIMIT 10
        """, (today,), fetchall=True)

        stats['recent_bookings'] = recent or []

        # Unread notifications count
        notif_count = execute_query(
            "SELECT COUNT(*) as c FROM notifications WHERE is_read=0", fetchone=True)
        stats['unread_notifications'] = (notif_count or {}).get('c', 0)

        return success_response(stats)
    except Exception as e:
        traceback.print_exc()
        return error_response(str(e), 500)


# ── Bookings ──────────────────────────────────────────────────────────────────

def handle_get_bookings(params):
    try:
        filters = []
        args = []
        status = params.get('status', [None])[0]
        date_filter = params.get('date', [None])[0]
        search = params.get('search', [None])[0]

        if status:
            filters.append("b.status=%s")
            args.append(status)
        if date_filter:
            filters.append("b.booking_date=%s")
            args.append(date_filter)
        if search:
            filters.append("(c.name LIKE %s OR c.phone LIKE %s OR b.vehicle_reg LIKE %s)")
            args += [f'%{search}%', f'%{search}%', f'%{search}%']

        where = ("WHERE " + " AND ".join(filters)) if filters else ""

        bookings = execute_query(f"""
            SELECT b.id, b.booking_date, b.booking_time, b.status, b.vehicle_reg,
                   b.total_price, b.notes,
                   c.name as customer_name, c.phone as customer_phone,
                   s.name as service_name, s.duration_minutes,
                   COALESCE(e.name,'Unassigned') as employee_name
            FROM bookings b
            JOIN customers c ON b.customer_id=c.id
            JOIN services s ON b.service_id=s.id
            LEFT JOIN employees e ON b.employee_id=e.id
            {where}
            ORDER BY b.booking_date DESC, b.booking_time ASC
            LIMIT 100
        """, args if args else None, fetchall=True)

        return success_response(bookings or [])
    except Exception as e:
        traceback.print_exc()
        return error_response(str(e), 500)


def handle_create_booking(body, is_customer_portal=False):
    try:
        data = json.loads(body)
        required = ['customer_id','service_id','booking_date','booking_time']
        for f in required:
            if not data.get(f):
                return error_response(f'Field {f} is required')

        service = execute_query("SELECT price, name FROM services WHERE id=%s", (data['service_id'],), fetchone=True)
        if not service:
            return error_response('Service not found')

        # Customer portal bookings start as 'pending', admin bookings as 'pending' too
        booking_id = execute_query("""
            INSERT INTO bookings (customer_id, service_id, employee_id, booking_date, booking_time,
                                  vehicle_reg, notes, total_price, status)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'pending')
        """, (
            data['customer_id'], data['service_id'],
            data.get('employee_id') or None,
            data['booking_date'], data['booking_time'],
            data.get('vehicle_reg',''), data.get('notes',''),
            service['price']
        ), commit=True)

        # Auto-create task for assigned employee
        if data.get('employee_id'):
            execute_query("""
                INSERT INTO tasks (booking_id, employee_id, title, description, status, priority)
                VALUES (%s,%s,%s,%s,'pending','medium')
            """, (booking_id, data['employee_id'],
                  f"Carwash: {service['name']}",
                  f"Vehicle: {data.get('vehicle_reg','N/A')} | Date: {data['booking_date']} {data['booking_time']}"),
                commit=True)

        # Get customer info for notifications
        customer = execute_query(
            "SELECT name, phone FROM customers WHERE id=%s", (data['customer_id'],), fetchone=True)

        if customer:
            # In-app notification
            execute_query("""
                INSERT INTO notifications (customer_id, booking_id, type, message)
                VALUES (%s,%s,'booking_confirmed',%s)
            """, (data['customer_id'], booking_id,
                  f"Booking #{booking_id} for {service['name']} on {data['booking_date']} "
                  f"at {data['booking_time']} received successfully!"),
                commit=True)

            # SMS notification via Africa's Talking
            if customer.get('phone'):
                sms_booking_received(
                    customer_name=customer['name'],
                    service=service['name'],
                    booking_date=data['booking_date'],
                    booking_time=data['booking_time'],
                    booking_id=booking_id,
                    phone=customer['phone']
                )

        return success_response({'booking_id': booking_id}, 'Booking created successfully')
    except Exception as e:
        traceback.print_exc()
        return error_response(str(e), 500)


def handle_update_booking_status(booking_id, body):
    try:
        data = json.loads(body)
        new_status = data.get('status')
        valid = ['pending','confirmed','in_progress','completed','cancelled']
        if new_status not in valid:
            return error_response('Invalid status')

        execute_query(
            "UPDATE bookings SET status=%s WHERE id=%s",
            (new_status, booking_id), commit=True)

        # Get full booking info for notifications
        booking = execute_query("""
            SELECT b.customer_id, b.vehicle_reg, b.booking_date, b.booking_time,
                   b.total_price, c.name, c.phone, s.name as svc
            FROM bookings b
            JOIN customers c ON b.customer_id=c.id
            JOIN services s ON b.service_id=s.id
            WHERE b.id=%s
        """, (booking_id,), fetchone=True)

        if booking:
            vehicle = booking.get('vehicle_reg') or 'your vehicle'
            price = float(booking.get('total_price') or 0)

            # In-app notification messages
            notif_msgs = {
                'confirmed':   f"Booking #{booking_id} for {booking['svc']} is CONFIRMED! See you on {booking['booking_date']}.",
                'in_progress': f"Your {booking['svc']} for {vehicle} has STARTED. Our team is on it!",
                'completed':   f"Your {booking['svc']} for {vehicle} is DONE! Total: KES {price:,.0f}. Thank you!",
                'cancelled':   f"Booking #{booking_id} for {booking['svc']} has been cancelled."
            }
            notif_types = {
                'confirmed':   'booking_confirmed',
                'in_progress': 'service_started',
                'completed':   'service_completed',
                'cancelled':   'booking_confirmed'
            }

            if new_status in notif_msgs:
                execute_query("""
                    INSERT INTO notifications (customer_id, booking_id, type, message)
                    VALUES (%s,%s,%s,%s)
                """, (booking['customer_id'], booking_id,
                      notif_types[new_status], notif_msgs[new_status]), commit=True)

            # SMS via Africa's Talking
            phone = booking.get('phone', '')
            if phone:
                if new_status == 'confirmed':
                    sms_booking_confirmed(
                        customer_name=booking['name'], service=booking['svc'],
                        booking_date=str(booking['booking_date']),
                        booking_time=str(booking['booking_time']),
                        booking_id=booking_id, phone=phone)
                elif new_status == 'in_progress':
                    sms_service_started(
                        customer_name=booking['name'], service=booking['svc'],
                        vehicle_reg=vehicle, phone=phone)
                elif new_status == 'completed':
                    sms_service_completed(
                        customer_name=booking['name'], service=booking['svc'],
                        vehicle_reg=vehicle, price=price, phone=phone)
                elif new_status == 'cancelled':
                    sms_booking_cancelled(
                        customer_name=booking['name'], service=booking['svc'],
                        booking_id=booking_id, phone=phone)

            # Side effects on completion
            if new_status == 'completed':
                execute_query(
                    "UPDATE tasks SET status='completed', completed_at=NOW() WHERE booking_id=%s",
                    (booking_id,), commit=True)
                execute_query(
                    "UPDATE customers SET total_visits=total_visits+1 WHERE id=%s",
                    (booking['customer_id'],), commit=True)

        return success_response(message=f'Booking updated to {new_status}')
    except Exception as e:
        traceback.print_exc()
        return error_response(str(e), 500)


def handle_delete_booking(booking_id):
    try:
        execute_query("DELETE FROM bookings WHERE id=%s", (booking_id,), commit=True)
        return success_response(message='Booking deleted')
    except Exception as e:
        return error_response(str(e), 500)


# ── Customers ─────────────────────────────────────────────────────────────────

def handle_get_customers(params):
    try:
        search = params.get('search', [None])[0]
        if search:
            customers = execute_query("""
                SELECT * FROM customers WHERE name LIKE %s OR phone LIKE %s OR vehicle_reg LIKE %s
                ORDER BY created_at DESC LIMIT 50
            """, (f'%{search}%', f'%{search}%', f'%{search}%'), fetchall=True)
        else:
            customers = execute_query(
                "SELECT * FROM customers ORDER BY created_at DESC LIMIT 100", fetchall=True)
        return success_response(customers or [])
    except Exception as e:
        return error_response(str(e), 500)


def handle_create_customer(body):
    try:
        data = json.loads(body)
        if not data.get('name') or not data.get('phone'):
            return error_response('Name and phone are required')
        cid = execute_query("""
            INSERT INTO customers (name, phone, email, vehicle_reg, vehicle_type)
            VALUES (%s,%s,%s,%s,%s)
        """, (data['name'], data['phone'], data.get('email',''),
              data.get('vehicle_reg',''), data.get('vehicle_type','')), commit=True)
        return success_response({'id': cid}, 'Customer created')
    except Exception as e:
        return error_response(str(e), 500)


def handle_update_customer(cid, body):
    try:
        data = json.loads(body)
        execute_query("""
            UPDATE customers SET name=%s, phone=%s, email=%s, vehicle_reg=%s, vehicle_type=%s
            WHERE id=%s
        """, (data.get('name'), data.get('phone'), data.get('email',''),
              data.get('vehicle_reg',''), data.get('vehicle_type',''), cid), commit=True)
        return success_response(message='Customer updated')
    except Exception as e:
        return error_response(str(e), 500)


def handle_delete_customer(cid):
    try:
        execute_query("DELETE FROM customers WHERE id=%s", (cid,), commit=True)
        return success_response(message='Customer deleted')
    except Exception as e:
        return error_response(str(e), 500)


# ── Services ──────────────────────────────────────────────────────────────────

def handle_get_services():
    try:
        services = execute_query("SELECT * FROM services WHERE is_active=1 ORDER BY price ASC", fetchall=True)
        return success_response(services or [])
    except Exception as e:
        return error_response(str(e), 500)


def handle_create_service(body):
    try:
        data = json.loads(body)
        if not data.get('name') or not data.get('price'):
            return error_response('Name and price are required')
        sid = execute_query("""
            INSERT INTO services (name, description, price, duration_minutes, category)
            VALUES (%s,%s,%s,%s,%s)
        """, (data['name'], data.get('description',''), data['price'],
              data.get('duration_minutes', 30), data.get('category','standard')), commit=True)
        return success_response({'id': sid}, 'Service created')
    except Exception as e:
        return error_response(str(e), 500)


def handle_update_service(sid, body):
    try:
        data = json.loads(body)
        execute_query("""
            UPDATE services SET name=%s, description=%s, price=%s, duration_minutes=%s, category=%s
            WHERE id=%s
        """, (data['name'], data.get('description',''), data['price'],
              data.get('duration_minutes',30), data.get('category','standard'), sid), commit=True)
        return success_response(message='Service updated')
    except Exception as e:
        return error_response(str(e), 500)


def handle_delete_service(sid):
    try:
        execute_query("UPDATE services SET is_active=0 WHERE id=%s", (sid,), commit=True)
        return success_response(message='Service deactivated')
    except Exception as e:
        return error_response(str(e), 500)


# ── Employees ─────────────────────────────────────────────────────────────────

def handle_get_employees(params=None):
    try:
        employees = execute_query("""
            SELECT e.*, COUNT(t.id) as active_tasks
            FROM employees e
            LEFT JOIN tasks t ON e.id=t.employee_id AND t.status!='completed'
            GROUP BY e.id ORDER BY e.name
        """, fetchall=True)
        return success_response(employees or [])
    except Exception as e:
        return error_response(str(e), 500)


def handle_create_employee(body):
    try:
        data = json.loads(body)
        if not data.get('name') or not data.get('role'):
            return error_response('Name and role are required')
        eid = execute_query(
            "INSERT INTO employees (name, phone, role, status) VALUES (%s,%s,%s,%s)",
            (data['name'], data.get('phone',''), data['role'], data.get('status','active')),
            commit=True)
        return success_response({'id': eid}, 'Employee created')
    except Exception as e:
        return error_response(str(e), 500)


def handle_update_employee(eid, body):
    try:
        data = json.loads(body)
        execute_query("""
            UPDATE employees SET name=%s, phone=%s, role=%s, status=%s WHERE id=%s
        """, (data['name'], data.get('phone',''), data['role'], data.get('status','active'), eid),
            commit=True)
        return success_response(message='Employee updated')
    except Exception as e:
        return error_response(str(e), 500)


def handle_delete_employee(eid):
    try:
        execute_query("DELETE FROM employees WHERE id=%s", (eid,), commit=True)
        return success_response(message='Employee deleted')
    except Exception as e:
        return error_response(str(e), 500)


# ── Tasks ─────────────────────────────────────────────────────────────────────

def handle_get_tasks(params):
    try:
        emp_id = params.get('employee_id', [None])[0]
        status = params.get('status', [None])[0]
        filters, args = [], []
        if emp_id:
            filters.append("t.employee_id=%s"); args.append(emp_id)
        if status:
            filters.append("t.status=%s"); args.append(status)
        where = ("WHERE " + " AND ".join(filters)) if filters else ""
        tasks = execute_query(f"""
            SELECT t.*, e.name as employee_name,
                   COALESCE(b.vehicle_reg,'N/A') as vehicle_reg,
                   COALESCE(s.name,'N/A') as service_name
            FROM tasks t
            LEFT JOIN employees e ON t.employee_id=e.id
            LEFT JOIN bookings b ON t.booking_id=b.id
            LEFT JOIN services s ON b.service_id=s.id
            {where} ORDER BY t.assigned_at DESC LIMIT 100
        """, args if args else None, fetchall=True)
        return success_response(tasks or [])
    except Exception as e:
        traceback.print_exc()
        return error_response(str(e), 500)


def handle_update_task(tid, body):
    try:
        data = json.loads(body)
        status = data.get('status')
        completed_at = "NOW()" if status == 'completed' else "NULL"
        execute_query(f"""
            UPDATE tasks SET status=%s, completed_at={"NOW()" if status=='completed' else "NULL"}
            WHERE id=%s
        """.replace("NULL", "null"), (status, tid), commit=True)
        # Raw fix:
        if status == 'completed':
            execute_query("UPDATE tasks SET status=%s, completed_at=NOW() WHERE id=%s", (status, tid), commit=True)
        else:
            execute_query("UPDATE tasks SET status=%s, completed_at=NULL WHERE id=%s", (status, tid), commit=True)
        return success_response(message='Task updated')
    except Exception as e:
        return error_response(str(e), 500)


# ── Notifications ─────────────────────────────────────────────────────────────

def handle_get_notifications(params):
    try:
        unread_only = params.get('unread', [None])[0]
        where = "WHERE is_read=0" if unread_only else ""
        notifs = execute_query(f"""
            SELECT n.*, c.name as customer_name, c.phone as customer_phone
            FROM notifications n
            LEFT JOIN customers c ON n.customer_id=c.id
            {where} ORDER BY n.sent_at DESC LIMIT 50
        """, fetchall=True)
        return success_response(notifs or [])
    except Exception as e:
        return error_response(str(e), 500)


def handle_mark_notification_read(nid):
    try:
        execute_query("UPDATE notifications SET is_read=1 WHERE id=%s", (nid,), commit=True)
        return success_response(message='Marked as read')
    except Exception as e:
        return error_response(str(e), 500)


def handle_mark_all_read():
    try:
        execute_query("UPDATE notifications SET is_read=1", commit=True)
        return success_response(message='All notifications marked as read')
    except Exception as e:
        return error_response(str(e), 500)


# ── Analytics ─────────────────────────────────────────────────────────────────

def handle_analytics():
    try:
        # Revenue by day (last 7 days)
        revenue_7d = execute_query("""
            SELECT booking_date, COALESCE(SUM(total_price),0) as revenue, COUNT(*) as count
            FROM bookings WHERE booking_date >= CURDATE()-INTERVAL 7 DAY AND status='completed'
            GROUP BY booking_date ORDER BY booking_date
        """, fetchall=True)

        # Top services
        top_services = execute_query("""
            SELECT s.name, COUNT(*) as bookings, COALESCE(SUM(b.total_price),0) as revenue
            FROM bookings b JOIN services s ON b.service_id=s.id
            WHERE b.status='completed'
            GROUP BY s.id, s.name ORDER BY bookings DESC LIMIT 5
        """, fetchall=True)

        # Status breakdown
        status_breakdown = execute_query("""
            SELECT status, COUNT(*) as count FROM bookings GROUP BY status
        """, fetchall=True)

        # Employee performance
        emp_perf = execute_query("""
            SELECT e.name, COUNT(b.id) as completed,
                   COALESCE(SUM(b.total_price),0) as revenue
            FROM employees e
            LEFT JOIN bookings b ON b.employee_id=e.id AND b.status='completed'
            GROUP BY e.id, e.name ORDER BY completed DESC
        """, fetchall=True)

        return success_response({
            'revenue_7d': revenue_7d or [],
            'top_services': top_services or [],
            'status_breakdown': status_breakdown or [],
            'employee_performance': emp_perf or []
        })
    except Exception as e:
        traceback.print_exc()
        return error_response(str(e), 500)



# ── Customer Portal API ───────────────────────────────────────────────────────

def handle_portal_services():
    """Public: list all active services (no auth required)"""
    return handle_get_services()


def handle_portal_book(body):
    """Public: customer self-booking — finds or creates customer, then books."""
    try:
        data = json.loads(body)
        required = ['name','phone','service_id','booking_date','booking_time']
        for f in required:
            if not data.get(f):
                return error_response(f'Field {f} is required')

        phone = data['phone'].strip()

        # Find existing customer by phone or create new
        customer = execute_query(
            "SELECT id, name FROM customers WHERE phone=%s", (phone,), fetchone=True)
        if customer:
            customer_id = customer['id']
            # Update vehicle info if provided
            if data.get('vehicle_reg'):
                execute_query(
                    "UPDATE customers SET vehicle_reg=%s, vehicle_type=%s WHERE id=%s",
                    (data.get('vehicle_reg',''), data.get('vehicle_type',''), customer_id),
                    commit=True)
        else:
            customer_id = execute_query("""
                INSERT INTO customers (name, phone, email, vehicle_reg, vehicle_type)
                VALUES (%s,%s,%s,%s,%s)
            """, (data['name'], phone, data.get('email',''),
                  data.get('vehicle_reg',''), data.get('vehicle_type','')), commit=True)

        # Create booking
        booking_body = json.dumps({
            'customer_id':  customer_id,
            'service_id':   data['service_id'],
            'booking_date': data['booking_date'],
            'booking_time': data['booking_time'],
            'vehicle_reg':  data.get('vehicle_reg',''),
            'notes':        data.get('notes',''),
        })
        return handle_create_booking(booking_body, is_customer_portal=True)
    except Exception as e:
        traceback.print_exc()
        return error_response(str(e), 500)


def handle_portal_check_booking(params):
    """Public: customer looks up their bookings by phone number."""
    try:
        phone = params.get('phone', [None])[0]
        if not phone:
            return error_response('Phone number required')
        bookings = execute_query("""
            SELECT b.id, b.booking_date, b.booking_time, b.status,
                   b.vehicle_reg, b.total_price, b.notes,
                   s.name as service_name, s.duration_minutes,
                   COALESCE(e.name,'To be assigned') as employee_name
            FROM bookings b
            JOIN customers c ON b.customer_id=c.id
            JOIN services s ON b.service_id=s.id
            LEFT JOIN employees e ON b.employee_id=e.id
            WHERE c.phone=%s
            ORDER BY b.booking_date DESC, b.booking_time DESC
            LIMIT 10
        """, (phone,), fetchall=True)
        return success_response(bookings or [])
    except Exception as e:
        return error_response(str(e), 500)


# ── HTTP Handler ──────────────────────────────────────────────────────────────

class CarwashHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # Suppress default logs

    def send_response_data(self, status, body, content_type):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

    def get_body(self):
        length = int(self.headers.get('Content-Length', 0))
        return self.rfile.read(length).decode('utf-8') if length else ''

    def get_session_from_header(self):
        auth = self.headers.get('Authorization', '')
        token = auth.replace('Bearer ', '')
        return get_session(token) if token else None

    def serve_static(self, path):
        base = os.path.join(os.path.dirname(__file__), '..', 'frontend')
        if path == '/' or path == '':
            path = '/templates/index.html'
        if path == '/portal' or path == '/portal/':
            path = '/templates/portal.html'
        
        file_path = os.path.normpath(base + path)
        
        # Security check
        if not file_path.startswith(os.path.normpath(base)):
            self.send_response(403); self.end_headers(); return

        if os.path.isfile(file_path):
            ext = os.path.splitext(file_path)[1]
            mime = {'.html':'text/html','.css':'text/css','.js':'application/javascript',
                    '.png':'image/png','.jpg':'image/jpeg','.ico':'image/x-icon',
                    '.svg':'image/svg+xml','.woff2':'font/woff2'}.get(ext, 'text/plain')
            with open(file_path, 'rb') as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        else:
            # SPA fallback
            index = os.path.join(base, 'templates', 'index.html')
            if os.path.isfile(index):
                with open(index, 'rb') as f:
                    content = f.read()
                self.send_response(200)
                self.send_header('Content-Type', 'text/html')
                self.end_headers()
                self.wfile.write(content)
            else:
                self.send_response(404); self.end_headers()

    def route(self, method, path, params, body, headers):
        session = self.get_session_from_header()

        # Auth routes (no session required)
        if method == 'POST' and path == '/api/auth/login':
            return handle_login(body, headers)
        if method == 'POST' and path == '/api/auth/logout':
            return handle_logout(body, headers, session)

        # Protected routes
        # Dashboard
        if method == 'GET' and path == '/api/dashboard':
            return handle_dashboard_stats(session)

        # Analytics
        if method == 'GET' and path == '/api/analytics':
            return handle_analytics()

        # Bookings
        if method == 'GET' and path == '/api/bookings':
            return handle_get_bookings(params)
        if method == 'POST' and path == '/api/bookings':
            return handle_create_booking(body)
        m = re.match(r'^/api/bookings/(\d+)/status$', path)
        if m and method == 'PUT':
            return handle_update_booking_status(int(m.group(1)), body)
        m = re.match(r'^/api/bookings/(\d+)$', path)
        if m and method == 'DELETE':
            return handle_delete_booking(int(m.group(1)))

        # Customers
        if method == 'GET' and path == '/api/customers':
            return handle_get_customers(params)
        if method == 'POST' and path == '/api/customers':
            return handle_create_customer(body)
        m = re.match(r'^/api/customers/(\d+)$', path)
        if m and method == 'PUT':
            return handle_update_customer(int(m.group(1)), body)
        if m and method == 'DELETE':
            return handle_delete_customer(int(m.group(1)))

        # Services
        if method == 'GET' and path == '/api/services':
            return handle_get_services()
        if method == 'POST' and path == '/api/services':
            return handle_create_service(body)
        m = re.match(r'^/api/services/(\d+)$', path)
        if m and method == 'PUT':
            return handle_update_service(int(m.group(1)), body)
        if m and method == 'DELETE':
            return handle_delete_service(int(m.group(1)))

        # Employees
        if method == 'GET' and path == '/api/employees':
            return handle_get_employees(params)
        if method == 'POST' and path == '/api/employees':
            return handle_create_employee(body)
        m = re.match(r'^/api/employees/(\d+)$', path)
        if m and method == 'PUT':
            return handle_update_employee(int(m.group(1)), body)
        if m and method == 'DELETE':
            return handle_delete_employee(int(m.group(1)))

        # Tasks
        if method == 'GET' and path == '/api/tasks':
            return handle_get_tasks(params)
        m = re.match(r'^/api/tasks/(\d+)$', path)
        if m and method == 'PUT':
            return handle_update_task(int(m.group(1)), body)

        # Notifications
        if method == 'GET' and path == '/api/notifications':
            return handle_get_notifications(params)
        if method == 'PUT' and path == '/api/notifications/read-all':
            return handle_mark_all_read()
        m = re.match(r'^/api/notifications/(\d+)/read$', path)
        if m and method == 'PUT':
            return handle_mark_notification_read(int(m.group(1)))

        # Change password
        if method == 'POST' and path == '/api/auth/change-password':
            return handle_change_password(body, session)

        # Test SMS
        if method == 'POST' and path == '/api/sms/test':
            return handle_test_sms(body)

        # ── Customer Portal Routes (public, no auth) ──────────────
        if method == 'GET' and path == '/api/portal/services':
            return handle_portal_services()
        if method == 'POST' and path == '/api/portal/book':
            return handle_portal_book(body)
        if method == 'GET' and path == '/api/portal/bookings':
            return handle_portal_check_booking(params)

        return error_response('Route not found', 404)

    def handle_request(self, method):
        parsed = urlparse(self.path)
        path = unquote(parsed.path).rstrip('/')
        params = parse_qs(parsed.query)
        headers = dict(self.headers)
        body = self.get_body()

        if path.startswith('/api/'):
            try:
                status, resp_body, ctype = self.route(method, path, params, body, headers)
                self.send_response_data(status, resp_body, ctype)
            except Exception as e:
                traceback.print_exc()
                s, b, c = error_response(str(e), 500)
                self.send_response_data(s, b, c)
        else:
            self.serve_static(path if path else '/')

    def do_GET(self): self.handle_request('GET')
    def do_POST(self): self.handle_request('POST')
    def do_PUT(self): self.handle_request('PUT')
    def do_DELETE(self): self.handle_request('DELETE')


def run(port=8080):
    server = HTTPServer(('0.0.0.0', port), CarwashHandler)
    print(f"🚗 Extremeclean Carwash System running at http://localhost:{port}")
    print(f"📊 Admin: http://localhost:{port}/")
    print(f"🔑 Login: admin / admin123")
    server.serve_forever()


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    run(port)
