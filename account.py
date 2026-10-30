from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


def money(value):
    """
    Convert any numeric value to a Decimal rounded to 2 decimal places.

    Args:
        value: A number or string to convert.

    Returns:
        Decimal: The value rounded to 2 decimal places.

    Raises:
        ValueError: If the value cannot be converted to a valid finite amount.
    """
    try:
        amount = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("Enter a valid amount")
    if not amount.is_finite():
        raise ValueError("Enter a valid amount")
    return amount


class Account:
    """
    Base bank account class.

    Provides the core deposit and withdraw operations.
    All monetary values are handled using Decimal for precision.
    """

    def __init__(self, number, customer, kind, balance=0):
        """
        Initialise an Account.

        Args:
            number   (str):   Unique account number.
            customer (dict):  Customer details dictionary.
            kind     (str):   Account type label.
            balance  (float): Starting balance (default 0).
        """
        self.number = number
        self.customer = customer
        self.kind = kind
        self.balance = money(balance)

    def deposit(self, amount):
        """
        Deposit money into the account.

        Args:
            amount: Amount to deposit — must be greater than zero.

        Returns:
            Decimal: The deposited amount.

        Raises:
            ValueError: If the amount is not positive.
        """
        amount = money(amount)
        if amount <= 0:
            raise ValueError("Amount must be greater than zero")
        self.balance += amount
        return amount

    def withdraw(self, amount):
        """
        Withdraw money from the account.

        Args:
            amount: Amount to withdraw — must be > 0 and <= current balance.

        Returns:
            Decimal: The withdrawn amount.

        Raises:
            ValueError: If the amount is invalid or the balance is insufficient.
        """
        amount = money(amount)
        if amount <= 0:
            raise ValueError("Amount must be greater than zero")
        if amount > self.balance:
            raise ValueError("Insufficient balance")
        self.balance -= amount
        return amount


class SavingsAccount(Account):
    """
    Savings account — must always maintain a minimum balance of ₹500.
    A minimum opening deposit of ₹500 is also required.
    """

    MIN_BALANCE = Decimal("500.00")
    MIN_OPENING = Decimal("500.00")

    def withdraw(self, amount):
        """
        Withdraw while ensuring the ₹500 minimum balance is maintained.

        Raises:
            ValueError: If the withdrawal would drop the balance below ₹500.
        """
        amount = money(amount)
        if amount <= 0:
            raise ValueError("Amount must be greater than zero")
        if self.balance - amount < self.MIN_BALANCE:
            raise ValueError("Keep at least ₹500 in the savings account")
        return super().withdraw(amount)


class CurrentAccount(Account):
    """
    Current account — no minimum balance requirement.
    Suitable for businesses and frequent transactions.
    """
    pass


class FixedDepositAccount(Account):
    """
    Fixed Deposit account — money is locked for the deposit period.
    Deposits are allowed but NO withdrawals are permitted.
    """

    def withdraw(self, amount):
        """Withdrawals are not allowed from a Fixed Deposit account."""
        raise ValueError("Withdrawals are not allowed from a Fixed Deposit account")
