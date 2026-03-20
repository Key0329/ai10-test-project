"""Tests for work directory cleanup after job execution."""

import os
import pytest
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.executor import _cleanup_workdir


class TestCleanupWorkdir:

    def test_cleanup_after_successful_job(self, tmp_path):
        """work_dir is deleted after cleanup."""
        work_dir = tmp_path / "TEST-1-1000"
        work_dir.mkdir()
        (work_dir / "file.txt").write_text("hello")

        _cleanup_workdir(str(work_dir))

        assert not work_dir.exists()

    def test_cleanup_after_failed_job(self, tmp_path):
        """work_dir with partial content is still deleted."""
        work_dir = tmp_path / "TEST-2-1000"
        work_dir.mkdir()
        sub = work_dir / "src"
        sub.mkdir()
        (sub / "partial.py").write_text("# incomplete")

        _cleanup_workdir(str(work_dir))

        assert not work_dir.exists()

    def test_cleanup_when_workdir_does_not_exist(self, tmp_path):
        """No error when work_dir doesn't exist (clone never completed)."""
        work_dir = str(tmp_path / "NONEXISTENT-999")

        # Should not raise
        _cleanup_workdir(work_dir)

    def test_cleanup_failure_is_nonfatal(self, tmp_path, monkeypatch):
        """Cleanup failure logs but doesn't raise."""
        work_dir = tmp_path / "TEST-3-1000"
        work_dir.mkdir()

        import shutil
        def mock_rmtree(path, **kwargs):
            raise PermissionError("access denied")

        monkeypatch.setattr(shutil, "rmtree", mock_rmtree)

        # Should not raise
        _cleanup_workdir(str(work_dir))

    def test_job_status_preserved_after_cleanup_failure(self, tmp_path, monkeypatch):
        """Cleanup failure returns False but no exception propagates."""
        work_dir = tmp_path / "TEST-4-1000"
        work_dir.mkdir()

        import shutil
        def mock_rmtree(path, **kwargs):
            raise OSError("disk error")

        monkeypatch.setattr(shutil, "rmtree", mock_rmtree)

        # Returns False on failure, True on success
        result = _cleanup_workdir(str(work_dir))
        assert result is False

    def test_cleanup_returns_true_on_success(self, tmp_path):
        """Cleanup returns True when successful."""
        work_dir = tmp_path / "TEST-5-1000"
        work_dir.mkdir()

        result = _cleanup_workdir(str(work_dir))
        assert result is True
