"""
Workflow definition repository.
"""

from himp.database.database import Database


class WorkflowRepository:
    """
    Persists workflow definitions, workflow tasks,
    and workflow-local dependencies.
    """

    def __init__(self):
        self.database = Database()
        self._ensure_tables()

    def _ensure_tables(self):
        self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS workflows
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT NOT NULL DEFAULT '',
                enabled INTEGER NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS workflow_tasks
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_id INTEGER NOT NULL,
                task_id TEXT NOT NULL,
                position INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                UNIQUE(workflow_id, task_id),

                FOREIGN KEY(workflow_id)
                    REFERENCES workflows(id)
                    ON DELETE CASCADE
            )
            """
        )

        self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS workflow_dependencies
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_id INTEGER NOT NULL,
                task_id TEXT NOT NULL,
                depends_on_task_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                UNIQUE(
                    workflow_id,
                    task_id,
                    depends_on_task_id
                ),

                FOREIGN KEY(workflow_id)
                    REFERENCES workflows(id)
                    ON DELETE CASCADE
            )
            """
        )

    # ------------------------------------------------------------------
    # Workflows
    # ------------------------------------------------------------------

    def create(
        self,
        name,
        description="",
        enabled=True,
    ):
        cursor = self.database.execute(
            """
            INSERT INTO workflows
            (
                name,
                description,
                enabled
            )
            VALUES (?, ?, ?)
            """,
            (
                name,
                description,
                int(enabled),
            ),
        )

        return self.get(cursor.lastrowid)

    def get(self, workflow_id):
        rows = self.database.query(
            """
            SELECT *
            FROM workflows
            WHERE id=?
            LIMIT 1
            """,
            (workflow_id,),
        )

        if not rows:
            return None

        return dict(rows[0])

    def get_by_name(self, name):
        rows = self.database.query(
            """
            SELECT *
            FROM workflows
            WHERE name=?
            LIMIT 1
            """,
            (name,),
        )

        if not rows:
            return None

        return dict(rows[0])

    def list(self):
        rows = self.database.query(
            """
            SELECT *
            FROM workflows
            ORDER BY id
            """
        )

        return [dict(row) for row in rows]

    def update(
        self,
        workflow_id,
        name,
        description,
        enabled,
    ):
        self.database.execute(
            """
            UPDATE workflows
            SET
                name=?,
                description=?,
                enabled=?,
                updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (
                name,
                description,
                int(enabled),
                workflow_id,
            ),
        )

        return self.get(workflow_id)

    def delete(self, workflow_id):
        self.database.execute(
            """
            DELETE FROM workflow_dependencies
            WHERE workflow_id=?
            """,
            (workflow_id,),
        )

        self.database.execute(
            """
            DELETE FROM workflow_tasks
            WHERE workflow_id=?
            """,
            (workflow_id,),
        )

        self.database.execute(
            """
            DELETE FROM workflows
            WHERE id=?
            """,
            (workflow_id,),
        )

    # ------------------------------------------------------------------
    # Workflow tasks
    # ------------------------------------------------------------------

    def add_task(
        self,
        workflow_id,
        task_id,
        position,
    ):
        cursor = self.database.execute(
            """
            INSERT INTO workflow_tasks
            (
                workflow_id,
                task_id,
                position
            )
            VALUES (?, ?, ?)
            """,
            (
                workflow_id,
                task_id,
                position,
            ),
        )

        rows = self.database.query(
            """
            SELECT *
            FROM workflow_tasks
            WHERE id=?
            LIMIT 1
            """,
            (cursor.lastrowid,),
        )

        if not rows:
            return None

        return dict(rows[0])

    def get_task(
        self,
        workflow_id,
        task_id,
    ):
        rows = self.database.query(
            """
            SELECT *
            FROM workflow_tasks
            WHERE workflow_id=?
              AND task_id=?
            LIMIT 1
            """,
            (
                workflow_id,
                task_id,
            ),
        )

        if not rows:
            return None

        return dict(rows[0])

    def list_tasks(self, workflow_id):
        rows = self.database.query(
            """
            SELECT *
            FROM workflow_tasks
            WHERE workflow_id=?
            ORDER BY position, id
            """,
            (workflow_id,),
        )

        return [dict(row) for row in rows]

    def remove_task(
        self,
        workflow_id,
        task_id,
    ):
        self.database.execute(
            """
            DELETE FROM workflow_dependencies
            WHERE workflow_id=?
              AND (
                    task_id=?
                    OR depends_on_task_id=?
              )
            """,
            (
                workflow_id,
                task_id,
                task_id,
            ),
        )

        self.database.execute(
            """
            DELETE FROM workflow_tasks
            WHERE workflow_id=?
              AND task_id=?
            """,
            (
                workflow_id,
                task_id,
            ),
        )

    # ------------------------------------------------------------------
    # Workflow dependencies
    # ------------------------------------------------------------------

    def add_dependency(
        self,
        workflow_id,
        task_id,
        depends_on_task_id,
    ):
        cursor = self.database.execute(
            """
            INSERT INTO workflow_dependencies
            (
                workflow_id,
                task_id,
                depends_on_task_id
            )
            VALUES (?, ?, ?)
            """,
            (
                workflow_id,
                task_id,
                depends_on_task_id,
            ),
        )

        rows = self.database.query(
            """
            SELECT *
            FROM workflow_dependencies
            WHERE id=?
            LIMIT 1
            """,
            (cursor.lastrowid,),
        )

        if not rows:
            return None

        return dict(rows[0])

    def list_dependencies(self, workflow_id):
        rows = self.database.query(
            """
            SELECT *
            FROM workflow_dependencies
            WHERE workflow_id=?
            ORDER BY id
            """,
            (workflow_id,),
        )

        return [dict(row) for row in rows]

    def list_task_dependencies(
        self,
        workflow_id,
        task_id,
    ):
        rows = self.database.query(
            """
            SELECT *
            FROM workflow_dependencies
            WHERE workflow_id=?
              AND task_id=?
            ORDER BY id
            """,
            (
                workflow_id,
                task_id,
            ),
        )

        return [dict(row) for row in rows]

    def remove_dependency(
        self,
        workflow_id,
        task_id,
        depends_on_task_id,
    ):
        self.database.execute(
            """
            DELETE FROM workflow_dependencies
            WHERE workflow_id=?
              AND task_id=?
              AND depends_on_task_id=?
            """,
            (
                workflow_id,
                task_id,
                depends_on_task_id,
            ),
        )
