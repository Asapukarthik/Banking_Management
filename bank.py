import hashlib
import hmac
import json
import os
import secrets
import threading
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from account import SavingsAccount, CurrentAccount, FixedDepositAccount, money
from customer import Customer

BASE_DIR = Path(__file__).resolve().parent
FILE = BASE_DIR / "data" / "bank.json"
_LOCK = threading.RLock()


# ── Helpers ──────────────────────────────────────────────────────────────────

def now_iso() -> str:
    """Return the current local time as an ISO 8601 string (with timezone)."""
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def new_transaction_id() -> str:
    """Generate a unique transaction ID, e.g. TXN-A1B2C3D4E5F6."""
    return f"TXN-{uuid.uuid4().hex[:12].upper()}"


def hash_pin(pin: str) -> str:
    """Return the SHA-256 hex digest of a PIN string."""
    return hashlib.sha256(pin.encode()).hexdigest()


# ── Bank ─────────────────────────────────────────────────────────────────────

class Bank:
    """
    Core banking engine.

    Manages accounts, transactions, and JSON-based persistence with a
    thread-safe in-process lock. Not safe for multi-process production use.
    """

    def __init__(self):
        """Initialise the bank and create the data file if it does not exist."""
        FILE.parent.mkdir(parents=True, exist_ok=True)
        if not FILE.exists():
            self.save({"customers": [], "accounts": [], "transactions": []})
        else:
            data = self.load()
            data.setdefault("customers", [])
            data.setdefault("accounts", [])
            data.setdefault("transactions", [])
            for account in data["accounts"]:
                account.setdefault("status", "Active")
                account.setdefault("pin_hash", None)   # Support accounts created before PIN was added
            self.save(data)

    # ── Persistence ───────────────────────────────────────────────────────────

    def load(self) -> dict:
        """Load and return bank data from the JSON file."""
        with _LOCK:
            try:
                return json.loads(FILE.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise RuntimeError("Bank data file is corrupted; restore a valid backup") from exc

    def save(self, data: dict) -> None:
        """Atomically save bank data using a temp file + os.replace()."""
        with _LOCK:
            temp_file = FILE.with_suffix(".tmp")
            temp_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
            os.replace(temp_file, FILE)

    # ── Account Creation ──────────────────────────────────────────────────────

    def create(self, form: dict) -> str:
        """
        Create a new bank account.

        Args:
            form: Dictionary with keys — name, dob, gender, email, phone,
                  address, account_type, pin, initial_deposit (optional),
                  aadhar (optional), pan (optional).

        Returns:
            The newly generated account number (e.g. 'AC123456789012').

        Raises:
            ValueError: If required fields are missing or any validation fails.
        """
        required = ("name", "dob", "gender", "email", "phone", "address", "account_type", "pin")
        missing = [k for k in required if not str(form.get(k, "")).strip()]
        if missing:
            raise ValueError(f"Please complete all required fields: {', '.join(missing)}")

        account_type = str(form["account_type"]).strip()
        if account_type not in ("Savings", "Current", "Fixed Deposit"):
            raise ValueError("Choose a valid account type: Savings, Current, or Fixed Deposit")

        # Validate 4-digit PIN
        pin = str(form.get("pin", "")).strip()
        if not pin.isdigit() or len(pin) != 4:
            raise ValueError("PIN must be exactly 4 digits (numbers only)")

        # Validate Aadhaar (optional field)
        aadhar = str(form.get("aadhar", "")).strip()
        if aadhar and (not aadhar.isdigit() or len(aadhar) != 12):
            raise ValueError("Aadhaar must contain exactly 12 digits")

        # Validate phone (required)
        phone = str(form.get("phone", "")).strip()
        if not phone.isdigit() or len(phone) != 10:
            raise ValueError("Phone number must contain exactly 10 digits")

        # Validate initial deposit
        raw_deposit = form.get("initial_deposit") or 0
        initial_deposit = money(raw_deposit)
        if initial_deposit < 0:
            raise ValueError("Initial deposit cannot be negative")
        if account_type == "Savings" and initial_deposit < Decimal("500.00"):
            raise ValueError("Savings accounts require a minimum opening balance of ₹500")
        if account_type == "Fixed Deposit" and initial_deposit <= 0:
            raise ValueError("Fixed Deposit accounts require an initial deposit amount greater than zero")

        with _LOCK:
            data = self.load()
            existing = {a["number"] for a in data["accounts"]}
            number = self._new_account_number(existing)

            # Build the customer record using the Customer class (Improvement #1)
            customer_obj = Customer(
                name    = str(form.get("name",    "")).strip(),
                dob     = str(form.get("dob",     "")).strip(),
                gender  = str(form.get("gender",  "")).strip(),
                email   = str(form.get("email",   "")).strip(),
                phone   = phone,
                address = str(form.get("address", "")).strip(),
                aadhar  = aadhar,
                pan     = str(form.get("pan", "")).strip(),
            )
            customer = customer_obj.to_dict()

            account = {
                "number":     number,
                "customer":   customer,
                "type":       account_type,
                "balance":    float(initial_deposit),
                "status":     "Active",
                "pin_hash":   hash_pin(pin),       # Improvement #2 — store hashed PIN
                "created_at": now_iso(),
            }
            data["customers"].append(customer)
            data["accounts"].append(account)

            # Record the opening deposit as a transaction (Improvement #3)
            if initial_deposit > 0:
                opening_txn = {
                    "transaction_id": new_transaction_id(),
                    "transfer_id":    None,
                    "account":        number,
                    "type":           "Deposit",
                    "amount":         float(initial_deposit),
                    "balance_after":  float(initial_deposit),
                    "date_time":      now_iso(),
                    "status":         "Success",
                }
                data["transactions"].append(opening_txn)

            self.save(data)
            return number

    @staticmethod
    def _new_account_number(existing: set) -> str:
        """
        Generate a unique random 12-digit account number with the 'AC' prefix.
        Keeps retrying until a number not already in the set is found.
        """
        while True:
            candidate = "AC" + str(secrets.randbelow(900000000000) + 100000000000)
            if candidate not in existing:
                return candidate

    # ── Account Lookup ────────────────────────────────────────────────────────

    def find(self, number, data: dict) -> dict:
        """
        Find and return an account record by account number.

        Raises:
            ValueError: If no account with that number exists.
        """
        number = str(number or "").strip()
        for account in data["accounts"]:
            if account["number"] == number:
                return account
        raise ValueError("Account not found. Check the account number")

    def _account_object(self, acc: dict):
        """Instantiate the correct Account subclass for the given account record."""
        type_map = {
            "Savings":       SavingsAccount,
            "Current":       CurrentAccount,
            "Fixed Deposit": FixedDepositAccount,   # Improvement #4
        }
        cls = type_map.get(acc["type"], CurrentAccount)
        return cls(acc["number"], acc["customer"], acc["type"], acc["balance"])

    def _ensure_active(self, acc: dict) -> None:
        """Raise ValueError if the account status is not 'Active'."""
        if acc.get("status", "Active") != "Active":
            raise ValueError("This account is frozen or inactive. Contact the bank administrator")

    def _verify_pin(self, acc: dict, pin: str) -> None:
        """
        Verify the PIN for an account (Improvement #2).
        Only enforced when the account has a stored PIN hash.
        Legacy accounts without a pin_hash are always accessible.

        Raises:
            ValueError: If the PIN is required but missing or incorrect.
        """
        stored_hash = acc.get("pin_hash")
        if not stored_hash:
            return  # Legacy account without a PIN — allow access
        if not pin:
            raise ValueError("PIN is required to access this account")
        if not hmac.compare_digest(hash_pin(str(pin)), stored_hash):
            raise ValueError("Incorrect PIN. Please try again")

    # ── Transactions ──────────────────────────────────────────────────────────

    def action(self, number, amount, action) -> dict:
        """
        Perform a deposit or withdrawal on an account.

        Args:
            number: Account number.
            amount: Transaction amount.
            action: 'deposit' or 'withdraw' (case-insensitive).

        Returns:
            The transaction record as a dict.

        Raises:
            ValueError: If the action is invalid, account is inactive, or
                        balance is insufficient for withdrawal.
        """
        action = str(action or "").strip().lower()
        if action not in ("deposit", "withdraw"):
            raise ValueError("Choose Deposit or Withdraw")
        amount = money(amount)
        with _LOCK:
            data = self.load()
            acc = self.find(number, data)
            self._ensure_active(acc)
            obj = self._account_object(acc)
            if action == "deposit":
                obj.deposit(amount)
            else:
                obj.withdraw(amount)
            acc["balance"] = float(obj.balance)
            transaction = {
                "transaction_id": new_transaction_id(),
                "transfer_id":    None,
                "account":        acc["number"],
                "type":           action.title(),
                "amount":         float(amount),
                "balance_after":  float(obj.balance),
                "date_time":      now_iso(),
                "status":         "Success",
            }
            data["transactions"].append(transaction)
            self.save(data)
            return transaction

    def transfer(self, from_number, to_number, amount) -> dict:
        """
        Transfer money from one account to another.

        Args:
            from_number: Source account number.
            to_number:   Recipient account number.
            amount:      Amount to transfer (must be > 0).

        Returns:
            A dict containing transfer_id, amount, from/to accounts, and timestamp.

        Raises:
            ValueError: If accounts are the same, either is inactive, or
                        the sender has insufficient funds.
        """
        amount = money(amount)
        if amount <= 0:
            raise ValueError("Transfer amount must be greater than zero")
        if str(from_number).strip() == str(to_number).strip():
            raise ValueError("Source and recipient accounts must be different")
        with _LOCK:
            data = self.load()
            source    = self.find(from_number, data)
            recipient = self.find(to_number, data)
            self._ensure_active(source)
            self._ensure_active(recipient)
            source_obj    = self._account_object(source)
            recipient_obj = self._account_object(recipient)
            source_obj.withdraw(amount)
            recipient_obj.deposit(amount)
            source["balance"]    = float(source_obj.balance)
            recipient["balance"] = float(recipient_obj.balance)
            transfer_id = f"TRF-{uuid.uuid4().hex[:12].upper()}"
            timestamp   = now_iso()
            debit = {
                "transaction_id": new_transaction_id(), "transfer_id": transfer_id,
                "account": source["number"],    "counterparty": recipient["number"],
                "type": "Transfer Sent",        "amount": float(amount),
                "balance_after": float(source_obj.balance),
                "date_time": timestamp,         "status": "Success",
            }
            credit = {
                "transaction_id": new_transaction_id(), "transfer_id": transfer_id,
                "account": recipient["number"], "counterparty": source["number"],
                "type": "Transfer Received",    "amount": float(amount),
                "balance_after": float(recipient_obj.balance),
                "date_time": timestamp,         "status": "Success",
            }
            data["transactions"].extend([debit, credit])
            self.save(data)  # Both balance updates and ledger entries saved atomically.
            return {
                "transfer_id":  transfer_id,
                "amount":       float(amount),
                "from_account": source["number"],
                "to_account":   recipient["number"],
                "date_time":    timestamp,
            }

    # ── Customer Dashboard ────────────────────────────────────────────────────

    def customer_dashboard(self, number: str, pin: str = "") -> dict:
        """
        Return account info and recent transaction history for the customer portal.

        Args:
            number: Account number.
            pin:    4-digit PIN for verification (Improvement #2).

        Returns:
            dict with 'account', 'transactions', 'deposit_total', 'withdrawal_total'.

        Raises:
            ValueError: If account not found or PIN is incorrect.
        """
        data = self.load()
        acc  = self.find(number, data)
        self._verify_pin(acc, pin)
        txns       = [t for t in data["transactions"] if t.get("account") == acc["number"]]
        deposits   = sum(t["amount"] for t in txns if t["type"] in ("Deposit", "Transfer Received"))
        withdrawals= sum(t["amount"] for t in txns if t["type"] in ("Withdraw", "Transfer Sent"))
        return {
            "account":          acc,
            "transactions":     sorted(txns, key=lambda t: t.get("date_time", ""), reverse=True)[:10],
            "deposit_total":    round(deposits, 2),
            "withdrawal_total": round(withdrawals, 2),
        }

    # ── Account Management ────────────────────────────────────────────────────

    def delete_account(self, number: str) -> None:
        """
        Close and permanently delete an account (Improvement #5).

        The account must have a zero balance before it can be deleted.

        Args:
            number: The account number to delete.

        Raises:
            ValueError: If the account has a remaining balance or is not found.
        """
        with _LOCK:
            data = self.load()
            acc  = self.find(number, data)
            if float(acc["balance"]) > 0:
                raise ValueError(
                    "Cannot close an account with a remaining balance. "
                    "Please withdraw all funds first."
                )
            data["accounts"] = [a for a in data["accounts"] if a["number"] != number]
            self.save(data)

    def set_account_status(self, number: str, status: str) -> dict:
        """
        Update an account's status to Active, Frozen, or Inactive.

        Args:
            number: Account number.
            status: One of 'Active', 'Frozen', or 'Inactive'.

        Returns:
            dict with 'number' and updated 'status'.

        Raises:
            ValueError: If the status value is not one of the allowed values.
        """
        if status not in ("Active", "Frozen", "Inactive"):
            raise ValueError("Invalid account status — choose Active, Frozen, or Inactive")
        with _LOCK:
            data = self.load()
            acc  = self.find(number, data)
            acc["status"] = status
            self.save(data)
        return {"number": number, "status": status}

    # ── Dashboard Analytics ───────────────────────────────────────────────────

    def dashboard(self) -> dict:
        """
        Compute the full bank-wide dashboard summary.

        Returns:
            dict with accounts, transactions (up to 100), totals,
            active_count, and monthly deposit/withdrawal analytics.
        """
        data         = self.load()
        accounts     = data["accounts"]
        transactions = sorted(data["transactions"], key=lambda t: t.get("date_time", ""), reverse=True)
        deposits     = sum(t["amount"] for t in transactions if t["type"] in ("Deposit", "Transfer Received"))
        withdrawals  = sum(t["amount"] for t in transactions if t["type"] in ("Withdraw", "Transfer Sent"))

        # Build monthly analytics buckets (Improvement #9 — used for chart)
        monthly: dict = {}
        for txn in transactions:
            month  = txn.get("date_time", "")[:7] or "Unknown"
            bucket = monthly.setdefault(month, {"month": month, "deposits": 0.0, "withdrawals": 0.0})
            key    = "deposits" if txn["type"] in ("Deposit", "Transfer Received") else "withdrawals"
            bucket[key] += txn["amount"]

        return {
            "accounts":         accounts,
            "transactions":     transactions[:100],
            "total":            round(sum(a["balance"] for a in accounts), 2),
            "account_count":    len(accounts),
            "active_count":     sum(a.get("status", "Active") == "Active" for a in accounts),
            "deposit_total":    round(deposits, 2),
            "withdrawal_total": round(withdrawals, 2),
            "monthly":          sorted(monthly.values(), key=lambda x: x["month"]),
        }
