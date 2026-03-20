"""Tests for jobs table — parent_job_id column for rerun support."""

import aiosqlite
import pytest
import pytest_asyncio


@pytest_asyncio.fixture
async def db(tmp_path):
    """Create a temp DB with current schema applied."""
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

    db_path = str(tmp_path / "test.sqlite")
    conn = await aiosqlite.connect(db_path)
    conn.row_factory = aiosqlite.Row

    from db import CREATE_JOBS_TABLE, CREATE_LOGS_TABLE
    await conn.execute(CREATE_JOBS_TABLE)
    await conn.execute(CREATE_LOGS_TABLE)
    await conn.commit()
    yield conn
    await conn.close()


class TestParentJobIdSchema:
    """Verify jobs table has parent_job_id column."""

    @pytest.mark.asyncio
    async def test_fresh_db_has_parent_job_id_column(self, db):
        """A fresh DB created with CREATE_JOBS_TABLE should include parent_job_id."""
        cursor = await db.execute("PRAGMA table_info(jobs)")
        columns = {row[1] for row in await cursor.fetchall()}
        assert "parent_job_id" in columns

    @pytest.mark.asyncio
    async def test_insert_job_with_parent_job_id(self, db):
        """Should be able to insert a job with parent_job_id set."""
        await db.execute(
            "INSERT INTO jobs (id, repo_url, jira_ticket, created_at, parent_job_id) "
            "VALUES (?, ?, ?, ?, ?)",
            ("job-rerun-1", "https://github.com/org/repo", "JIRA-100",
             "2026-03-20T00:00:00Z", "job-original-1"),
        )
        await db.commit()
        cursor = await db.execute(
            "SELECT parent_job_id FROM jobs WHERE id = 'job-rerun-1'"
        )
        row = await cursor.fetchone()
        assert row["parent_job_id"] == "job-original-1"

    @pytest.mark.asyncio
    async def test_parent_job_id_defaults_to_null(self, db):
        """Jobs without parent_job_id should default to NULL."""
        await db.execute(
            "INSERT INTO jobs (id, repo_url, jira_ticket, created_at) "
            "VALUES (?, ?, ?, ?)",
            ("job-new-1", "https://github.com/org/repo", "JIRA-200",
             "2026-03-20T00:00:00Z"),
        )
        await db.commit()
        cursor = await db.execute(
            "SELECT parent_job_id FROM jobs WHERE id = 'job-new-1'"
        )
        row = await cursor.fetchone()
        assert row["parent_job_id"] is None


class TestMigrateJobsParent:
    """Verify _migrate_jobs_parent adds the column to legacy DBs."""

    @pytest.mark.asyncio
    async def test_migration_adds_parent_job_id_to_legacy_db(self, tmp_path):
        """Migration should add parent_job_id to a DB that lacks it."""
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

        db_path = str(tmp_path / "legacy.sqlite")
        conn = await aiosqlite.connect(db_path)
        conn.row_factory = aiosqlite.Row

        # Create a legacy jobs table WITHOUT parent_job_id
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                repo_url TEXT NOT NULL,
                jira_ticket TEXT NOT NULL,
                branch TEXT DEFAULT 'main',
                extra_prompt TEXT DEFAULT '',
                priority INTEGER DEFAULT 3,
                requested_by TEXT DEFAULT '',
                status TEXT DEFAULT 'queued',
                exit_code INTEGER,
                pr_url TEXT,
                error_message TEXT,
                work_dir TEXT,
                created_at TEXT NOT NULL,
                started_at TEXT,
                finished_at TEXT
            );
        """)
        await conn.commit()

        # Verify column is missing before migration
        cursor = await conn.execute("PRAGMA table_info(jobs)")
        columns_before = {row[1] for row in await cursor.fetchall()}
        assert "parent_job_id" not in columns_before

        # Run migration
        from db import _migrate_jobs_parent
        await _migrate_jobs_parent(conn)
        await conn.commit()

        # Verify column now exists
        cursor = await conn.execute("PRAGMA table_info(jobs)")
        columns_after = {row[1] for row in await cursor.fetchall()}
        assert "parent_job_id" in columns_after

        await conn.close()

    @pytest.mark.asyncio
    async def test_migration_is_noop_when_column_exists(self, db):
        """Running migration on a DB that already has parent_job_id should not error."""
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

        from db import _migrate_jobs_parent

        # Run migration twice — second call should be a no-op
        await _migrate_jobs_parent(db)
        await _migrate_jobs_parent(db)

        # Verify column still exists and only once
        cursor = await db.execute("PRAGMA table_info(jobs)")
        columns = [row[1] for row in await cursor.fetchall()]
        assert columns.count("parent_job_id") == 1
