"""
scripts/clear_db.py
-------------------
Deletes data from the database. Tables are NOT dropped — structure is kept.

Usage:
    cd backend && python scripts/clear_db.py           # interactive prompt
    cd backend && python scripts/clear_db.py --yes     # skip confirmation
    cd backend && python scripts/clear_db.py --yes --keep-users   # keep user accounts

The path fix makes this runnable from either:
    cd backend         && python scripts/clear_db.py
    cd backend/scripts && python clear_db.py
"""

import sys
import os

# ── Path fix ────────────────────────────────────────────────────────────────────
# Walk up one directory from scripts/ to reach backend/
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

from db.session import SessionLocal
from db.models import InterviewAnswer, Application, Job, User


def clear(yes: bool = False, keep_users: bool = False):
    scope = "interview answers, applications, and jobs" if keep_users else "ALL data including users"

    if not yes:
        print(f"\n⚠️  This will delete {scope}.")
        confirm = input("   Type 'yes' to continue: ").strip().lower()
        if confirm != "yes":
            print("Aborted.")
            return

    db = SessionLocal()
    try:
        # Delete in FK-safe order: children before parents
        ia = db.query(InterviewAnswer).delete()
        ap = db.query(Application).delete()
        jo = db.query(Job).delete()
        us = 0
        if not keep_users:
            us = db.query(User).delete()

        db.commit()

        print(f"\n✓ Cleared:")
        print(f"  {ia:>4}  interview answers")
        print(f"  {ap:>4}  applications")
        print(f"  {jo:>4}  jobs")
        if not keep_users:
            print(f"  {us:>4}  users")
        else:
            print(f"     -   users  (kept)")
        print("\nRun python scripts/seed.py to re-populate.")

    except Exception as e:
        db.rollback()
        print(f"\n✗ Error during clear: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    clear(
        yes="--yes" in sys.argv,
        keep_users="--keep-users" in sys.argv,
    )
