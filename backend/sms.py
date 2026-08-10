"""
Africa's Talking SMS Integration
Sends SMS notifications to customers for booking events.

Set these environment variables:
    AT_USERNAME   - Your Africa's Talking username
    AT_API_KEY    - Your Africa's Talking API key
    AT_SENDER_ID  - Optional sender ID (e.g. EXTREMECLEAN)
    AT_SANDBOX    - Set to '1' to use sandbox (testing) mode
"""

import os
import json
import urllib.request
import urllib.parse
import urllib.error

AT_USERNAME  = os.environ.get('AT_USERNAME', 'sandbox')
AT_API_KEY   = os.environ.get('AT_API_KEY', 'atsk_323f0deacc7e7c8175d9b099330ff9da2efc6485c8051330f8f67e8b6e5d04939dd183c5')
AT_SENDER_ID = os.environ.get('AT_SENDER_ID', '')   # leave blank to use shortcode
AT_SANDBOX   = os.environ.get('AT_SANDBOX', '1') == '1'  # default: sandbox mode

BASE_URL = (
    'https://api.sandbox.africastalking.com/version1/messaging'
    if AT_SANDBOX else
    'https://api.africastalking.com/version1/messaging'
)


def _format_phone(phone: str) -> str:
    """Normalize Kenyan phone numbers to E.164 format (+2547XXXXXXXX)."""
    phone = phone.strip().replace(' ', '').replace('-', '')
    if phone.startswith('+'):
        return phone
    if phone.startswith('07') or phone.startswith('01'):
        return '+254' + phone[1:]
    if phone.startswith('254'):
        return '+' + phone
    if phone.startswith('7') or phone.startswith('1'):
        return '+254' + phone
    return phone  # return as-is if unrecognized


def send_sms(phone: str, message: str) -> dict:
    """
    Send a single SMS via Africa's Talking.
    Returns dict with keys: success (bool), message_id (str), error (str).
    """
    if not AT_API_KEY or AT_API_KEY.startswith('atsk_xxx'):
        # SMS not configured — log and skip silently
        print(f"[SMS-SKIP] Not configured. Would send to {phone}: {message}")
        return {'success': False, 'error': 'SMS not configured'}

    formatted = _format_phone(phone)
    payload = {
        'username': AT_USERNAME,
        'to':       formatted,
        'message':  message,
    }
    if AT_SENDER_ID:
        payload['from'] = AT_SENDER_ID

    data = urllib.parse.urlencode(payload).encode('utf-8')
    req = urllib.request.Request(
        BASE_URL,
        data=data,
        headers={
            'Accept':       'application/json',
            'Content-Type': 'application/x-www-form-urlencoded',
            'apiKey':       AT_API_KEY,
        },
        method='POST'
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            recipients = result.get('SMSMessageData', {}).get('Recipients', [])
            if recipients and recipients[0].get('statusCode') == 101:
                mid = recipients[0].get('messageId', '')
                print(f"[SMS-OK] Sent to {formatted} | ID: {mid}")
                return {'success': True, 'message_id': mid}
            else:
                err = result.get('SMSMessageData', {}).get('Message', 'Unknown error')
                print(f"[SMS-FAIL] {formatted}: {err}")
                return {'success': False, 'error': err}

    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        print(f"[SMS-HTTP-ERR] {e.code}: {body}")
        return {'success': False, 'error': f'HTTP {e.code}: {body}'}
    except Exception as e:
        print(f"[SMS-ERR] {e}")
        return {'success': False, 'error': str(e)}


# ── Pre-built SMS templates ──────────────────────────────────────────────────

def sms_booking_confirmed(customer_name: str, service: str,
                           booking_date: str, booking_time: str,
                           booking_id: int, phone: str) -> dict:
    msg = (
        f"Hi {customer_name}! Your booking #{booking_id} for {service} "
        f"on {booking_date} at {booking_time} is CONFIRMED. "
        f"Extremeclean Carwash Nairobi. Questions? Call us anytime."
    )
    return send_sms(phone, msg)


def sms_booking_received(customer_name: str, service: str,
                          booking_date: str, booking_time: str,
                          booking_id: int, phone: str) -> dict:
    msg = (
        f"Hi {customer_name}! We received your booking #{booking_id} for {service} "
        f"on {booking_date} at {booking_time}. "
        f"We'll confirm shortly. - Extremeclean Carwash Nairobi"
    )
    return send_sms(phone, msg)


def sms_service_started(customer_name: str, service: str,
                         vehicle_reg: str, phone: str) -> dict:
    msg = (
        f"Hi {customer_name}! Your {service} for {vehicle_reg} has STARTED. "
        f"Our team is working on your vehicle now. - Extremeclean Nairobi"
    )
    return send_sms(phone, msg)


def sms_service_completed(customer_name: str, service: str,
                           vehicle_reg: str, price: float, phone: str) -> dict:
    msg = (
        f"Hi {customer_name}! Your {service} for {vehicle_reg} is DONE! "
        f"Total: KES {price:,.0f}. Thank you for choosing Extremeclean Nairobi. "
        f"See you next time!"
    )
    return send_sms(phone, msg)


def sms_booking_cancelled(customer_name: str, service: str,
                           booking_id: int, phone: str) -> dict:
    msg = (
        f"Hi {customer_name}, your booking #{booking_id} for {service} "
        f"has been cancelled. To rebook call us or visit our portal. "
        f"- Extremeclean Carwash Nairobi"
    )
    return send_sms(phone, msg)


def sms_booking_reminder(customer_name: str, service: str,
                          booking_date: str, booking_time: str,
                          phone: str) -> dict:
    msg = (
        f"Reminder: Hi {customer_name}, your {service} appointment is tomorrow "
        f"({booking_date}) at {booking_time}. "
        f"See you at Extremeclean Carwash Nairobi!"
    )
    return send_sms(phone, msg)
