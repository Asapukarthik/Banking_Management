# MyBank – Banking Management System (Flask demo)

## Features
- Unique random account numbers with collision checks.
- Unique transaction IDs and transfer reference IDs.
- Backend-generated timezone-aware transaction timestamps.
- Savings/current accounts, deposits and withdrawals.
- Account-to-account transfers with paired debit/credit ledger records.
- Customer dashboard with balance, recent transactions and deposit/withdrawal totals.
- Monthly deposit/withdrawal analytics.
- Admin overview and account status controls (Active/Frozen/Inactive).
- Success/error toast notifications and server-side validation.

## Run locally (Windows)
```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
$env:BANK_ADMIN_KEY="your-local-demo-secret"
python app.py
```
Open http://127.0.0.1:5000.

## Run locally (macOS/Linux)
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export BANK_ADMIN_KEY="your-local-demo-secret"
python app.py
```

## Render deployment
- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app`
- Add environment variable `BANK_ADMIN_KEY` with a long random secret.
- Set up persistent storage for `data/bank.json` or, preferably, migrate to PostgreSQL before relying on stored data. Render's default filesystem is ephemeral.

## Admin demo
The admin panel asks for `BANK_ADMIN_KEY`. For local development only, the fallback key is `local-demo-admin-key`. Always set a strong environment variable before deployment.

## Important limitations
This is an educational demonstration, not production banking software. It currently uses a JSON file and an in-process lock; it is not safe for multi-process/concurrent production traffic. Before public or real-money use, migrate to PostgreSQL with database transactions, add customer authentication/authorization, CSRF protection, rate limiting, secure audit logging, encryption and appropriate compliance/security review. Use synthetic customer data only; do not enter real Aadhaar/PAN information.
