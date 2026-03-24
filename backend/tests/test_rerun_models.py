"""Tests for JobResponse parent_job_id field."""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from models.job import JobResponse


class TestJobResponseParentJobId:
    def test_parent_job_id_defaults_to_none(self):
        """JobResponse should have parent_job_id defaulting to None."""
        job = JobResponse(
            job_id="TEST-1-123",
            repo_url="https://github.com/test/repo",
            jira_ticket="TEST-1",
            branch="main",
            extra_prompt=None,

            requested_by=None,
            status="queued",
            exit_code=None,
            pr_url=None,
            error_message=None,
            created_at="2026-01-01T00:00:00Z",
            started_at=None,
            finished_at=None,
        )
        assert job.parent_job_id is None

    def test_parent_job_id_can_be_set(self):
        """JobResponse should accept parent_job_id."""
        job = JobResponse(
            job_id="TEST-1-456",
            repo_url="https://github.com/test/repo",
            jira_ticket="TEST-1",
            branch="main",
            extra_prompt=None,

            requested_by=None,
            status="queued",
            exit_code=None,
            pr_url=None,
            error_message=None,
            created_at="2026-01-01T00:00:00Z",
            started_at=None,
            finished_at=None,
            parent_job_id="TEST-1-123",
        )
        assert job.parent_job_id == "TEST-1-123"

    def test_parent_job_id_in_serialized_output(self):
        """parent_job_id should appear in model_dump output."""
        job = JobResponse(
            job_id="TEST-1-789",
            repo_url="https://github.com/test/repo",
            jira_ticket="TEST-1",
            branch="main",
            extra_prompt=None,

            requested_by=None,
            status="queued",
            exit_code=None,
            pr_url=None,
            error_message=None,
            created_at="2026-01-01T00:00:00Z",
            started_at=None,
            finished_at=None,
            parent_job_id="TEST-1-100",
        )
        data = job.model_dump()
        assert "parent_job_id" in data
        assert data["parent_job_id"] == "TEST-1-100"
