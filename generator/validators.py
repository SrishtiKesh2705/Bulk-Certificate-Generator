from django.core.exceptions import ValidationError
from django.core.validators import validate_email

def validate_recipient(row):
    name=str(row.get("name") or "").strip()
    if not name:
        return "name is required"
    if len(name)>255:
        return "name too long"

    email=str(row.get("email") or "").strip()
    if email:
        try:
            validate_email(email)
        except ValidationError:
            return "invalid email"
        
    return None