import sqlite3
import base64
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, ed25519
from cryptography.hazmat.primitives.serialization import load_pem_private_key

BASE_DIR = Path(__file__).resolve().parent
PRIVATE_KEY_PATH = BASE_DIR / "private_key.pem"
DB_FILE = BASE_DIR / "trial_ledger.db"

PLANS = {
    "1": {"name": "Solo 14-Day Free Trial", "days": 14, "seats": 1, "tier": "trial"},
    "2": {"name": "Solo 1-Month Commercial", "days": 30, "seats": 1, "tier": "commercial"},
    "3": {"name": "Solo 1-Year Commercial", "days": 365, "seats": 1, "tier": "commercial"},
    "4": {"name": "Group 14-Day Trial", "days": 14, "seats": 3, "tier": "trial"},
    "5": {"name": "Group 1-Month Commercial", "days": 30, "seats": 3, "tier": "commercial"},
    "6": {"name": "Group 1-Year Commercial", "days": 365, "seats": 3, "tier": "commercial"},
}

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS licenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_name TEXT NOT NULL,
            email TEXT NOT NULL,
            practice_number TEXT NOT NULL,
            plan_name TEXT NOT NULL,
            tier TEXT NOT NULL,
            seat_number INTEGER NOT NULL,
            total_seats INTEGER NOT NULL,
            license_key TEXT NOT NULL UNIQUE,
            date_issued TEXT NOT NULL,
            day_10_followup TEXT,
            date_expires TEXT NOT NULL,
            status TEXT DEFAULT 'Active'
        )
    """)
    conn.commit()
    conn.close()

def generate_signed_token(pr_number: str, duration_days: int) -> tuple[str, str]:
    if not PRIVATE_KEY_PATH.exists():
        raise FileNotFoundError(f"private_key.pem not found at {PRIVATE_KEY_PATH}")

    with open(PRIVATE_KEY_PATH, "rb") as f:
        private_key = load_pem_private_key(f.read(), password=None)

    now = datetime.now()
    expiry_date = (now + timedelta(days=duration_days)).strftime("%Y-%m-%d")

    payload = {
        "practice_number": pr_number.strip(),
        "valid_until": expiry_date,
        "issued_at": now.strftime("%Y-%m-%d"),
    }

    payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")

    if isinstance(private_key, ed25519.Ed25519PrivateKey):
        signature = private_key.sign(payload_bytes)
    else:
        signature = private_key.sign(
            payload_bytes,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH,
            ),
            hashes.SHA256(),
        )

    sig_len = len(signature).to_bytes(4, byteorder="big")
    token = base64.b64encode(sig_len + signature + payload_bytes).decode("utf-8")
    return token, expiry_date

def issue_license(account_name: str, email: str, practice_number: str, plan_choice: str, custom_seats: int = None):
    init_db()

    if plan_choice not in PLANS:
        print(f"❌ Invalid plan '{plan_choice}'. Choose 1 through 6.")
        return

    plan = PLANS[plan_choice]
    seats = custom_seats if custom_seats and custom_seats > 1 else plan["seats"]
    today = datetime.now()
    day_10 = (today + timedelta(days=10)).strftime("%Y-%m-%d") if plan["tier"] == "trial" else None

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    print("\n" + "=" * 65)
    print(f"📦 REGISTERING: {plan['name'].upper()}")
    print(f"👤 Clinician / Practice: {account_name}")
    print(f"🏥 Practice / BHF Number: {practice_number}")
    print(f"📧 Contact Email: {email}")
    print(f"🪑 Total Seats: {seats}")
    print("=" * 65)

    for seat in range(1, seats + 1):
        token, expiry = generate_signed_token(practice_number, plan["days"])
        try:
            c.execute("""
                INSERT INTO licenses (
                    account_name, email, practice_number, plan_name, tier,
                    seat_number, total_seats, license_key, date_issued,
                    day_10_followup, date_expires
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                account_name, email.strip().lower(), practice_number.strip(),
                plan["name"], plan["tier"], seat, seats, token,
                today.strftime("%Y-%m-%d"), day_10, expiry
            ))
            conn.commit()

            print(f"\n🔑 [Seat {seat}/{seats} Token]:")
            print(token)
        except sqlite3.IntegrityError:
            print(f"⚠️ License record conflict for seat {seat}.")

    conn.close()
    print("\n" + "-" * 65)
    print(f"✅ Recorded in trial_ledger.db. Expires: {expiry}")
    if day_10:
        print(f"🔔 Day 10 Check-in Scheduled: {day_10}")
    print("-" * 65 + "\n")

def view_ledger():
    init_db()
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        SELECT id, account_name, practice_number, email, plan_name,
               seat_number, total_seats, date_expires, day_10_followup, status
        FROM licenses ORDER BY id DESC
    """)
    rows = c.fetchall()
    conn.close()

    print("\n" + "=" * 95)
    print("                      PRAXIS CLINICAL MASTER AUDIT LEDGER")
    print("=" * 95)
    if not rows:
        print("No active records found in ledger.")
    for r in rows:
        follow = f" | Day 10: {r[8]}" if r[8] else ""
        print(
            f"ID #{r[0]:02d} | {r[1]} (PR: {r[2]}) | {r[3]} | "
            f"{r[4]} [Seat {r[5]}/{r[6]}] | Exp: {r[7]}{follow} | Status: {r[9]}"
        )
    print("=" * 95 + "\n")

def interactive_prompt():
    print("\n--- PRAXIS CLINICAL KEY DISPATCH & AUDIT ---")
    account_name = input("Clinician / Practice Name: ").strip()
    practice_number = input("Practice / BHF Number (or PR000000 for trial): ").strip() or "PR000000"
    email = input("Clinician Email Address: ").strip()

    print("\nSelect Subscription / Evaluation Timeline:")
    print("  [1] Solo 14-Day Free Trial (1 Seat)")
    print("  [2] Solo 1-Month Commercial (1 Seat)")
    print("  [3] Solo 1-Year Commercial (1 Seat)")
    print("  [4] Group Practice 14-Day Trial (Multi-Seat)")
    print("  [5] Group Practice 1-Month Commercial (Multi-Seat)")
    print("  [6] Group Practice 1-Year Commercial (Multi-Seat)")
    choice = input("\nEnter Plan Number (1-6): ").strip()

    custom_seats = None
    if choice in ["4", "5", "6"]:
        seats_in = input("Number of seats (press Enter for default 3): ").strip()
        if seats_in.isdigit():
            custom_seats = int(seats_in)

    issue_license(account_name, email, practice_number, choice, custom_seats)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].lower() == "view":
        view_ledger()
    else:
        interactive_prompt()