"""
User repository.
"""

from datetime import datetime, timezone

from himp.database.database import Database
from himp.models.user import User


class UserRepository:
    """Persists HIMP users."""

    ROLES = {
        "admin",
        "operator",
        "viewer",
    }

    def __init__(self):
        self.database = Database()
        self._ensure_table()

    def _ensure_table(self):
        self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS users
            (
                username TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                display_name TEXT NOT NULL DEFAULT '',
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL,
                last_login_at TIMESTAMP,
                failed_login_attempts INTEGER NOT NULL DEFAULT 0,
                password_change_required INTEGER NOT NULL DEFAULT 0,
                CHECK (
                    role IN (
                        'admin',
                        'operator',
                        'viewer'
                    )
                ),
                CHECK (
                    active IN (0, 1)
                ),
                CHECK (
                    failed_login_attempts >= 0
                ),
                CHECK (
                    password_change_required IN (0, 1)
                )
            )
            """
        )

    def create(
        self,
        username,
        password_hash,
        role,
        display_name="",
        password_change_required=False,
    ):
        username = self.normalize_username(username)

        self._validate_role(role)

        if not isinstance(password_hash, str):
            raise TypeError(
                "Password hash must be a string"
            )

        if not password_hash:
            raise ValueError(
                "Password hash cannot be empty"
            )

        if not isinstance(display_name, str):
            raise TypeError(
                "Display name must be a string"
            )

        now = datetime.now(timezone.utc).replace(
            tzinfo=None
        )

        self.database.execute(
            """
            INSERT INTO users
            (
                username,
                password_hash,
                role,
                active,
                display_name,
                created_at,
                updated_at,
                password_change_required
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                username,
                password_hash,
                role,
                1,
                display_name,
                now,
                now,
                int(password_change_required),
            ),
        )

        return self.get(username)

    def get(self, username):
        username = self.normalize_username(username)

        rows = self.database.query(
            """
            SELECT *
            FROM users
            WHERE username=?
            LIMIT 1
            """,
            (username,),
        )

        if not rows:
            return None

        return self._to_user(rows[0])

    def credentials(self, username):
        """Return authentication credentials for internal auth use."""
        username = self.normalize_username(username)

        rows = self.database.query(
            """
            SELECT
                username,
                password_hash,
                active,
                failed_login_attempts,
                password_change_required,
                role,
                display_name
            FROM users
            WHERE username=?
            LIMIT 1
            """,
            (username,),
        )

        if not rows:
            return None

        credentials = dict(rows[0])

        credentials["active"] = bool(
            credentials["active"]
        )

        credentials["password_change_required"] = bool(
            credentials["password_change_required"]
        )

        return credentials

    def set_password(
        self,
        username,
        password_hash,
        password_change_required=False,
    ):
        """Replace a user's password hash and authentication state."""
        username = self.normalize_username(username)

        if not isinstance(password_hash, str):
            raise TypeError(
                "Password hash must be a string"
            )

        if not password_hash:
            raise ValueError(
                "Password hash cannot be empty"
            )

        if not isinstance(
            password_change_required,
            bool,
        ):
            raise TypeError(
                "Password change required must be a boolean"
            )

        now = datetime.now(timezone.utc).replace(
            tzinfo=None
        )

        self.database.execute(
            """
            UPDATE users
            SET
                password_hash=?,
                password_change_required=?,
                failed_login_attempts=0,
                updated_at=?
            WHERE username=?
            """,
            (
                password_hash,
                int(password_change_required),
                now,
                username,
            ),
        )

    def reset_login_failures(self, username):
        """Clear failed login attempts for an account."""
        username = self.normalize_username(username)

        now = datetime.now(timezone.utc).replace(
            tzinfo=None
        )

        self.database.execute(
            """
            UPDATE users
            SET
                failed_login_attempts=0,
                updated_at=?
            WHERE username=?
            """,
            (
                now,
                username,
            ),
        )

    def update_login_success(self, username):
        username = self.normalize_username(username)

        now = datetime.now(timezone.utc).replace(
            tzinfo=None
        )

        self.database.execute(
            """
            UPDATE users
            SET
                last_login_at=?,
                failed_login_attempts=0,
                updated_at=?
            WHERE username=?
            """,
            (
                now,
                now,
                username,
            ),
        )

    def record_login_failure(self, username):
        username = self.normalize_username(username)

        now = datetime.now(timezone.utc).replace(
            tzinfo=None
        )

        self.database.execute(
            """
            UPDATE users
            SET
                failed_login_attempts =
                    failed_login_attempts + 1,
                updated_at=?
            WHERE username=?
            """,
            (
                now,
                username,
            ),
        )

    def set_active(self, username, active):
        username = self.normalize_username(username)

        if not isinstance(active, bool):
            raise TypeError(
                "Active must be a boolean"
            )

        now = datetime.now(timezone.utc).replace(
            tzinfo=None
        )

        self.database.execute(
            """
            UPDATE users
            SET
                active=?,
                updated_at=?
            WHERE username=?
            """,
            (
                int(active),
                now,
                username,
            ),
        )

    def set_password_change_required(
        self,
        username,
        required,
    ):
        username = self.normalize_username(username)

        if not isinstance(required, bool):
            raise TypeError(
                "Password change required must be "
                "a boolean"
            )

        now = datetime.now(timezone.utc).replace(
            tzinfo=None
        )

        self.database.execute(
            """
            UPDATE users
            SET
                password_change_required=?,
                updated_at=?
            WHERE username=?
            """,
            (
                int(required),
                now,
                username,
            ),
        )

    @staticmethod
    def normalize_username(username):
        if not isinstance(username, str):
            raise TypeError(
                "Username must be a string"
            )

        username = username.strip().lower()

        if not username:
            raise ValueError(
                "Username cannot be empty"
            )

        return username

    def _validate_role(self, role):
        if role not in self.ROLES:
            raise ValueError(
                "Invalid user role: "
                f"{role}"
            )

    def _to_user(self, row):
        return User(
            username=row["username"],
            role=row["role"],
            active=bool(row["active"]),
            display_name=row["display_name"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            last_login_at=row["last_login_at"],
            failed_login_attempts=row[
                "failed_login_attempts"
            ],
            password_change_required=bool(
                row["password_change_required"]
            ),
        )
