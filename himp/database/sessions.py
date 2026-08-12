"""
Session repository.

Persists server-side authentication sessions without storing
plaintext session tokens.
"""

from datetime import datetime, timezone

from himp.database.database import Database


class SessionRepository:
    """Persists and manages authentication sessions."""

    def __init__(self):
        self.database = Database()
        self._ensure_table()

    def _ensure_table(self):
        self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                token_hash TEXT NOT NULL UNIQUE,

                username TEXT NOT NULL,

                created_at TIMESTAMP NOT NULL,

                expires_at TIMESTAMP NOT NULL,

                revoked_at TIMESTAMP,

                last_seen_at TIMESTAMP NOT NULL,

                CHECK (
                    length(token_hash) = 64
                ),

                CHECK (
                    length(username) > 0
                ),

                CHECK (
                    expires_at > created_at
                )
            )
            """
        )

    def create(
        self,
        token_hash,
        username,
        created_at,
        expires_at,
    ):
        """Create a new authentication session."""

        if not isinstance(token_hash, str):
            raise TypeError(
                "Token hash must be a string"
            )

        if len(token_hash) != 64:
            raise ValueError(
                "Token hash must be a SHA-256 hexadecimal digest"
            )

        if not isinstance(username, str):
            raise TypeError(
                "Username must be a string"
            )

        username = username.strip().lower()

        if not username:
            raise ValueError(
                "Username cannot be empty"
            )

        if not isinstance(created_at, datetime):
            raise TypeError(
                "Created at must be a datetime"
            )

        if not isinstance(expires_at, datetime):
            raise TypeError(
                "Expires at must be a datetime"
            )

        if expires_at <= created_at:
            raise ValueError(
                "Session expiration must be after creation"
            )

        self.database.execute(
            """
            INSERT INTO sessions
            (
                token_hash,
                username,
                created_at,
                expires_at,
                last_seen_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                token_hash,
                username,
                created_at,
                expires_at,
                created_at,
            ),
        )

        return self.get(token_hash)

    def get(self, token_hash):
        """Return a session by token hash."""

        rows = self.database.query(
            """
            SELECT *
            FROM sessions
            WHERE token_hash=?
            LIMIT 1
            """,
            (token_hash,),
        )

        if not rows:
            return None

        return dict(rows[0])

    def active(self, token_hash, now=None):
        """Return a session only when it is active and unexpired."""

        if now is None:
            now = datetime.now(timezone.utc).replace(
                tzinfo=None
            )

        rows = self.database.query(
            """
            SELECT *
            FROM sessions
            WHERE token_hash=?
              AND revoked_at IS NULL
              AND expires_at > ?
            LIMIT 1
            """,
            (
                token_hash,
                now,
            ),
        )

        if not rows:
            return None

        return dict(rows[0])

    def touch(self, token_hash, now=None):
        """Update the last-seen time for an active session."""

        if now is None:
            now = datetime.now(timezone.utc).replace(
                tzinfo=None
            )

        self.database.execute(
            """
            UPDATE sessions
            SET last_seen_at=?
            WHERE token_hash=?
              AND revoked_at IS NULL
              AND expires_at > ?
            """,
            (
                now,
                token_hash,
                now,
            ),
        )

    def revoke(self, token_hash, now=None):
        """Revoke a session."""

        if now is None:
            now = datetime.now(timezone.utc).replace(
                tzinfo=None
            )

        self.database.execute(
            """
            UPDATE sessions
            SET revoked_at=?
            WHERE token_hash=?
              AND revoked_at IS NULL
            """,
            (
                now,
                token_hash,
            ),
        )

    def revoke_all(self, username, now=None):
        """Revoke every active session belonging to a user."""

        if not isinstance(username, str):
            raise TypeError(
                "Username must be a string"
            )

        username = username.strip().lower()

        if not username:
            raise ValueError(
                "Username cannot be empty"
            )

        if now is None:
            now = datetime.now(timezone.utc).replace(
                tzinfo=None
            )

        self.database.execute(
            """
            UPDATE sessions
            SET revoked_at=?
            WHERE username=?
              AND revoked_at IS NULL
            """,
            (
                now,
                username,
            ),
        )

    def delete_expired(self, now=None):
        """Delete expired and revoked sessions."""

        if now is None:
            now = datetime.now(timezone.utc).replace(
                tzinfo=None
            )

        cursor = self.database.execute(
            """
            DELETE FROM sessions
            WHERE expires_at <= ?
               OR revoked_at IS NOT NULL
            """,
            (now,),
        )

        return cursor.rowcount
