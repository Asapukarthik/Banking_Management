import hmac
import os
from functools import wraps
from flask import Flask, render_template, request, jsonify
from bank import Bank

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False
bank = Bank()
ADMIN_KEY = os.environ.get("BANK_ADMIN_KEY", "local-demo-admin-key")


def payload():
    """Return parsed JSON body from the request, or an empty dict."""
    return request.get_json(silent=True) or {}


def admin_required(fn):
    """Decorator that blocks access unless the correct admin key is supplied."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        supplied = request.headers.get("X-Admin-Key", "")
        if not hmac.compare_digest(supplied, ADMIN_KEY):
            return jsonify({"error": "Admin authorization required"}), 401
        return fn(*args, **kwargs)
    return wrapper


# ── Page routes (multi-page site) ─────────────────────────────────────────────

@app.route("/")
def home():
    """Dashboard — overview of all banking activity."""
    return render_template("index.html")


@app.route("/create")
def create_page():
    """Create Account — open a new Savings, Current, or Fixed Deposit account."""
    return render_template("create.html")


@app.route("/transactions")
def transactions_page():
    """Transactions — deposit or withdraw from any active account."""
    return render_template("transactions.html")


@app.route("/transfer")
def transfer_page():
    """Money Transfer — move funds between two active accounts."""
    return render_template("transfer.html")


@app.route("/customer")
def customer_page():
    """Customer Portal — view account balance and transaction history (PIN protected)."""
    return render_template("customer.html")


@app.route("/accounts")
def accounts_page():
    """All Accounts — searchable, paginated list of every account."""
    return render_template("accounts.html")


@app.route("/admin")
def admin_page():
    """Admin Panel — account status management and account deletion."""
    return render_template("admin.html")


# ── JSON API routes ───────────────────────────────────────────────────────────

@app.get("/api/data")
def get_data():
    """Return the full bank dashboard data (accounts, transactions, analytics)."""
    return jsonify(bank.dashboard())


@app.post("/api/create")
def create():
    """Create a new bank account. Expects JSON body with customer + account details."""
    try:
        number = bank.create(payload())
        return jsonify({"message": "Account created successfully", "number": number}), 201
    except (ValueError, KeyError) as error:
        return jsonify({"error": str(error)}), 400
    except Exception:
        app.logger.exception("Account creation failed")
        return jsonify({"error": "Unable to create account right now"}), 500


@app.post("/api/action")
def action():
    """Perform a deposit or withdrawal. Expects JSON: number, amount, action."""
    try:
        data        = payload()
        transaction = bank.action(data.get("number"), data.get("amount"), data.get("action"))
        return jsonify({"message": "Transaction completed successfully", "transaction": transaction})
    except (ValueError, KeyError) as error:
        return jsonify({"error": str(error)}), 400
    except Exception:
        app.logger.exception("Transaction failed")
        return jsonify({"error": "Unable to complete transaction right now"}), 500


@app.post("/api/transfer")
def transfer():
    """Transfer money between accounts. Expects JSON: from_number, to_number, amount."""
    try:
        data   = payload()
        result = bank.transfer(data.get("from_number"), data.get("to_number"), data.get("amount"))
        return jsonify({"message": "Money transferred successfully", "transfer": result})
    except (ValueError, KeyError) as error:
        return jsonify({"error": str(error)}), 400
    except Exception:
        app.logger.exception("Money transfer failed")
        return jsonify({"error": "Unable to complete transfer right now"}), 500


@app.get("/api/customer/<number>")
def customer_dashboard(number):
    """
    Return customer account details.
    PIN is read from the X-Account-Pin request header (Improvement #2).
    """
    try:
        pin  = request.headers.get("X-Account-Pin", "")
        return jsonify(bank.customer_dashboard(number, pin))
    except ValueError as error:
        return jsonify({"error": str(error)}), 404


@app.delete("/api/account/<number>")
@admin_required
def delete_account(number):
    """
    Permanently close and delete an account (Improvement #5).
    Requires admin key. Account balance must be zero.
    """
    try:
        bank.delete_account(number)
        return jsonify({"message": "Account closed and deleted successfully"})
    except ValueError as error:
        return jsonify({"error": str(error)}), 400


@app.get("/api/admin/overview")
@admin_required
def admin_overview():
    """Return full dashboard data — admin only."""
    return jsonify(bank.dashboard())


@app.patch("/api/admin/account/<number>/status")
@admin_required
def update_account_status(number):
    """Update the status of an account to Active, Frozen, or Inactive — admin only."""
    try:
        result = bank.set_account_status(number, payload().get("status"))
        return jsonify({"message": f"Account status updated to {result['status']}", "account": result})
    except ValueError as error:
        return jsonify({"error": str(error)}), 400


if __name__ == "__main__":
    app.run(debug=True)
