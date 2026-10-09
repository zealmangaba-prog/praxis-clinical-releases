"""
core/license_guard.py

Cryptographic offline license token verification using Ed25519.
Verifies tokens against embedded or file-based public key with canonical
practice number normalization and backwards-compatible tuple returns.
Supports both JSON transport envelopes and binary concatenation tokens.
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
    Natively supports:
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


def verify_license_token(token_or_pr: Any, pr_or_token: Any = "") -> LicenseResult:
    """
    Universal verification function handling:
    1. String or tuple inputs from mint_token: (token_str, expiry)
    2. Both parameter orders: (token, pr_number) or (pr_number, token)
    """
    # If a tuple was passed (from mint_token returning (token, expiry)), extract the token string
    if isinstance(token_or_pr, (tuple, list)):
        token_or_pr = token_or_pr[0]
    if isinstance(pr_or_token, (tuple, list)):
        pr_or_token = pr_or_token[0]

    arg1 = str(token_or_pr).strip()
    arg2 = str(pr_or_token).strip()

    # The token is the longer string; the PR number is the shorter identifier
    if len(arg1) > len(arg2):
        token_b64 = arg1
        pr_number = arg2
    else:
        token_b64 = arg2
        pr_number = arg1

    if not token_b64:
        return LicenseResult(False, "No license key entered", {})

    # 1. Base64 unpack
    try:
        clean_b64 = "".join(token_b64.split())
        pad = len(clean_b64) % 4
        if pad:
            clean_b64 += "=" * (4 - pad)
        raw_decoded = base64.b64decode(clean_b64)
    except Exception as e:
        return LicenseResult(False, f"Invalid base64 encoding: {e}", {})

    payload = None
    raw_sig = None
    payload_bytes_candidates = []

    # Attempt 1: Format A - JSON envelope: {"payload": ..., "signature" / "sig": ...}
    try:
        envelope_json = raw_decoded.decode("utf-8")
        envelope = json.loads(envelope_json)
        if isinstance(envelope, dict) and "payload" in envelope:
            payload = envelope["payload"]
            sig_b64 = envelope.get("sig") or envelope.get("signature")
            if sig_b64:
                raw_sig = base64.b64decode(sig_b64)
                payload_bytes_candidates.append(
                    json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
                )
                payload_bytes_candidates.append(
                    json.dumps(payload, sort_keys=True).encode("utf-8")
                )
    except (UnicodeDecodeError, json.JSONDecodeError):
        pass

    # Attempt 2: Format B - Binary concatenation: signature bytes followed by JSON payload bytes
    if payload is None or raw_sig is None:
        # Check standard 64-byte Ed25519 signature
        # Also check 4-byte big-endian length prefix (e.g. b'\x00\x00\x00@' = 64 bytes)
        for offset in [0, 4]:
            sig_start = offset
            sig_end = offset + 64
            if len(raw_decoded) > sig_end:
                cand_sig = raw_decoded[sig_start:sig_end]
                cand_payload_bytes = raw_decoded[sig_end:]
                try:
                    cand_payload = json.loads(cand_payload_bytes.decode("utf-8"))
                    payload = cand_payload
                    raw_sig = cand_sig
                    payload_bytes_candidates.append(cand_payload_bytes)
                    payload_bytes_candidates.append(
                        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
                    )
                    payload_bytes_candidates.append(
                        json.dumps(payload, sort_keys=True).encode("utf-8")
                    )
                    break
                except Exception:
                    continue

    if payload is None or raw_sig is None:
        return LicenseResult(False, "Invalid license key format", {})

    # 2. Resolve Public Key
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

    # 3. Cryptographic Signature Verification
    verified = False
    for candidate_bytes in payload_bytes_candidates:
        try:
            public_key.verify(raw_sig, candidate_bytes)
            verified = True
            break
        except InvalidSignature:
            continue

    if not verified:
        return LicenseResult(False, "Cryptographic signature validation failed", {})

    # 4. Practice Number Matching
    token_pr = str(payload.get("practice_number") or payload.get("pr_number") or "").strip()
    norm_token_pr = normalize_pr_number(token_pr)
    norm_input_pr = normalize_pr_number(pr_number)

    if norm_token_pr != norm_input_pr:
        return LicenseResult(
            False,
            f"License is registered to PR #{token_pr}, not {pr_number}",
            payload,
        )

    # 5. Expiration Check
    exp_str = payload.get("expires") or payload.get("expires_at") or payload.get("valid_until")
    if not exp_str:
        return LicenseResult(False, "Subscription expired", payload)

    try:
        if "T" in exp_str:
            expires_at = datetime.fromisoformat(exp_str.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            is_expired = now > expires_at
        else:
            expires_date = datetime.strptime(str(exp_str)[:10], "%Y-%m-%d").date()
            is_expired = datetime.now(timezone.utc).date() > expires_date
    except Exception:
        return LicenseResult(False, "Subscription expired", payload)

    if is_expired:
        return LicenseResult(False, "Subscription expired", payload)

    # 6. Success Format
    tier = str(payload.get("tier") or payload.get("type") or "SOLO").upper()
    return LicenseResult(True, f"Active ({tier} Tier)", payload)


# Backward compatibility aliases
verify_license = verify_license_token