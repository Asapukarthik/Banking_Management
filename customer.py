class Customer:
    """Represents a bank customer with all personal details."""

    def __init__(self, name, dob, gender, email, phone, address, aadhar="", pan=""):
        """
        Initialise a Customer with their personal details.

        Args:
            name    (str): Full name of the customer.
            dob     (str): Date of birth (ISO format recommended).
            gender  (str): Gender identity.
            email   (str): Email address.
            phone   (str): 10-digit mobile number.
            address (str): Residential address.
            aadhar  (str): 12-digit Aadhaar number (optional, demo only).
            pan     (str): PAN card number (optional, demo only).
        """
        self.name = name
        self.dob = dob
        self.gender = gender
        self.email = email
        self.phone = phone
        self.address = address
        self.aadhar = aadhar
        self.pan = pan

    def to_dict(self):
        """Return customer details as a plain dictionary for JSON storage."""
        return {
            "name":    self.name,
            "dob":     self.dob,
            "gender":  self.gender,
            "email":   self.email,
            "phone":   self.phone,
            "address": self.address,
            "aadhar":  self.aadhar,
            "pan":     self.pan,
        }
