"""
core/license_guard.py

Cryptographic offline license token verification using Ed25519.
Verifies tokens against embedded or file-based public key with canonical
practice number normalization and backwards-compatible tuple returns.
"""

import os
import re
import json
import base64
from datetime import datetime, timezone
from typing import Tuple, Dict, Any, Union

from cryptography.hazmat.primitives.serialization import load_pem_public_key
from cryptography.exceptions import InvalidSignature

# Default fallback public key search
def _load_default_public_key_pem() -> bytes:
    possible_paths = [
        os.path.join(os.path.dirname(__file__), "..", "public_key.pem"),
        os.path.join(os.path.dirname(__file__), "public_key.pem"),
        "public_key.pem",
    ]
    for path in possible_paths:
        if os.path.exists(path):
            with open(path, "rb") as f:
                return f.read()
    return b""

# Exposed at module level so tests can patch it via monkeypatch.setattr("core.license_guard.PUBLIC_KEY_PEM", pub_pem)
PUBLIC_KEY_PEM: Union[bytes, str] = _load_default_public_key_pem()


def normalize_pr_number(raw_pr: str) -> str:
    """
    Strips prefixes (PR, PC), punctuation, whitespace, and leading zeros
    so comparisons remain robust across different input formats.
    """
    if not raw_pr:
        return ""
    digits_only = re.sub(r"\D", "", str(raw_pr))
    if not digits_only:
        return re.sub(r"[^A-Za-z0-9]", "", str(raw_pr)).upper()
    return digits_only.lstrip("0") or "0"


class LicenseResult(tuple):
    """
    Standard 2-tuple: (is_valid, msg)
    Natively supports 2-variable unpacking:
        is_valid, msg = verify_license(...)
    And attribute access:
        res.is_valid, res.msg, res.payload
    """
    def __new__(cls, is_valid: bool, msg: str, payload: Dict[str, Any] = None):
        if payload is None:
            payload = {}
        return super().__new__(cls, (bool(is_valid), str(msg)))

    def __init__(self, is_valid: bool, msg: str, payload: Dict[str, Any] = None):
        self.is_valid = bool(is_valid)
        self.msg = str(msg)
        self.payload = payload or {}


def verify_license_token(token_or_pr: str, pr_or_token: str = "") -> LicenseResult:
    """
    Universal verification function handling both parameter orders:
    1. verify_license_token(token, pr_number) -> Test suite convention
    2. verify_license_token(pr_number, token) -> app.py convention
    """
    # Detect which argument is the base64 token and which is the PR number
    # A base64 JSON envelope is longer and contains JSON/base64 characteristics
    arg1 = str(token_or_pr).strip()
    arg2 = str(pr_or_token).strip()

    if len(arg1) > len(arg2) and len(arg1) > 20:
        token_b64 = arg1
        pr_number = arg2
    elif len(arg2) > len(arg1) and len(arg2) > 20:
        token_b64 = arg2
        pr_number = arg1
    else:
        # Default order matching test signature: (token, pr_number)
        token_b64 = arg1
        pr_number = arg2

    if not token_b64:
        return LicenseResult(False, "No license key entered", {})

    # 1. Base64 unpack envelope
    try:
        envelope_json = base64.b64decode(token_b64.encode("utf-8")).decode("utf-8")
        envelope = json.loads(envelope_json)
    except Exception:
        return LicenseResult(False, "Invalid license key format", {})

    if not isinstance(envelope, dict):
        return LicenseResult(False, "Invalid license key format", {})

    payload = envelope.get("payload")
    sig_b64 = envelope.get("sig") or envelope.get("signature")

    if not payload or not sig_b64:
        return LicenseResult(False, "Invalid license key format", {})

    # 2. Canonical serialization of payload
    try:
        raw_sig = base64.b64decode(sig_b64.encode("utf-8"))
        payload_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":") if ":" in token_b64 else None).encode("utf-8")
        # Support alternative standard json dump formatting without separators
        payload_bytes_alt = json.dumps(payload, sort_keys=True).encode("utf-8")
    except Exception:
        return LicenseResult(False, "Invalid license key format", {})

    # 3. Resolve Public Key
    pem_data = PUBLIC_KEY_PEM
    if isinstance(pem_data, str):
        pem_data = pem_data.encode("utf-8")
    if not pem_data:
        pem_data = _load_default_public_key_pem()

    if not pem_data:
        return LicenseResult(False, "public_key.pem not found in project directory.", {})

    try:
        public_key = load_pem_public_key(pem_data)
    except Exception as e:
        return LicenseResult(False, f"Failed to load public key: {e}", {})

    # 4. Cryptographic Signature Verification
    verified = False
    for candidate_bytes in [payload_bytes_alt, payload_bytes]:
        try:
            public_key.verify(raw_sig, candidate_bytes)
            verified = True
            break
        except InvalidSignature:
            continue

    if not verified:
        return LicenseResult(False, "Cryptographic signature validation failed", {})

    # 5. Practice Number Matching
    token_pr = str(payload.get("practice_number") or payload.get("pr_number") or "").strip()
    norm_token_pr = normalize_pr_number(token_pr)
    norm_input_pr = normalize_pr_number(pr_number)

    if norm_token_pr != norm_input_pr:
        return LicenseResult(
            False,
            f"License is registered to PR #{token_pr}, not {pr_number}",
            payload
        )

    # 6. Expiration Check
    exp_str = payload.get("expires") or payload.get("expires_at")
    if not exp_str:
        return LicenseResult(False, "Subscription expired", payload)

    try:
        # Support both 'YYYY-MM-DD' and ISO-8601 strings
        if "T" in exp_str:
            expires_at = datetime.fromisoformat(exp_str.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            is_expired = now > expires_at
        else:
            expires_date = datetime.strptime(exp_str, "%Y-%m-%d").date()
            is_expired = datetime.utcnow().date() > expires_date
    except Exception:
        return LicenseResult(False, "Subscription expired", payload)

    if is_expired:
        return LicenseResult(False, "Subscription expired", payload)

    # 7. Success Format
    tier = str(payload.get("tier") or payload.get("type") or "SOLO").upper()
    return LicenseResult(True, f"Active ({tier} Tier)", payload)


# Backward compatibility aliases
verify_license = verify_license_token