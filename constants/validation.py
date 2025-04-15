# data validator constants


# Validation configuration
REQUIRED_FIELDS = ["username", "email", "first_name", "last_name", "registered_date"]
EMAIL_PATTERN = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
DATE_PATTERN = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.\d{3}Z$'
GENDER_VALUES = ["male", "female","other"]


# Data type validation rules
FIELD_TYPES = {
    "first_name": str,
    "last_name": str,
    "gender": str,
    "address": str,
    "post_code": [str, int],  # Can be string or integer
    "email": str,
    "username": str,
    "dob": str,
    "registered_date": str,
    "phone": str,
    "picture": str
}

# Value constraints
VALUE_CONSTRAINTS = {
    "gender": ["male", "female","other"],
    "username": {"min_length": 3, "max_length": 30}
}




