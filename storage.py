# storage.py
import sqlite3
from datetime import datetime, timedelta
from contextlib import contextmanager

DB_PATH = "vpn_bot.db"


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                user_id INTEGER PRIMARY KEY,
                expires_at TEXT NOT NULL,
                last_charge_id TEXT,
                total_paid INTEGER DEFAULT 0,
                is_lifetime INTEGER DEFAULT 0
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                plan_id TEXT NOT NULL,
                stars INTEGER NOT NULL,
                charge_id TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS bans (
                user_id INTEGER PRIMARY KEY,
                reason TEXT,
                banned_at TEXT NOT NULL
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                user_id INTEGER PRIMARY KEY,
                added_at TEXT NOT NULL
            )
        """)


# ---------- Подписки ----------

def get_subscription(user_id: int):
    with get_db() as db:
        row = db.execute(
            "SELECT * FROM subscriptions WHERE user_id = ?", (user_id,)
        ).fetchone()
        return dict(row) if row else None


def is_active(user_id: int) -> bool:
    if is_banned(user_id):
        return False
    sub = get_subscription(user_id)
    if not sub:
        return False
    if sub.get("is_lifetime"):
        return True
    return datetime.fromisoformat(sub["expires_at"]) > datetime.utcnow()


def is_lifetime(user_id: int) -> bool:
    sub = get_subscription(user_id)
    return bool(sub and sub.get("is_lifetime"))


def days_left(user_id: int) -> int:
    sub = get_subscription(user_id)
    if not sub or sub.get("is_lifetime"):
        return 0
    delta = datetime.fromisoformat(sub["expires_at"]) - datetime.utcnow()
    return max(0, delta.days)


def add_subscription(user_id: int, days: int, charge_id: str,
                     amount: int, plan_id: str, lifetime: bool = False):
    sub = get_subscription(user_id)
    now = datetime.utcnow()

    if sub and sub.get("is_lifetime"):
        with get_db() as db:
            db.execute("""
                INSERT INTO payments (user_id, plan_id, stars, charge_id, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, plan_id, amount, charge_id, now.isoformat()))
        return

    if lifetime:
        new_expires = now + timedelta(days=days)
        total_paid = (sub["total_paid"] if sub else 0) + amount
        new_lifetime = 1
    else:
        if sub:
            current = datetime.fromisoformat(sub["expires_at"])
            base = current if current > now else now
            new_expires = base + timedelta(days=days)
            total_paid = sub["total_paid"] + amount
        else:
            new_expires = now + timedelta(days=days)
            total_paid = amount
        new_lifetime = 0

    with get_db() as db:
        db.execute("""
            INSERT INTO subscriptions
                (user_id, expires_at, last_charge_id, total_paid, is_lifetime)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                expires_at = excluded.expires_at,
                last_charge_id = excluded.last_charge_id,
                total_paid = excluded.total_paid,
                is_lifetime = excluded.is_lifetime
        """, (user_id, new_expires.isoformat(), charge_id, total_paid, new_lifetime))

        db.execute("""
            INSERT INTO payments (user_id, plan_id, stars, charge_id, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, plan_id, amount, charge_id, now.isoformat()))


def remove_subscription(user_id: int):
    with get_db() as db:
        db.execute("DELETE FROM subscriptions WHERE user_id = ?", (user_id,))


# ---------- Баны ----------

def is_banned(user_id: int) -> bool:
    with get_db() as db:
        row = db.execute(
            "SELECT 1 FROM bans WHERE user_id = ?", (user_id,)
        ).fetchone()
        return row is not None


def ban_user(user_id: int, reason: str = ""):
    with get_db() as db:
        db.execute("""
            INSERT INTO bans (user_id, reason, banned_at)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                reason = excluded.reason,
                banned_at = excluded.banned_at
        """, (user_id, reason, datetime.utcnow().isoformat()))


def unban_user(user_id: int):
    with get_db() as db:
        db.execute("DELETE FROM bans WHERE user_id = ?", (user_id,))


def get_ban_info(user_id: int):
    with get_db() as db:
        row = db.execute(
            "SELECT * FROM bans WHERE user_id = ?", (user_id,)
        ).fetchone()
        return dict(row) if row else None


# ---------- Админы ----------

def is_admin(user_id: int) -> bool:
    with get_db() as db:
        row = db.execute(
            "SELECT 1 FROM admins WHERE user_id = ?", (user_id,)
        ).fetchone()
        return row is not None


def add_admin(user_id: int):
    with get_db() as db:
        db.execute("""
            INSERT OR IGNORE INTO admins (user_id, added_at)
            VALUES (?, ?)
        """, (user_id, datetime.utcnow().isoformat()))


def remove_admin(user_id: int):
    with get_db() as db:
        db.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))


def list_admins() -> list:
    with get_db() as db:
        rows = db.execute("SELECT user_id FROM admins").fetchall()
        return [r["user_id"] for r in rows]


# ---------- Статистика ----------

def get_stats() -> dict:
    with get_db() as db:
        users = db.execute("SELECT COUNT(*) as c FROM subscriptions").fetchone()["c"]
        active = db.execute("""
            SELECT COUNT(*) as c FROM subscriptions
            WHERE is_lifetime = 1 OR expires_at > ?
        """, (datetime.utcnow().isoformat(),)).fetchone()["c"]
        banned = db.execute("SELECT COUNT(*) as c FROM bans").fetchone()["c"]
        payments = db.execute("SELECT COUNT(*) as c FROM payments").fetchone()["c"]
        stars = db.execute(
            "SELECT COALESCE(SUM(stars), 0) as s FROM payments"
        ).fetchone()["s"]
        return {
            "users": users,
            "active": active,
            "banned": banned,
            "payments": payments,
            "stars": stars,
        }


def get_all_user_ids() -> list:
    with get_db() as db:
        rows = db.execute("SELECT user_id FROM subscriptions").fetchall()
        return [r["user_id"] for r in rows]