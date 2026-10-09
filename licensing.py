import base64
import json
import hmac
import hashlib
from datetime import datetime

SECRET_SIGNING_KEY = b"praxis-super-secret-licensing-key-2026"

def verify_license_key(key_string: str) -> tuple[bool, str, dict]:
    """
    Validates offline trial and commercial keys.
    Robust against hyphens in base64 payloads by parsing prefix and signature cleanly.
    Returns: (is_valid: bool, status_message: str, license_info: dict)
    """
    if not key_string or not isinstance(key_string, str):
        return False, "Invalid license key format.", {}

    cleaned_key = key_string.strip()

    # 1. Validate and extract prefix
    if cleaned_key.startswith("PRAXIS-PRO-"):
        prefix = "PRAXIS-PRO"
    elif cleaned_key.startswith("PRAXIS-TRIAL-"):
        prefix = "PRAXIS-TRIAL"
    else:
        return False, "Invalid license key format: Missing expected prefix.", {}

    # Strip prefix and leading hyphen
    body = cleaned_key[len(prefix) + 1:]

    # 2. Extract payload and signature (supports both '.' and '-' delimiters)
    if "." in body:
        b64_payload, signature = body.rsplit(".", 1)
    elif "-" in body:
        b64_payload, signature = body.rsplit("-", 1)
    else:
        return False, "Invalid license key format: Missing signature segment.", {}

    # 3. Verify HMAC signature integrity
    expected_sig = hmac.new(SECRET_SIGNING_KEY, b64_payload.encode(), hashlib.sha256).hexdigest()[:12]
    if not hmac.compare_digest(signature, expected_sig):
        return False, "License signature verification failed. Key may have been modified.", {}

    # 4. Decode base64 payload safely with restored padding
    try:
        padded_b64 = b64_payload + "=" * (-len(b64_payload) % 4)
        raw_json = base64.urlsafe_b64decode(padded_b64.encode()).decode("utf-8")
        data = json.loads(raw_json)
    except Exception:
        return False, "Corrupted license data payload.", {}

    # 5. Check expiration date
    try:
        expiry_date = datetime.strptime(data["exp"], "%Y-%m-%d")
    except (KeyError, ValueError):
        return False, "Invalid or missing expiration timestamp.", data

    today = datetime.now()
    if today.date() > expiry_date.date():
        return False, f"License expired on {data['exp']}. Please renew your plan.", data

    days_left = (expiry_date.date() - today.date()).days

    seat_info = data.get("seat", "1/1")
    if prefix == "PRAXIS-PRO":
        tier_label = f"Commercial License [Seat {seat_info}]"
    else:
        tier_label = f"Evaluation License [Seat {seat_info}]"

    status_message = f"{tier_label} active ({days_left} days remaining)."
    return True, status_message, data

if __name__ == "__main__":
    # Self-test when executed directly
    test_key = input("Paste a license key to verify: ").strip()
    valid, msg, info = verify_license_key(test_key)
    print(f"\nVerification Result: {'✅ SUCCESS' if valid else '❌ FAILED'}")
    print(f"Message: {msg}")
    print(f"Decoded Data: {info}\n")