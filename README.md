# Extremeclean Carwash Nairobi — Management System
### Full-Stack: Pure Python + MySQL + Vanilla JS | Africa's Talking SMS

---

## Project Structure

```
extremeclean/
├── run.py                        ← START HERE: python run.py
├── requirements.txt
├── backend/
│   ├── app.py                    ← HTTP server + all API routes
│   ├── db.py                     ← MySQL connection layer
│   ├── sms.py                    ← Africa's Talking SMS integration
│   └── schema.sql                ← DB schema + seed data (auto-runs)
└── frontend/
    ├── templates/
    │   ├── index.html            ← Admin dashboard (SPA)
    │   └── portal.html          ← Customer self-booking portal
    └── static/
        ├── css/style.css
        └── js/app.js
```

---

## Quick Start

### 1. Install dependency
```bash
pip install mysql-connector-python
```

### 2. Set MySQL credentials
```bash
export DB_HOST=localhost
export DB_USER=root
export DB_PASS=your_password
```

### 3. Set Africa's Talking credentials
```bash
export AT_USERNAME=your_username
export AT_API_KEY=your_api_key
export AT_SENDER_ID=EXTREMECLEAN
export AT_SANDBOX=0
```

### 4. Run
```bash
python run.py
```

| URL | Access |
|-----|--------|
| http://localhost:8080 | Admin — login: admin / admin123 |
| http://localhost:8080/portal | Customer booking portal (public) |

---

## SMS Triggers (Africa's Talking)

| Event | SMS |
|-------|-----|
| Booking received | Confirmation + details |
| Admin confirms | Confirmed notification |
| Service starts | "We've started your car" |
| Service done | "Done! Total: KES X" |
| Cancelled | Cancellation notice |

---

*Python 3 stdlib only — no frameworks required*
